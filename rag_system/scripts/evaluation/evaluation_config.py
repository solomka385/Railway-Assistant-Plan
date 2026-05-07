# evaluation_config.py
"""
Конфигурация для оценки RAG системы с использованием RAGAS.
Поддерживает кастомные API endpoints (например, X5 API).
"""

import os
import sys
from typing import List, Dict, Any


class EvaluationConfig:
    """Конфигурация для оценки RAG системы."""
    
    # X5 API Configuration
    X5_API_BASE_URL = "https://api-copilot.x5.ru/aigw/v1"
    
    @classmethod
    def _load_env_file(cls):
        """Загружает переменные из .env файла."""
        env_file = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        if key not in os.environ:
                            os.environ[key] = value
    
    @classmethod
    def get_x5_api_key(cls) -> str:
        """Возвращает API ключ X5."""
        # Сначала пробуем загрузить из .env
        cls._load_env_file()
        
        # Проверяем переменную окружения
        api_key = os.getenv("X5_API_KEY")
        
        # Проверяем, не является ли это плейсхолдер
        if api_key and api_key not in ["API-TOKEN", "your-x5-api-key", "your-api-key"]:
            return api_key
        
        # Проверяем аргументы командной строки
        if len(sys.argv) > 1:
            for arg in sys.argv[1:]:
                if "--x5-api-key" in arg.lower():
                    parts = arg.split('=')
                    if len(parts) == 2:
                        return parts[1].strip('"\'')
        
        return None
    
    X5_API_KEY = property(get_x5_api_key)
    
    # Доступные модели X5
    X5_MODELS = {
        "copilot-flash": {
            "name": "Qwen3-coder-next - быстрая",
            "description": "Быстрая модель для кода и текста",
            "context_window": 131072
        },
        "copilot-code-large": {
            "name": "GLM 4.7 - лучшая размышляющая",
            "description": "Мощная размышляющая модель",
            "context_window": 147456
        },
        "x5-airun-large": {
            "name": "oldschool - резервный канал",
            "description": "Резервная модель",
            "context_window": 128000
        },
        "x5-airun-medium-vl-test": {
            "name": "Qwen3-32b-VL - размышляющая и для фото",
            "description": "Размышляющая модель с поддержкой изображений",
            "context_window": 256000
        }
    }
    
    # Модели для оценки по умолчанию
    DEFAULT_EVALUATION_MODEL = "copilot-flash"  # Qwen3-coder-next - быстрая, поддерживает автоматизацию
    DEFAULT_EMBEDDING_MODEL = "copilot-flash"  # Используем ту же модель для эмбеддингов
    
    # OpenAI fallback (если X5 недоступен)
    OPENAI_FALLBACK_MODEL = "gpt-4o-mini"
    OPENAI_FALLBACK_EMBEDDING = "text-embedding-3-small"
    
    # Альтернативные модели
    ALTERNATIVE_MODELS = {
        **X5_MODELS,
        "gpt-4o": "Мощная модель OpenAI для точной оценки",
        "gpt-4o-mini": "Быстрая и экономичная модель OpenAI",
        "gpt-3.5-turbo": "Базовая модель OpenAI",
    }
    
    # Директории
    EVALUATION_RESULTS_DIR = "evaluation_results"
    TEST_DATA_DIR = "test_data"
    
    # Метрики для оценки
    DEFAULT_METRICS = [
        "faithfulness",
        "answer_similarity",
        "context_precision",
        "context_recall"
    ]
    
    # Дополнительные метрики (опционально)
    OPTIONAL_METRICS = [
        "context_entity_recall",
        "answer_correctness"
    ]
    
    # Параметры генерации тестовых данных
    QUESTIONS_PER_DOCUMENT = 3
    MAX_DOCUMENTS_PER_CATEGORY = 20
    MAX_DOCUMENT_LENGTH = 4000
    
    # Параметры RAG системы для оценки
    RAG_CONFIG = {
        "max_context_docs": 5,
        "temperature": 0.2,
        "max_tokens": 4096
    }
    
    # Категории документов
    DOCUMENT_CATEGORIES = [
        "technic",
        "work_plan",
        "employees",
        "subdivisions",
        "all_docs"
    ]
    
    # Пороговые значения для метрик
    METRIC_THRESHOLDS = {
        "faithfulness": {
            "excellent": 0.9,
            "good": 0.7,
            "acceptable": 0.5
        },
        "answer_similarity": {
            "excellent": 0.9,
            "good": 0.7,
            "acceptable": 0.5
        },
        "context_precision": {
            "excellent": 0.85,
            "good": 0.65,
            "acceptable": 0.5
        },
        "context_recall": {
            "excellent": 0.85,
            "good": 0.65,
            "acceptable": 0.5
        }
    }
    
    @classmethod
    def get_model(cls) -> str:
        """Возвращает модель для оценки из переменной окружения или значение по умолчанию."""
        return os.getenv("RAGAS_EVAL_MODEL", cls.DEFAULT_EVALUATION_MODEL)
    
    @classmethod
    def get_embedding_model(cls) -> str:
        """Возвращает модель эмбеддингов из переменной окружения или значение по умолчанию."""
        return os.getenv("RAGAS_EMBEDDING_MODEL", cls.DEFAULT_EMBEDDING_MODEL)
    
    @classmethod
    def get_api_key(cls) -> str:
        """Возвращает API ключ (X5 или OpenAI)."""
        # Загружаем переменные из .env
        cls._load_env_file()
        
        # Приоритет: X5 API ключ
        x5_key = os.getenv("X5_API_KEY")
        if x5_key:
            return x5_key
        
        # Fallback на OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            return openai_key
        
        raise ValueError(
            "API ключ не найден. Установите одну из переменных окружения:\n"
            "export X5_API_KEY='your-x5-api-key'\n"
            "или\n"
            "export OPENAI_API_KEY='your-openai-api-key'\n"
            "или (Windows):\n"
            "set X5_API_KEY=your-x5-api-key\n"
            "set OPENAI_API_KEY=your-openai-api-key"
        )
    
    @classmethod
    def get_base_url(cls) -> str:
        """Возвращает базовый URL API."""
        # Если используется X5 модель
        model = cls.get_model()
        if model in cls.X5_MODELS:
            return cls.X5_API_BASE_URL
        
        # Для OpenAI используем стандартный URL (или кастомный из переменной)
        return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    @classmethod
    def is_x5_model(cls, model: str) -> bool:
        """Проверяет, является ли модель моделью X5."""
        return model in cls.X5_MODELS
    
    @classmethod
    def get_openai_api_key(cls) -> str:
        """Возвращает API ключ OpenAI (устаревший метод, используйте get_api_key)."""
        return cls.get_api_key()
    
    @classmethod
    def get_metrics(cls, include_optional: bool = False) -> List[str]:
        """Возвращает список метрик для оценки."""
        metrics = cls.DEFAULT_METRICS.copy()
        if include_optional:
            metrics.extend(cls.OPTIONAL_METRICS)
        return metrics
    
    @classmethod
    def get_metric_quality(cls, metric_name: str, value: float) -> str:
        """
        Возвращает качество метрики на основе пороговых значений.
        
        Args:
            metric_name: Название метрики
            value: Значение метрики
            
        Returns:
            Качество: excellent, good, acceptable, poor
        """
        thresholds = cls.METRIC_THRESHOLDS.get(metric_name, {})
        
        if value >= thresholds.get("excellent", 0.9):
            return "excellent"
        elif value >= thresholds.get("good", 0.7):
            return "good"
        elif value >= thresholds.get("acceptable", 0.5):
            return "acceptable"
        else:
            return "poor"
    
    @classmethod
    def get_quality_color(cls, quality: str) -> str:
        """Возвращает цвет для отображения качества."""
        colors = {
            "excellent": "\033[92m",  # Зеленый
            "good": "\033[94m",      # Синий
            "acceptable": "\033[93m", # Желтый
            "poor": "\033[91m"       # Красный
        }
        return colors.get(quality, "\033[0m")
    
    @classmethod
    def print_metric_summary(cls, metric_name: str, value: float):
        """Выводит сводку по метрике с цветовой индикацией."""
        quality = cls.get_metric_quality(metric_name, value)
        color = cls.get_quality_color(quality)
        reset = "\033[0m"
        
        quality_labels = {
            "excellent": "Отлично",
            "good": "Хорошо",
            "acceptable": "Приемлемо",
            "poor": "Плохо"
        }
        
        print(f"{color}{metric_name.upper():20s}: {value:.4f} ({quality_labels[quality]}){reset}")


