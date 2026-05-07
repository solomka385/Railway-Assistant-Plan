# ragas_evaluation.py
"""
Модуль для оценки качества RAG системы с использованием фреймворка RAGAS.

Поддерживаемые метрики:
- Faithfulness (Верность) - насколько ответ соответствует контексту
- Answer Relevance (Релевантность ответа) - насколько ответ соответствует вопросу
- Context Precision (Точность контекста) - доля релевантных документов
- Context Recall (Полнота контекста) - доля найденных релевантных документов
- Context Entity Recall (Полнота сущностей контекста)
- Answer Correctness (Правильность ответа) - сходство с эталонным ответом

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
from dataclasses import dataclass, asdict
from datetime import datetime

import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_similarity,
    context_precision,
    context_recall,
    context_entity_recall,
    answer_correctness
)
from ragas.llms import LangchainLLMWrapper
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from scripts.evaluation.evaluation_config import EvaluationConfig
from scripts.rag import app_state
from scripts.rag import retrieval
from scripts.rag import async_rag

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Результат оценки одного запроса."""
    question: str
    answer: str
    contexts: List[str]
    ground_truth: str
    faithfulness: Optional[float] = None
    answer_similarity: Optional[float] = None
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    context_entity_recall: Optional[float] = None
    answer_correctness: Optional[float] = None


