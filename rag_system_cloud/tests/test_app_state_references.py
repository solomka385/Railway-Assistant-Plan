# test_app_state_references.py
"""Тестовый скрипт для проверки предварительной загрузки справочников в app_state."""
import os
import sys

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app_state
import response_processing
import retrieval

def main():
    print("=" * 60)
    print("ТЕСТ ПРЕДВАРИТЕЛЬНОЙ ЗАГРУЗКИ СПРАВОЧНИКОВ")
    print("=" * 60)
    
    # Инициализация системы
    print("\n1. Инициализация системы...")
    if not app_state.init_system():
        print("   ОШИБКА: Не удалось инициализировать систему")
        return False
    print("   Система инициализирована успешно")
    
    # Проверка статуса системы
    print("\n2. Проверка статуса системы...")
    status = app_state.get_system_status()
    print(f"   Модель загружена: {status['model_loaded']}")
    print(f"   Справочник техники загружен: {status['technic_reference_loaded']}")
    print(f"   Справочник сотрудников загружен: {status['employees_reference_loaded']}")
    print(f"   Количество записей в справочнике техники: {len(app_state.technic_reference)}")
    print(f"   Количество записей в справочнике сотрудников: {len(app_state.employees_reference)}")
    
    # Тест получения справочников через response_processing
    print("\n3. Тест получения справочников через response_processing...")
    employees_ref = response_processing.get_employees_reference()
    technic_ref = response_processing.get_technic_reference()
    print(f"   Получено записей сотрудников: {len(employees_ref)}")
    print(f"   Получено записей техники: {len(technic_ref)}")
    
    # Проверка, что данные берутся из app_state
    print("\n4. Проверка источника данных...")
    if app_state.employees_reference:
        print("   ✓ Справочник сотрудников загружен из app_state")
        # Проверяем, что данные совпадают
        expected_employees = {item.get('должность', '').strip() for item in app_state.employees_reference if item.get('должность')}
        if employees_ref == expected_employees:
            print("   ✓ Данные совпадают с app_state.employees_reference")
        else:
            print("   ✗ Данные НЕ совпадают с app_state.employees_reference")
    else:
        print("   ✗ Справочник сотрудников НЕ загружен в app_state")
    
    if app_state.technic_reference:
        print("   ✓ Справочник техники загружен из app_state")
        # Проверяем, что данные совпадают
        expected_technic = {item.get('название_техники', '').strip() for item in app_state.technic_reference if item.get('название_техники')}
        if technic_ref == expected_technic:
            print("   ✓ Данные совпадают с app_state.technic_reference")
        else:
            print("   ✗ Данные НЕ совпадают с app_state.technic_reference")
    else:
        print("   ✗ Справочник техники НЕ загружен в app_state")
    
    # Тест получения справочников через retrieval
    print("\n5. Тест получения справочников через retrieval...")
    technic_data = retrieval.get_technic_reference_data()
    employees_data = retrieval.get_employees_reference_data()
    print(f"   Получено записей техники: {len(technic_data)}")
    print(f"   Получено записей сотрудников: {len(employees_data)}")
    
    # Проверка, что данные берутся из app_state
    if technic_data == app_state.technic_reference:
        print("   ✓ Данные техники совпадают с app_state.technic_reference")
    else:
        print("   ✗ Данные техники НЕ совпадают с app_state.technic_reference")
    
    if employees_data == app_state.employees_reference:
        print("   ✓ Данные сотрудников совпадают с app_state.employees_reference")
    else:
        print("   ✗ Данные сотрудников НЕ совпадают с app_state.employees_reference")
    
    # Тест форматирования справочников
    print("\n6. Тест форматирования справочников...")
    technic_formatted = retrieval.format_technic_reference_for_prompt(technic_data)
    employees_formatted = retrieval.format_employees_reference_for_prompt(employees_data)
    print(f"   Длина форматированного текста техники: {len(technic_formatted)} символов")
    print(f"   Длина форматированного текста сотрудников: {len(employees_formatted)} символов")
    
    print("\n" + "=" * 60)
    print("ТЕСТ ЗАВЕРШЁН УСПЕШНО")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