# Примеры тестовых вопросов для быстрого старта
SAMPLE_TEST_DATA = [
    {
        "question": "Какие обязанности у ДГПС?",
        "ground_truth": "ДГПС (старший дорожный диспетчер по управлению перевозками) отвечает за управление перевозками, координацию движения поездов и оперативное решение вопросов на дороге.",
        "category": "subdivisions"
    },
    {
        "question": "Какая техника используется при пожарах?",
        "ground_truth": "При пожарах используется пожарная техника: пожарные автомобили, насосные станции, средства пожаротушения и специальное оборудование для ликвидации возгораний.",
        "category": "technic"
    },
    {
        "question": "Кто отвечает за восстановительные работы?",
        "ground_truth": "За восстановительные работы отвечает ДАВС (дирекция аварийно-восстановительных средств), которая координирует и проводит работы по восстановлению инфраструктуры.",
        "category": "subdivisions"
    },
    {
        "question": "Что такое МАБ?",
        "ground_truth": "МАБ - медицинская выездная врачебно-аварийная бригада, которая оказывает экстренную медицинскую помощь на месте происшествия.",
        "category": "subdivisions"
    },
    {
        "question": "Какие функции выполняет ДЦУП?",
        "ground_truth": "ДЦУП (диспетчерский центр управления перевозками) осуществляет оперативное управление перевозочным процессом, координацию работы станций и диспетчерских участков.",
        "category": "subdivisions"
    }
]


def get_config() -> EvaluationConfig:
    """Возвращает экземпляр конфигурации."""
    return EvaluationConfig()
