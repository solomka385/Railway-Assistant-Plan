# test_data_generator.py
"""
Генератор тестовых данных для оценки RAG системы.

Автоматически создает вопросы и эталонные ответы из документов,
хранящихся в векторных базах данных.

Поддержка кастомных API endpoints (X5 API):
- Автоматически определяет тип модели (X5 или OpenAI)
- Настраивает base_url для X5 API
"""

import sys
import os

# Добавляем родительскую директорию в sys.path для импортов
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

import chromadb
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from scripts.config import config
from scripts.evaluation.evaluation_config import EvaluationConfig

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TestQuestion:
    """Тестовый вопрос с эталонным ответом."""
    question: str
    ground_truth: str
    source_doc: str
    category: str


class TestDataGenerator:
    """Генератор тестовых данных из документов."""
    
    def __init__(
        self,
        llm_model: Optional[str] = None,
        questions_per_doc: int = 3,
        output_dir: str = "test_data"
    ):
        """
        Инициализация генератора тестовых данных.
        
        Args:
            llm_model: Модель для генерации вопросов (по умолчанию из конфигурации)
            questions_per_doc: Количество вопросов на документ
            output_dir: Директория для сохранения результатов
        """
        self.llm_model = llm_model or EvaluationConfig.get_model()
        self.questions_per_doc = questions_per_doc
        self.output_dir = output_dir
        
        # Создаем директорию для результатов
        os.makedirs(output_dir, exist_ok=True)
        
        # Настраиваем LLM с поддержкой X5 API
        self._setup_llm()
    
    def _setup_llm(self):
        """Настраивает LLM с поддержкой X5 API."""
        base_url = EvaluationConfig.get_base_url()
        api_key = EvaluationConfig.get_api_key()
        
        # Создаем LangChain ChatOpenAI с кастомным base_url
        self.llm = ChatOpenAI(
            model=self.llm_model,
            temperature=0.7,
            openai_api_key=api_key,
            openai_api_base=base_url,
            request_timeout=60
        )
        
        logger.info(f"Используется модель: {self.llm_model}")
        logger.info(f"API Base URL: {base_url}")
        
        # Промпт для генерации вопросов
        self.question_prompt = ChatPromptTemplate.from_messages([
            ("system", """Ты - эксперт по созданию тестовых вопросов для оценки RAG систем.
            
Твоя задача - создать {num_questions} тестовых вопросов на основе предоставленного документа.
Каждый вопрос должен:
1. Быть конкретным и понятным
2. Требовать информации из документа
3. Быть разнообразным по типу (фактический, аналитический, процедурный)
4. Быть на русском языке

Формат ответа - JSON массив объектов:
[
    {
        "question": "Текст вопроса",
        "ground_truth": "Краткий и точный ответ на основе документа",
        "category": "Категория вопроса (например: обязанности, процедуры, характеристики)"
    }
]
"""),
            ("user", "Документ:\n\n{document}\n\nСоздай {num_questions} тестовых вопросов.")
        ])
        
        # Промпт для генерации вопросов из списка подразделений
        self.subdivision_prompt = ChatPromptTemplate.from_messages([
            ("system", """Ты - эксперт по созданию тестовых вопросов о железнодорожных подразделениях.
            
Создай {num_questions} тестовых вопросов на основе списка подразделений.
Вопросы должны касаться:
- Обязанностей подразделения
- Типичных ситуаций, когда привлекается подразделение
- Характеристик подразделения

Формат ответа - JSON массив:
[
    {
        "question": "Текст вопроса",
        "ground_truth": "Краткий ответ",
        "category": "Категория"
    }
]
"""),
            ("user", "Подразделения:\n{subdivisions}\n\nСоздай {num_questions} вопросов.")
        ])
    
    def load_documents_from_chroma(
        self,
        persist_directory: str,
        collection_name: str = "default",
        max_docs: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Загружает документы из ChromaDB.
        
        Args:
            persist_directory: Путь к директории ChromaDB
            collection_name: Имя коллекции
            max_docs: Максимальное количество документов
            
        Returns:
            Список документов
        """
        try:
            client = chromadb.PersistentClient(path=persist_directory)
            collection = client.get_collection(name=collection_name)
            
            # Получаем все документы
            results = collection.get(
                limit=max_docs,
                include=["documents", "metadatas"]
            )
            
            docs = []
            for i, doc in enumerate(results["documents"]):
                metadata = results["metadatas"][i] if results["metadatas"] else {}
                docs.append({
                    "content": doc,
                    "metadata": metadata,
                    "id": results.get("ids", [])[i] if results.get("ids") else f"doc_{i}"
                })
            
            logger.info(f"Загружено {len(docs)} документов из {persist_directory}")
            return docs
            
        except Exception as e:
            logger.error(f"Ошибка загрузки документов из {persist_directory}: {e}")
            return []
    
    async def generate_questions_from_document(
        self,
        document: str,
        category: str = "general"
    ) -> List[TestQuestion]:
        """
        Генерирует вопросы из одного документа.
        
        Args:
            document: Текст документа
            category: Категория документа
            
        Returns:
            Список тестовых вопросов
        """
        try:
            # Ограничиваем длину документа
            max_length = 4000
            truncated_doc = document[:max_length] if len(document) > max_length else document
            
            # Генерируем вопросы
            chain = self.question_prompt | self.llm
            response = await chain.ainvoke({
                "document": truncated_doc,
                "num_questions": self.questions_per_doc
            })
            
            # Парсим JSON ответ
            content = response.content
            # Извлекаем JSON из ответа (если есть дополнительный текст)
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                questions_data = json.loads(json_str)
            else:
                logger.warning(f"Не удалось найти JSON в ответе: {content[:200]}...")
                return []
            
            # Создаем объекты TestQuestion
            questions = []
            for q_data in questions_data:
                questions.append(TestQuestion(
                    question=q_data.get("question", ""),
                    ground_truth=q_data.get("ground_truth", ""),
                    source_doc=truncated_doc[:100] + "...",
                    category=q_data.get("category", category)
                ))
            
            return questions
            
        except Exception as e:
            logger.error(f"Ошибка генерации вопросов: {e}")
            return []
    
    async def generate_questions_from_subdivisions(
        self,
        subdivisions: Dict[str, str],
        num_questions: int = 10
    ) -> List[TestQuestion]:
        """
        Генерирует вопросы из списка подразделений.
        
        Args:
            subdivisions: Словарь {код: описание}
            num_questions: Количество вопросов
            
        Returns:
            Список тестовых вопросов
        """
        try:
            # Формируем текст подразделений
            subdivisions_text = "\n".join([
                f"{code}: {desc}" for code, desc in subdivisions.items()
            ])
            
            # Генерируем вопросы
            chain = self.subdivision_prompt | self.llm
            response = await chain.ainvoke({
                "subdivisions": subdivisions_text,
                "num_questions": num_questions
            })
            
            # Парсим JSON ответ
            content = response.content
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                questions_data = json.loads(json_str)
            else:
                logger.warning(f"Не удалось найти JSON в ответе")
                return []
            
            # Создаем объекты TestQuestion
            questions = []
            for q_data in questions_data:
                questions.append(TestQuestion(
                    question=q_data.get("question", ""),
                    ground_truth=q_data.get("ground_truth", ""),
                    source_doc="Подразделения",
                    category=q_data.get("category", "subdivisions")
                ))
            
            return questions
            
        except Exception as e:
            logger.error(f"Ошибка генерации вопросов из подразделений: {e}")
            return []
    
    async def generate_all_test_data(self) -> Dict[str, List[TestQuestion]]:
        """
        Генерирует тестовые данные из всех источников.
        
        Returns:
            Словарь {категория: список вопросов}
        """
        all_questions = {
            "technic": [],
            "work_plan": [],
            "employees": [],
            "subdivisions": [],
            "all_docs": []
        }
        
        # Генерируем вопросы из техники
        logger.info("Генерация вопросов из техники...")
        technic_docs = self.load_documents_from_chroma(
            config.PERSIST_DIRECTORY_TECHNIC,
            max_docs=10
        )
        for doc in technic_docs:
            questions = await self.generate_questions_from_document(
                doc["content"],
                category="technic"
            )
            all_questions["technic"].extend(questions)
        
        # Генерируем вопросы из плана работ
        logger.info("Генерация вопросов из плана работ...")
        work_plan_docs = self.load_documents_from_chroma(
            config.PERSIST_DIRECTORY_WORK_PLAN,
            max_docs=10
        )
        for doc in work_plan_docs:
            questions = await self.generate_questions_from_document(
                doc["content"],
                category="work_plan"
            )
            all_questions["work_plan"].extend(questions)
        
        # Генерируем вопросы из сотрудников
        logger.info("Генерация вопросов из сотрудников...")
        employees_docs = self.load_documents_from_chroma(
            config.PERSIST_DIRECTORY_EMPLOYEES,
            max_docs=10
        )
        for doc in employees_docs:
            questions = await self.generate_questions_from_document(
                doc["content"],
                category="employees"
            )
            all_questions["employees"].extend(questions)
        
        # Генерируем вопросы из подразделений
        logger.info("Генерация вопросов из подразделений...")
        subdivisions_docs = self.load_documents_from_chroma(
            config.PERSIST_DIRECTORY_SUBDIVISIONS,
            max_docs=10
        )
        for doc in subdivisions_docs:
            questions = await self.generate_questions_from_document(
                doc["content"],
                category="subdivisions"
            )
            all_questions["subdivisions"].extend(questions)
        
        # Генерируем вопросы из справочника подразделений
        logger.info("Генерация вопросов из справочника подразделений...")
        subdivision_questions = await self.generate_questions_from_subdivisions(
            config.ALLOWED_SUBDIVISIONS,
            num_questions=15
        )
        all_questions["subdivisions"].extend(subdivision_questions)
        
        # Генерируем вопросы из всех документов
        logger.info("Генерация вопросов из всех документов...")
        all_docs = self.load_documents_from_chroma(
            config.PERSIST_DIRECTORY_ALL_DOCS,
            max_docs=10
        )
        for doc in all_docs:
            questions = await self.generate_questions_from_document(
                doc["content"],
                category="all_docs"
            )
            all_questions["all_docs"].extend(questions)
        
        return all_questions
    
    def save_test_data(
        self,
        questions: Dict[str, List[TestQuestion]],
        output_file: Optional[str] = None
    ) -> str:
        """
        Сохраняет тестовые данные в JSON файл.
        
        Args:
            questions: Словарь с вопросами по категориям
            output_file: Имя выходного файла
            
        Returns:
            Путь к сохраненному файлу
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.output_dir, f"test_data_{timestamp}.json")
        
        # Преобразуем в формат для RAGAS
        ragas_data = []
        for category, category_questions in questions.items():
            for q in category_questions:
                ragas_data.append({
                    "question": q.question,
                    "ground_truth": q.ground_truth,
                    "category": q.category,
                    "source": q.source_doc
                })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(ragas_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Сохранено {len(ragas_data)} вопросов в {output_file}")
        
        # Сохраняем статистику
        stats = {
            "total_questions": len(ragas_data),
            "by_category": {
                cat: len(qs) for cat, qs in questions.items()
            },
            "generated_at": datetime.now().isoformat()
        }
        
        stats_file = output_file.replace(".json", "_stats.json")
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        return output_file
    
    def print_statistics(self, questions: Dict[str, List[TestQuestion]]):
        """Выводит статистику по сгенерированным вопросам."""
        print("\n" + "="*60)
        print("СТАТИСТИКА СГЕНЕРИРОВАННЫХ ВОПРОСОВ")
        print("="*60)
        
        total = 0
        for category, category_questions in questions.items():
            count = len(category_questions)
            total += count
            print(f"{category:20s}: {count:3d} вопросов")
        
        print("-"*60)
        print(f"{'ИТОГО':20s}: {total:3d} вопросов")
        print("="*60)


async def main():
    """Главная функция для генерации тестовых данных."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Генератор тестовых данных для RAG")
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="Модель для генерации вопросов"
    )
    parser.add_argument(
        "--questions-per-doc",
        type=int,
        default=3,
        help="Количество вопросов на документ"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="test_data",
        help="Директория для сохранения результатов"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Имя выходного файла"
    )
    
    args = parser.parse_args()
    
    # Проверяем наличие API ключа
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY не найден. Установите переменную окружения.")
        return
    
    # Инициализация генератора
    generator = TestDataGenerator(
        llm_model=args.model,
        questions_per_doc=args.questions_per_doc,
        output_dir=args.output_dir
    )
    
    # Генерация вопросов
    logger.info("Начало генерации тестовых данных...")
    questions = await generator.generate_all_test_data()
    
    # Вывод статистики
    generator.print_statistics(questions)
    
    # Сохранение результатов
    output_file = generator.save_test_data(questions, args.output_file)
    logger.info(f"Тестовые данные сохранены в: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
