#!/usr/bin/env python3
"""
Генератор аварийных сценариев для оценки RAG системы.

Скрипт генерирует аварийные сценарии с помощью X5 модели,
затем получает ответы через API RAG системы и сохраняет результаты.
"""

import asyncio
import json
import logging
import os
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

import httpx
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# Добавляем родительскую директорию в путь для импорт
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.evaluation.evaluation_config import EvaluationConfig

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AccidentScenarioGenerator:
    """Генератор аварийных сценариев."""
    
    def __init__(
        self,
        model: str = None,
        rag_api_url: str = "http://localhost:8001",
        rag_api_timeout: int = 120
    ):
        """
        Инициализация генератора.
        
        Args:
            model: Модель X5 для генерации вопросов
            rag_api_url: URL API RAG системы
            rag_api_timeout: Таймаут запросов к API
        """
        self.model = model or EvaluationConfig.get_model()
        self.rag_api_url = rag_api_url
        self.rag_api_timeout = rag_api_timeout
        
        # Настройка LLM для генерации вопросов
        self.llm = self._setup_llm()
        
        logger.info(f"Генератор инициализирован с моделью: {self.model}")
        logger.info(f"API RAG системы: {self.rag_api_url}")
    
    def _setup_llm(self) -> ChatOpenAI:
        """Настройка LLM для генерации вопросов."""
        api_key = EvaluationConfig.get_api_key()
        base_url = EvaluationConfig.get_base_url()
        
        return ChatOpenAI(
            model=self.model,
            api_key=api_key,
            base_url=base_url,
            temperature=0.8,
            timeout=120
        )
    
    def generate_scenarios(self, num_scenarios: int = 75) -> List[str]:
        """
        Генерирует аварийные сценарии.
        
        Args:
            num_scenarios: Количество сценариев для генерации
            
        Returns:
            Список описаний сценариев
        """
        logger.info(f"Генерация {num_scenarios} аварийных сценариев...")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Ты - эксперт по железнодорожной безопасности и аварийному реагированию.

Сгенерируй {{num_scenarios}} уникальных и реалистичных аварийных сценариев на железной дороге.

Каждый сценарий должен включать:
- Тип аварии (сход поезда, столкновение, пожар, обрыв контактной сети, обрушение и т.д.)
- Местоположение (станция, перегон, мост, тоннель, переезд и т.д.)
- Погодные условия
- Масштаб повреждений
- Особенности доступа к месту аварии
- Какие ресурсы могут потребоваться

Сценарии должны быть разнообразными и охватывать разные ситуации.

