"""
Тестовый скрипт для проверки работы функции extract_keywords
с новой конфигурацией ключевых слов.
"""

import sys
import os

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from retrieval import extract_keywords, get_keywords
import config

def test_keywords_loading():
    """Тест загрузки ключевых слов."""
    print("=" * 60)
    print("ТЕСТ 1: Загрузка ключевых слов")
    print("=" * 60)
    
    keywords = get_keywords()
    print(f"Загружено {len(keywords)} ключевых слов")
    print(f"Первые 10 ключевых слов: {keywords[:10]}")
    print(f"Путь к JSON файлу: {config.KEYWORDS_JSON_PATH}")
    print(f"Максимальное количество для извлечения: {config.MAX_KEYWORDS_TO_EXTRACT}")
    print()


def test_extract_keywords():
    """Тест извлечения ключевых слов из описания."""
    print("=" * 60)
    print("ТЕСТ 2: Извлечение ключевых слов")
    print("=" * 60)
    
    test_cases = [
        "Пожар на станции Москва, требуется эвакуация",
        "Сход поезда на перегоне, повреждение пути",
        "Утечка опасных грузов, требуется МЧС",
        "Обрыв контактной сети, остановка движения",
        "Наводнение на участке, повреждение насыпи",
        "Кибератака на систему сигнализации",
        "Обледенение контактной сети, требуется ремонт",
        "Столкновение вагонов, есть пострадавшие",
        "Взрыв на депо, требуется медицинская помощь",
        "Снегопад и метель, падение деревьев на пути"
    ]
    
    for i, description in enumerate(test_cases, 1):
        keywords = extract_keywords(description)
        print(f"{i}. Описание: {description}")
        print(f"   Найденные ключевые слова: {keywords}")
        print()


def test_empty_description():
    """Тест с пустым описанием."""
    print("=" * 60)
    print("ТЕСТ 3: Пустое описание")
    print("=" * 60)
    
    keywords = extract_keywords("")
    print(f"Результат для пустой строки: {keywords}")
    print()


def test_no_keywords_found():
    """Тест с описанием, где нет ключевых слов."""
    print("=" * 60)
    print("ТЕСТ 4: Нет совпадений")
    print("=" * 60)
    
    keywords = extract_keywords("Обычная рабочая ситуация без аварий")
    print(f"Описание: Обычная рабочая ситуация без аварий")
    print(f"Найденные ключевые слова: {keywords}")
    print()


def test_max_keywords_limit():
    """Тест ограничения количества ключевых слов."""
    print("=" * 60)
    print("ТЕСТ 5: Ограничение количества ключевых слов")
    print("=" * 60)
    
    # Описание с множеством ключевых слов
    description = (
        "Пожар, взрыв, сход, столкновение, утечка, повреждение, "
        "мост, тоннель, путь, поезд, вагон, локомотив, станция, "
        "сигнализация, связь, ремонт, эвакуация, авария, катастрофа"
    )
    keywords = extract_keywords(description)
    print(f"Описание содержит много ключевых слов")
    print(f"Найденные ключевые слова: {keywords}")
    print(f"Количество: {len(keywords)} (максимум: {config.MAX_KEYWORDS_TO_EXTRACT})")
    print()


if __name__ == "__main__":
    try:
        test_keywords_loading()
        test_extract_keywords()
        test_empty_description()
        test_no_keywords_found()
        test_max_keywords_limit()
        
        print("=" * 60)
        print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО")
        print("=" * 60)
        
    except Exception as e:
        print(f"ОШИБКА при выполнении тестов: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