class RAGEvaluator:
    """Класс для оценки RAG системы с использованием RAGAS."""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        embedding_model: Optional[str] = None,
        results_dir: str = "evaluation_results"
    ):
        """
        Инициализация оценщика RAG.
        
        Args:
            model_name: Название модели для оценки (по умолчанию из конфигурации)
            embedding_model: Название модели эмбеддингов (по умолчанию из конфигурации)
            results_dir: Директория для сохранения результатов
        """
        # Получаем конфигурацию
        self.model_name = model_name or EvaluationConfig.get_model()
        self.embedding_model = embedding_model or EvaluationConfig.get_embedding_model()
        self.results_dir = results_dir
        
        # Создаем директорию для результатов
        os.makedirs(results_dir, exist_ok=True)
        
        # Настраиваем LLM для RAGAS
        self._setup_llm()
        
        # Настраиваем эмбеддинги для RAGAS
        self._setup_embeddings()
        
        # Проверяем наличие API ключа
        try:
            api_key = EvaluationConfig.get_api_key()
            logger.info(f"Используется модель: {self.model_name}")
            logger.info(f"API Base URL: {EvaluationConfig.get_base_url()}")
        except ValueError as e:
            logger.error(f"Ошибка конфигурации API: {e}")
            raise
    
    def _setup_llm(self):
        """Настраивает LLM для RAGAS с поддержкой X5 API."""
        base_url = EvaluationConfig.get_base_url()
        api_key = EvaluationConfig.get_api_key()
        
        # Создаем LangChain ChatOpenAI с кастомным base_url
        self.llm = ChatOpenAI(
            model=self.model_name,
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=0.1,  # Низкая температура для стабильной оценки
            request_timeout=60
        )
        
        # Оборачиваем для RAGAS
        self.ragas_llm = LangchainLLMWrapper(self.llm)
    
    def _setup_embeddings(self):
        """Настраивает эмбеддинги для RAGAS с поддержкой X5 API."""
        base_url = EvaluationConfig.get_base_url()
        api_key = EvaluationConfig.get_api_key()
        
        # Создаем LangChain OpenAIEmbeddings с кастомным base_url
        self.embeddings = OpenAIEmbeddings(
            model=self.embedding_model,
            openai_api_key=api_key,
            openai_api_base=base_url
        )
    
    async def get_rag_response(self, question: str) -> tuple[str, List[str]]:
        """
        Получает ответ от RAG системы.
        
        Args:
            question: Вопрос пользователя
            
        Returns:
            Кортеж (ответ, список контекстов)
        """
        try:
            # Получаем документы через retrieval
            docs = []
            if app_state.retriever_all_docs:
                docs.extend(retrieval.enhanced_retriever(app_state.retriever_all_docs, question))
            else:
                if app_state.retriever_work_plan:
                    docs.extend(retrieval.enhanced_retriever(app_state.retriever_work_plan, question))
                if app_state.retriever_subdivisions and len(docs) < 3:
                    docs.extend(retrieval.enhanced_retriever(app_state.retriever_subdivisions, question))
                if app_state.retriever_technic and len(docs) < 3:
                    docs.extend(retrieval.enhanced_retriever(app_state.retriever_technic, question))
            
            # Форматируем контексты
            contexts = [doc.page_content for doc in docs[:5]]
            
            # Получаем ответ от модели
            response_tokens = []
            async for token in async_rag.async_get_chat_response(question):
                response_tokens.append(token)
            
            answer = "".join(response_tokens)
            
            return answer, contexts
            
        except Exception as e:
            logger.error(f"Ошибка при получении ответа RAG: {e}", exc_info=True)
            return f"Ошибка: {str(e)}", []
    
    def load_test_data(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Загружает тестовые данные из JSON или CSV файла.
        
        Формат JSON:
        [
            {
                "question": "Вопрос",
                "ground_truth": "Эталонный ответ",
                "contexts": ["Контекст 1", "Контекст 2"]  # опционально
            }
        ]
        
        Формат CSV:
        question,ground_truth,contexts
        "Вопрос","Эталонный ответ","Контекст 1|Контекст 2"
        
        Args:
            file_path: Путь к файлу с тестовыми данными
            
        Returns:
            Список словарей с тестовыми данными
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        if file_path.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        elif file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
            data = []
            for _, row in df.iterrows():
                item = {
                    "question": row.get("question", ""),
                    "ground_truth": row.get("ground_truth", ""),
                }
                if "contexts" in row and pd.notna(row["contexts"]):
                    item["contexts"] = str(row["contexts"]).split("|")
                data.append(item)
            return data
        else:
            raise ValueError("Неподдерживаемый формат файла. Используйте JSON или CSV.")
    
    async def evaluate_single(
        self,
        question: str,
        ground_truth: str,
        contexts: Optional[List[str]] = None
    ) -> EvaluationResult:
        """
        Оценивает один запрос.
        
        Args:
            question: Вопрос
            ground_truth: Эталонный ответ
            contexts: Предоставленные контексты (опционально)
            
        Returns:
            Результат оценки
        """
        logger.info(f"Оценка вопроса: {question}")
        
        # Получаем ответ и контексты от RAG системы
        answer, retrieved_contexts = await self.get_rag_response(question)
        
        # Используем предоставленные контексты или полученные от RAG
        final_contexts = contexts if contexts else retrieved_contexts
        
        result = EvaluationResult(
            question=question,
            answer=answer,
            contexts=final_contexts,
            ground_truth=ground_truth
        )
        
        return result
    
    async def evaluate_batch(
        self,
        test_data: List[Dict[str, Any]],
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Оценивает пакет запросов с использованием RAGAS.
        
        Args:
            test_data: Список тестовых данных
            metrics: Список метрик для оценки (опционально)
            
        Returns:
            Словарь с результатами оценки
        """
        logger.info(f"Начало оценки {len(test_data)} запросов")
        
        # Подготавливаем данные для RAGAS
        ragas_data = {
            "question": [],
            "answer": [],
            "contexts": [],
            "ground_truth": []
        }
        
        # Получаем ответы для всех запросов
        for item in test_data:
            question = item.get("question", "")
            ground_truth = item.get("ground_truth", "")
            provided_contexts = item.get("contexts")
            
            answer, contexts = await self.get_rag_response(question)
            
            ragas_data["question"].append(question)
            ragas_data["answer"].append(answer)
            ragas_data["contexts"].append(contexts if not provided_contexts else provided_contexts)
            ragas_data["ground_truth"].append(ground_truth)
        
        # Создаем Dataset для RAGAS
        dataset = Dataset.from_dict(ragas_data)
        
        # Определяем метрики
        if metrics is None:
            metrics = [
                faithfulness,
                answer_similarity,
                context_precision,
                context_recall
            ]
        
        # Выполняем оценку
        logger.info("Выполнение оценки с RAGAS...")
        result = evaluate(
            dataset=dataset,
            metrics=metrics,
            llm=self.ragas_llm,
            embeddings=self.embeddings
        )
        
        # Преобразуем результат в DataFrame
        df = result.to_pandas()
        
        # Сохраняем результаты
        results_file = os.path.join(self.results_dir, "evaluation_results.csv")
        df.to_csv(results_file, index=False, encoding='utf-8')
        logger.info(f"Результаты сохранены в: {results_file}")
        
        # Вычисляем средние значения
        summary = {
            "total_queries": len(test_data),
            "metrics": {}
        }
        
        for metric in metrics:
            metric_name = metric.name
            if metric_name in df.columns:
                summary["metrics"][metric_name] = {
                    "mean": float(df[metric_name].mean()),
                    "std": float(df[metric_name].std()),
                    "min": float(df[metric_name].min()),
                    "max": float(df[metric_name].max())
                }
        
        # Сохраняем сводку
        summary_file = os.path.join(self.results_dir, "summary.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        logger.info(f"Сводка сохранена в: {summary_file}")
        
        return summary
    
    def print_summary(self, summary: Dict[str, Any]):
        """Выводит сводку результатов оценки."""
        print("\n" + "="*60)
        print("СВОДКА РЕЗУЛЬТАТОВ ОЦЕНКИ RAG СИСТЕМЫ")
        print("="*60)
        print(f"Всего запросов: {summary['total_queries']}")
        print("\nМетрики:")
        print("-"*60)
        
        for metric_name, values in summary["metrics"].items():
            print(f"\n{metric_name.upper()}:")
            print(f"  Среднее: {values['mean']:.4f}")
            print(f"  Std:     {values['std']:.4f}")
            print(f"  Min:     {values['min']:.4f}")
            print(f"  Max:     {values['max']:.4f}")
        
        print("\n" + "="*60)
    
    def generate_test_data_template(self, output_path: str = "test_data_template.json"):
        """
        Генерирует шаблон файла с тестовыми данными.
        
        Args:
            output_path: Путь для сохранения шаблона
        """
        template = [
            {
                "question": "Какие обязанности у ДГПС?",
                "ground_truth": "ДГПС (старший дорожный диспетчер по управлению перевозками) отвечает за...",
                "contexts": [
                    "ДГПС - старший дорожный диспетчер по управлению перевозками...",
                    "Основные обязанности ДГПС включают..."
                ]
            },
            {
                "question": "Какая техника используется при пожарах?",
                "ground_truth": "При пожарах используется следующая техника: пожарные машины, насосные станции...",
                "contexts": []
            },
            {
                "question": "Кто отвечает за восстановительные работы?",
                "ground_truth": "За восстановительные работы отвечает ДАВС (дирекция аварийно-восстановительных средств)...",
                "contexts": []
            }
        ]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Шаблон сохранен в: {output_path}")


async def main():
    """Главная функция для запуска оценки."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Оценка RAG системы с использованием RAGAS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Доступные модели X5:
  copilot-flash              - Qwen3-coder-next (быстрая)
  copilot-code-large         - GLM 4.7 (лучшая размышляющая)
  x5-airun-large           - oldschool (резервный канал)
  x5-airun-medium-vl-test  - Qwen3-32b-VL (с поддержкой изображений)

Доступные модели OpenAI:
  gpt-4o, gpt-4o-mini, gpt-3.5-turbo

Переменные окружения:
  X5_API_KEY              - API ключ для X5 моделей
  OPENAI_API_KEY           - API ключ для OpenAI моделей
  RAGAS_EVAL_MODEL         - Модель для оценки (по умолчанию)
  RAGAS_EMBEDDING_MODEL   - Модель эмбеддингов (по умолчанию)
        """
    )
    parser.add_argument(
        "--test-data",
        type=str,
        default="../test_data/accident_scenarios.json",
        help="Путь к файлу с тестовыми данными (JSON или CSV)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Модель для оценки (по умолчанию: copilot-code-large)"
    )
    parser.add_argument(
        "--embedding",
        type=str,
        default=None,
        help="Модель эмбеддингов (по умолчанию: copilot-code-large)"
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default="../evaluation_results",
        help="Директория для сохранения результатов"
    )
    parser.add_argument(
        "--generate-template",
        action="store_true",
        help="Сгенерировать шаблон тестовых данных"
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Показать список доступных моделей"
    )
    
    args = parser.parse_args()
    
    # Показать список моделей
    if args.list_models:
        print("\nДоступные модели X5:")
        for model_id, model_info in EvaluationConfig.X5_MODELS.items():
            print(f"  {model_id:30s} - {model_info['name']}")
        print("\nДоступные модели OpenAI:")
        print("  gpt-4o")
        print("  gpt-4o-mini")
        print("  gpt-3.5-turbo")
        return
    
    # Инициализация оценщика
    try:
        evaluator = RAGEvaluator(
            model_name=args.model,
            embedding_model=args.embedding,
            results_dir=args.results_dir
        )
    except ValueError as e:
        logger.error(f"Ошибка инициализации: {e}")
        return
    
    # Генерация шаблона
    if args.generate_template:
        evaluator.generate_test_data_template()
        return
    
    # Загрузка тестовых данных
    try:
        test_data = evaluator.load_test_data(args.test_data)
        logger.info(f"Загружено {len(test_data)} тестовых запросов")
    except Exception as e:
        logger.error(f"Ошибка загрузки тестовых данных: {e}")
        return
    
    # Выполнение оценки
    summary = await evaluator.evaluate_batch(test_data)
    
    # Вывод результатов
    evaluator.print_summary(summary)


if __name__ == "__main__":
    asyncio.run(main())
