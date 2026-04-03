# test_task_queue.py
"""
Тестовый скрипт для проверки работы очереди задач.
"""
import asyncio
import time
from task_queue import TaskQueue, init_task_queue, shutdown_task_queue


def heavy_operation(seconds: int) -> str:
    """Имитация тяжёлой операции (индексации)."""
    print(f"[ТЯЖЁЛАЯ ОПЕРАЦИЯ] Начало, будет выполняться {seconds} сек...")
    time.sleep(seconds)
    print(f"[ТЯЖЁЛАЯ ОПЕРАЦИЯ] Завершена")
    return f"Операция выполнена за {seconds} секунд"


async def test_basic_queue():
    """Базовый тест очереди задач."""
    print("\n=== ТЕСТ 1: Базовая работа очереди ===")
    
    queue = TaskQueue(max_concurrent_tasks=1)
    await queue.start()
    
    # Добавляем задачу
    task_id = queue.add_task(heavy_operation, 2)
    print(f"Задача добавлена: {task_id}")
    
    # Проверяем статус
    await asyncio.sleep(0.5)
    status = queue.get_task_status(task_id)
    print(f"Статус задачи: {status}")
    
    # Ждём завершения
    await asyncio.sleep(2.5)
    status = queue.get_task_status(task_id)
    print(f"Финальный статус: {status}")
    
    await queue.stop()
    print("ТЕСТ 1 ПРОЙДЕН ✓\n")


async def test_multiple_tasks():
    """Тест нескольких задач в очереди."""
    print("=== ТЕСТ 2: Несколько задач ===")
    
    queue = TaskQueue(max_concurrent_tasks=1)
    await queue.start()
    
    # Добавляем несколько задач
    task_ids = []
    for i in range(3):
        task_id = queue.add_task(heavy_operation, 1)
        task_ids.append(task_id)
        print(f"Задача {i+1} добавлена: {task_id}")
    
    print(f"Размер очереди: {queue.get_queue_size()}")
    print(f"Выполняется задач: {queue.get_running_count()}")
    
    # Проверяем статусы
    await asyncio.sleep(0.5)
    for i, task_id in enumerate(task_ids):
        status = queue.get_task_status(task_id)
        print(f"Задача {i+1} статус: {status['status']}")
    
    # Ждём завершения всех задач
    await asyncio.sleep(4)
    
    for i, task_id in enumerate(task_ids):
        status = queue.get_task_status(task_id)
        print(f"Задача {i+1} финальный статус: {status['status']}, результат: {status['result']}")
    
    await queue.stop()
    print("ТЕСТ 2 ПРОЙДЕН ✓\n")


async def test_concurrent_tasks():
    """Тест параллельного выполнения задач."""
    print("=== ТЕСТ 3: Параллельное выполнение ===")
    
    queue = TaskQueue(max_concurrent_tasks=2)
    await queue.start()
    
    # Добавляем задачи
    task_ids = []
    for i in range(4):
        task_id = queue.add_task(heavy_operation, 1)
        task_ids.append(task_id)
        print(f"Задача {i+1} добавлена: {task_id}")
    
    print(f"Размер очереди: {queue.get_queue_size()}")
    print(f"Выполняется задач: {queue.get_running_count()}")
    
    # Ждём завершения
    await asyncio.sleep(3)
    
    for i, task_id in enumerate(task_ids):
        status = queue.get_task_status(task_id)
        print(f"Задача {i+1}: {status['status']}, длительность: {status['duration_seconds']:.2f} сек")
    
    await queue.stop()
    print("ТЕСТ 3 ПРОЙДЕН ✓\n")


async def test_error_handling():
    """Тест обработки ошибок."""
    print("=== ТЕСТ 4: Обработка ошибок ===")
    
    def failing_operation():
        """Операция, которая вызывает ошибку."""
        raise ValueError("Тестовая ошибка")
    
    queue = TaskQueue(max_concurrent_tasks=1)
    await queue.start()
    
    task_id = queue.add_task(failing_operation)
    print(f"Задача с ошибкой добавлена: {task_id}")
    
    # Ждём завершения
    await asyncio.sleep(1)
    
    status = queue.get_task_status(task_id)
    print(f"Статус: {status}")
    print(f"Ошибка: {status['error']}")
    
    await queue.stop()
    print("ТЕСТ 4 ПРОЙДЕН ✓\n")


async def main():
    """Запуск всех тестов."""
    print("=" * 50)
    print("НАЧАЛО ТЕСТИРОВАНИЯ ОЧЕРЕДИ ЗАДАЧ")
    print("=" * 50)
    
    try:
        await test_basic_queue()
        await test_multiple_tasks()
        await test_concurrent_tasks()
        await test_error_handling()
        
        print("=" * 50)
        print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО ✓")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА В ТЕСТАХ: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
