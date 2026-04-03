# test_response_processing.py
"""
Тестовый скрипт для проверки улучшенных функций обработки ответов LLM.
"""
import sys
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Импорт функций
from response_processing import (
    extract_technics_from_model_response,
    extract_employees_from_model_response,
    reset_reference_cache
)


def test_technic_extraction():
    """Тестирование извлечения техники."""
    print("\n" + "="*80)
    print("ТЕСТ 1: Извлечение техники")
    print("="*80)
    
    # Пример ответа LLM с шумом
    test_response = """
    Необходимая техника:
    Боновые заграждения
    для локализации разливов нефтепродуктов на воде
    Сорбенты
    для сбора нефти
    Дезинфекционные установки
    для обработки территории
    Мобильные лаборатории НЦОП «ЭкоТест»
    для анализа почвы, воды, воздуха
    Пожарные поезда ПП
    с цистернами для воды и насосами для пожаротушения и локализации разливов
    В случае разлива нефтепродуктов из цистерны необходимо использовать боновые заграждения и сорбенты
    """
    
    result = extract_technics_from_model_response(test_response)
    print(f"\nРезультат: {result}")
    print(f"Количество элементов: {len(result)}")
    
    # Ожидаемый результат
    expected = ['Боновые заграждения', 'Сорбенты', 'Дезинфекционные установки', 
                'Мобильные лаборатории НЦОП «ЭкоТест»', 'Пожарные поезда ПП']
    
    print(f"\nОжидаемый результат: {expected}")
    print(f"Совпадение: {set(result) == set(expected)}")
    
    return result


def test_technic_extraction_with_markers():
    """Тестирование извлечения техники с маркерами списка."""
    print("\n" + "="*80)
    print("ТЕСТ 2: Извлечение техники с маркерами списка")
    print("="*80)
    
    test_response = """
    Необходимая техника:
    1. Экскаватор Э-153 - для расчистки завалов
    2. Кран КС-5371 - для подъёма конструкций
    3. Генератор ЯМЗ-238 - для обеспечения электроэнергией
    4. Пожарные машины АЦ-40 - для пожаротушения
    """
    
    result = extract_technics_from_model_response(test_response)
    print(f"\nРезультат: {result}")
    print(f"Количество элементов: {len(result)}")
    
    expected = ['Экскаватор Э-153', 'Кран КС-5371', 'Генератор ЯМЗ-238', 'Пожарные машины АЦ-40']
    print(f"\nОжидаемый результат: {expected}")
    print(f"Совпадение: {set(result) == set(expected)}")
    
    return result


def test_employee_extraction():
    """Тестирование извлечения сотрудников."""
    print("\n" + "="*80)
    print("ТЕСТ 3: Извлечение сотрудников")
    print("="*80)
    
    test_response = """
    Необходимые сотрудники:
    Машинист крана
    для управления краном при подъёме конструкций
    Монтёр пути
    для восстановления железнодорожного полотна
    Электромонтёр контактной сети
    для ремонта контактной сети
    Медицинский работник
    для оказания первой помощи пострадавшим
    """
    
    result = extract_employees_from_model_response(test_response)
    print(f"\nРезультат: {result}")
    print(f"Количество элементов: {len(result)}")
    
    expected = ['Машинист крана', 'Монтер пути', 'Электромонтер контактной сети', 'Медицинский работник']
    print(f"\nОжидаемый результат: {expected}")
    print(f"Совпадение: {set(result) == set(expected)}")
    
    return result


def test_employee_extraction_with_markers():
    """Тестирование извлечения сотрудников с маркерами списка."""
    print("\n" + "="*80)
    print("ТЕСТ 4: Извлечение сотрудников с маркерами списка")
    print("="*80)
    
    test_response = """
    Необходимые сотрудники:
    1. Пожарный - для тушения пожара
    2. Спасатель - для эвакуации пострадавших
    3. Врач-реаниматолог - для оказания медицинской помощи
    4. Фельдшер - для первой помощи
    """
    
    result = extract_employees_from_model_response(test_response)
    print(f"\nРезультат: {result}")
    print(f"Количество элементов: {len(result)}")
    
    expected = ['Пожарный', 'Спасатель', 'Врач-реаниматолог', 'Фельдшер']
    print(f"\nОжидаемый результат: {expected}")
    print(f"Совпадение: {set(result) == set(expected)}")
    
    return result


def test_fuzzy_matching():
    """Тестирование нечёткого сопоставления."""
    print("\n" + "="*80)
    print("ТЕСТ 5: Нечёткое сопоставление (опечатки)")
    print("="*80)
    
    test_response = """
    Необходимая техника:
    Боновые заграждения
    Сорбенты
    Экскаватор Э-153
    Кран КС-5371
    """
    
    result = extract_technics_from_model_response(test_response)
    print(f"\nРезультат: {result}")
    print(f"Количество элементов: {len(result)}")
    
    return result


def test_noise_filtering():
    """Тестирование фильтрации шума."""
    print("\n" + "="*80)
    print("ТЕСТ 6: Фильтрация шума")
    print("="*80)
    
    test_response = """
    Необходимая техника:
    для локализации разливов
    Боновые заграждения
    для сбора нефти
    Сорбенты
    и другие материалы
    """
    
    result = extract_technics_from_model_response(test_response)
    print(f"\nРезультат: {result}")
    print(f"Количество элементов: {len(result)}")
    
    expected = ['Боновые заграждения', 'Сорбенты']
    print(f"\nОжидаемый результат: {expected}")
    print(f"Совпадение: {set(result) == set(expected)}")
    
    return result


def main():
    """Запуск всех тестов."""
    print("\n" + "="*80)
    print("ЗАПУСК ТЕСТОВ УЛУЧШЕННОЙ ОБРАБОТКИ ОТВЕТОВ LLM")
    print("="*80)
    
    # Сброс кэша перед тестами
    reset_reference_cache()
    
    # Запуск тестов
    test_technic_extraction()
    test_technic_extraction_with_markers()
    test_employee_extraction()
    test_employee_extraction_with_markers()
    test_fuzzy_matching()
    test_noise_filtering()
    
    print("\n" + "="*80)
    print("ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
    print("="*80)


if __name__ == "__main__":
    main()
