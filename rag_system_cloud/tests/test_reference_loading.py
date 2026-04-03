# test_reference_loading.py
"""Тестовый скрипт для проверки загрузки справочников."""
import os
import sys
import csv

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import TECHNIC_REFERENCE_CSV, EMPLOYEES_REFERENCE_CSV
from retrieval import format_technic_reference_for_prompt, format_employees_reference_for_prompt

def load_reference_csv(csv_file_path: str) -> list:
    """Загружает справочник из CSV-файла (разделитель ;)."""
    reference = []
    try:
        print(f"[CSV] Попытка загрузить справочник: {csv_file_path}")
        abs_path = os.path.abspath(csv_file_path)
        if os.path.exists(abs_path):
            with open(abs_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                for row in reader:
                    reference.append(dict(row))
            print(f"[CSV] Загружено {len(reference)} записей из справочника.")
        else:
            print(f"[CSV] Файл {abs_path} не найден")
    except Exception as e:
        print(f"[CSV] Ошибка загрузки справочника: {e}")
    return reference

def main():
    print("=" * 60)
    print("ТЕСТ ЗАГРУЗКИ СПРАВОЧНИКОВ")
    print("=" * 60)
    
    # Загрузка справочника техники
    print("\n1. Загрузка справочника техники...")
    technic_ref = load_reference_csv(TECHNIC_REFERENCE_CSV)
    print(f"   Загружено {len(technic_ref)} записей")
    
    # Загрузка справочника сотрудников
    print("\n2. Загрузка справочника сотрудников...")
    employees_ref = load_reference_csv(EMPLOYEES_REFERENCE_CSV)
    print(f"   Загружено {len(employees_ref)} записей")
    
    # Тест форматирования справочника техники
    print("\n3. Тест форматирования справочника техники (все записи)...")
    technic_formatted = format_technic_reference_for_prompt(technic_ref)
    print(f"   Длина форматированного текста: {len(technic_formatted)} символов")
    print(f"   Первые 500 символов:\n{technic_formatted[:500]}")
    
    # Тест форматирования справочника техники с фильтрацией
    print("\n4. Тест форматирования справочника техники (фильтр по ДАВС)...")
    technic_filtered = format_technic_reference_for_prompt(technic_ref, ["ДАВС"])
    print(f"   Длина форматированного текста: {len(technic_filtered)} символов")
    print(f"   Первые 500 символов:\n{technic_filtered[:500]}")
    
    # Тест форматирования справочника сотрудников
    print("\n5. Тест форматирования справочника сотрудников (все записи)...")
    employees_formatted = format_employees_reference_for_prompt(employees_ref)
    print(f"   Длина форматированного текста: {len(employees_formatted)} символов")
    print(f"   Первые 500 символов:\n{employees_formatted[:500]}")
    
    # Тест форматирования справочника сотрудников с фильтрацией
    print("\n6. Тест форматирования справочника сотрудников (фильтр по ДАВС)...")
    employees_filtered = format_employees_reference_for_prompt(employees_ref, ["ДАВС"])
    print(f"   Длина форматированного текста: {len(employees_filtered)} символов")
    print(f"   Первые 500 символов:\n{employees_filtered[:500]}")
    
    print("\n" + "=" * 60)
    print("ТЕСТ ЗАВЕРШЁН УСПЕШНО")
    print("=" * 60)

if __name__ == "__main__":
    main()