ВАЖНО: Верни ТОЛЬКО JSON массив строк, без вводного текста и пояснений.
Формат ответа: ["сценарий 1", "сценарий 2", "сценарий 3", ...]"""),
            ("user", "Сгенерируй {num_scenarios} аварийных сценариев для железнодорожной инфраструктуры в формате JSON массива.")
        ])
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({"num_scenarios": num_scenarios})
            content = response.content
            
            # Парсим ответ
            scenarios = self._parse_scenarios(content)
            
            logger.info(f"Успешно сгенерировано {len(scenarios)} сценариев")
            return scenarios
            
        except Exception as e:
            logger.error(f"Ошибка при генерации сценариев: {e}")
            raise
    
    def _parse_scenarios(self, content: str) -> List[str]:
        """
        Парсит сгенерированные сценарии из ответа LLM.
        
        Args:
            content: Текст ответа от LLM
            
        Returns:
            Список сценариев
        """
        scenarios = []
        
        # Пытаемся найти JSON массив
        try:
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                scenarios = json.loads(json_str)
            else:
                # Альтернативный парсинг
                logger.warning("Не удалось найти JSON в ответе, используем альтернативный парсинг")
                scenarios = []
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('[') and not line.startswith(']'):
                        # Удаляем нумерацию и кавычки
                        line = line.lstrip('0123456789.- ')
                        line = line.strip('"\'')
                        if line:
                            scenarios.append(line)
        except json.JSONDecodeError:
            # Если JSON не распарсился, используем альтернативный метод
            logger.warning("Ошибка парсинга JSON, используем альтернативный метод")
            scenarios = []
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('[') and not line.startswith(']'):
                    line = line.lstrip('0123456789.- ')
                    line = line.strip('"\'')
                    if line:
                        scenarios.append(line)
        
        return scenarios
    
    async def get_rag_answers(
        self,
        scenarios: List[str],
        mode: str = "plan"
    ) -> List[Dict[str, Any]]:
        """
        Получает ответы от RAG системы через API.
        
        Args:
            scenarios: Список описаний сценариев
            mode: Режим работы RAG системы (chat или plan)
            
        Returns:
            Список словарей с вопросами и ответами
        """
        logger.info(f"Получение ответов от RAG системы для {len(scenarios)} сценариев...")
        
        results = []
        
        async with httpx.AsyncClient(timeout=self.rag_api_timeout) as client:
            for i, scenario in enumerate(scenarios, 1):
                logger.info(f"Обработка сценария {i}/{len(scenarios)}")
                
                try:
                    # Формируем запрос к API
                    payload = {
                        "question": scenario,
                        "mode": mode
                    }
                    
                    response = await client.post(
                        f"{self.rag_api_url}/ask",
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        answer = data.get("answer", "")
                        retrieved_contexts = data.get("retrieved_contexts", [])
                         
                        # Для режима plan собираем полный ответ
                        if mode == "plan":
                            full_answer = answer
                             
                            # Добавляем информацию о подразделениях
                            subdivisions = data.get("subdivisions", {})
                            if subdivisions.get("list"):
                                full_answer += f"\n\nПодразделения: {', '.join(subdivisions['list'])}"
                             
                            # Добавляем информацию о технике
                            technics = data.get("technics", {})
                            if technics.get("list"):
                                full_answer += f"\n\nТехника: {', '.join(technics['list'])}"
                             
                            # Добавляем информацию о сотрудниках
                            employees = data.get("employees", {})
                            if employees.get("list"):
                                full_answer += f"\n\nСотрудники: {', '.join(employees['list'])}"
                             
                            # Добавляем план работ
                            work_plan = data.get("work_plan", {})
                            if work_plan.get("plan"):
                                full_answer += f"\n\nПлан работ: {work_plan['plan']}"
                             
                            answer = full_answer
                    else:
                        logger.error(f"Ошибка API: {response.status_code} - {response.text}")
                        answer = f"Ошибка API: {response.status_code}"
                        retrieved_contexts = []
                     
                    results.append({
                        "question": scenario,
                        "ground_truth": answer,
                        "retrieved_contexts": retrieved_contexts,
                        "category": "accident_scenario"
                    })
                    
                except httpx.TimeoutException:
                    logger.error(f"Таймаут при запросе к API для сценария {i}")
                    results.append({
                        "question": scenario,
                        "ground_truth": "Ошибка: Таймаут запроса к API",
                        "category": "accident_scenario"
                    })
                except Exception as e:
                    logger.error(f"Ошибка при обработке сценария {i}: {e}")
                    results.append({
                        "question": scenario,
                        "ground_truth": f"Ошибка: {str(e)}",
                        "category": "accident_scenario"
                    })
        
        logger.info(f"Получено {len(results)} ответов от RAG системы")
        return results
    
    def save_scenarios(
        self,
        scenarios_data: List[Dict[str, Any]],
        filename: str = None
    ) -> str:
        """
        Сохраняет сценарии в JSON файл.
        
        Args:
            scenarios_data: Список словарей с данными сценариев
            filename: Имя файла для сохранения
            
        Returns:
            Путь к сохраненному файлу
        """
        if filename is None:
            filename = "accident_scenarios.json"
        
        output_dir = Path("../test_data")
        output_dir.mkdir(exist_ok=True)
        
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(scenarios_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Сценарии сохранены в: {filepath}")
        return str(filepath)
    
    def print_summary(self, scenarios_data: List[Dict[str, Any]]):
        """
        Выводит сводку по сгенерированным сценариям.
        
        Args:
            scenarios_data: Список словарей с данными сценариев
        """
        total = len(scenarios_data)
        successful = sum(1 for s in scenarios_data if not s["ground_truth"].startswith("Ошибка"))
        failed = total - successful
        
        print("\n" + "="*60)
        print("СВОДКА ПО СГЕНЕРИРОВАННЫМ СЦЕНАРИЯМ")
        print("="*60)
        print(f"Всего сценариев: {total}")
        print(f"Успешно обработано: {successful}")
        print(f"С ошибками: {failed}")
        print("="*60)
        
        if successful > 0:
            print("\nПримеры сценариев:")
            print("-"*60)
            for i, scenario in enumerate(scenarios_data[:3], 1):
                print(f"\n{i}. Вопрос: {scenario['question'][:100]}...")
                print(f"   Ответ: {scenario['ground_truth'][:150]}...")
            print("-"*60)


async def main():
    """Главная функция для генерации сценариев."""
    parser = argparse.ArgumentParser(
        description="Генератор аварийных сценариев для оценки RAG системы"
    )
    parser.add_argument(
        "--num-scenarios",
        type=int,
        default=75,
        help="Количество сценариев для генерации (по умолчанию: 75)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Модель X5 для генерации вопросов (по умолчанию: из конфигурации)"
    )
    parser.add_argument(
        "--rag-api-url",
        type=str,
        default="http://localhost:8001",
        help="URL API RAG системы (по умолчанию: http://localhost:8001)"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="plan",
        choices=["chat", "plan"],
        help="Режим работы RAG системы (по умолчанию: plan)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="../test_data",
        help="Директория для сохранения результатов (по умолчанию: ../test_data)"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Имя файла для сохранения результатов (по умолчанию: auto-generated)"
    )
    
    args = parser.parse_args()
    
    try:
        # Создаем генератор
        generator = AccidentScenarioGenerator(
            model=args.model,
            rag_api_url=args.rag_api_url
        )
        
        # Генерируем сценарии
        scenarios = generator.generate_scenarios(args.num_scenarios)
        
        if not scenarios:
            logger.error("Не удалось сгенерировать сценарии")
            return
        
        # Получаем ответы от RAG системы
        scenarios_data = await generator.get_rag_answers(scenarios, mode=args.mode)
        
        # Сохраняем результаты
        output_path = generator.save_scenarios(scenarios_data, args.output_file)
        
        # Выводим сводку
        generator.print_summary(scenarios_data)
        
        print(f"\nРезультаты сохранены в: {output_path}")
        
    except KeyboardInterrupt:
        logger.info("Генерация прервана пользователем")
    except Exception as e:
        logger.error(f"Ошибка при выполнении: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
