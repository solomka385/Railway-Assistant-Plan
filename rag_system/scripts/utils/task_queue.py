# task_queue.py
"""
Модуль очереди задач для асинхронного выполнения тяжёлых операций.
Решает проблему блокировки основного потока при индексации.
"""
import asyncio
import logging
import uuid
from enum import Enum
from typing import Dict, Optional, Callable, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Статусы задач в очереди."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task:
    """Класс задачи для очереди."""
    
    def __init__(self, task_id: str, func: Callable, *args, **kwargs):
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.status = TaskStatus.PENDING
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Преобразует задачу в словарь для API-ответа."""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": (
                (self.completed_at - self.started_at).total_seconds()
                if self.started_at and self.completed_at
                else None
            )
        }


class TaskQueue:
    """Очередь задач с фоновым воркером."""
    
    def __init__(self, max_concurrent_tasks: int = 1):
        """
        Инициализация очереди задач.
        
        Args:
            max_concurrent_tasks: Максимальное количество одновременно выполняемых задач
        """
        self.queue: asyncio.Queue = asyncio.Queue()
        self.tasks: Dict[str, Task] = {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.worker_task: Optional[asyncio.Task] = None
        self._running = False
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)
    
    async def start(self):
        """Запускает фоновый воркер для обработки задач."""
        if self._running:
            logger.warning("TaskQueue уже запущен")
            return
        
        self._running = True
        self.worker_task = asyncio.create_task(self._worker())
        logger.info("TaskQueue запущен")
    
    async def stop(self):
        """Останавливает воркер и завершает выполнение текущих задач."""
        if not self._running:
            return
        
        self._running = False
        
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        
        logger.info("TaskQueue остановлен")
    
    async def _worker(self):
        """Фоновый воркер для обработки задач из очереди."""
        logger.info("Воркер задач запущен")
        
        while self._running:
            try:
                # Получаем задачу из очереди с таймаутом для проверки флага _running
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                
                # Запускаем задачу с ограничением по количеству одновременных задач
                asyncio.create_task(self._execute_task(task))
                
            except asyncio.TimeoutError:
                # Таймаут - просто продолжаем цикл
                continue
            except Exception as e:
                logger.error(f"Ошибка в воркере: {e}", exc_info=True)
        
        logger.info("Воркер задач остановлен")
    
    async def _execute_task(self, task: Task):
        """Выполняет отдельную задачу."""
        async with self._semaphore:
            try:
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()
                logger.info(f"Начало выполнения задачи {task.task_id}")
                
                # Выполняем функцию в отдельном потоке, чтобы не блокировать event loop
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, task.func, *task.args, **task.kwargs)
                
                task.result = result
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                logger.info(f"Задача {task.task_id} выполнена успешно за {task.to_dict()['duration_seconds']:.2f} сек")
                
            except Exception as e:
                task.error = str(e)
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                logger.error(f"Задача {task.task_id} завершилась с ошибкой: {e}", exc_info=True)
            
            finally:
                self.queue.task_done()
    
    def add_task(self, func: Callable, *args, **kwargs) -> str:
        """
        Добавляет задачу в очередь.
        
        Args:
            func: Функция для выполнения
            *args: Позиционные аргументы функции
            **kwargs: Именованные аргументы функции
            
        Returns:
            ID задачи
        """
        task_id = str(uuid.uuid4())
        task = Task(task_id, func, *args, **kwargs)
        self.tasks[task_id] = task
        
        # Добавляем в очередь (создаём задачу для put, чтобы не блокировать)
        asyncio.create_task(self.queue.put(task))
        
        logger.info(f"Задача {task_id} добавлена в очередь")
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        Возвращает статус задачи.
        
        Args:
            task_id: ID задачи
            
        Returns:
            Словарь с информацией о задаче или None, если задача не найдена
        """
        task = self.tasks.get(task_id)
        if task:
            return task.to_dict()
        return None
    
    def get_all_tasks(self) -> Dict[str, Dict]:
        """
        Возвращает информацию о всех задачах.
        
        Returns:
            Словарь с информацией о всех задачах
        """
        return {task_id: task.to_dict() for task_id, task in self.tasks.items()}
    
    def get_queue_size(self) -> int:
        """Возвращает количество задач в очереди."""
        return self.queue.qsize()
    
    def get_running_count(self) -> int:
        """Возвращает количество выполняющихся задач."""
        return sum(1 for task in self.tasks.values() if task.status == TaskStatus.RUNNING)


# Глобальный экземпляр очереди задач
_global_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """
    Возвращает глобальный экземпляр очереди задач.
    Создаёт его при первом вызове.
    
    Returns:
        Экземпляр TaskQueue
    """
    global _global_task_queue
    if _global_task_queue is None:
        _global_task_queue = TaskQueue(max_concurrent_tasks=1)
    return _global_task_queue


async def init_task_queue():
    """Инициализирует и запускает глобальную очередь задач."""
    queue = get_task_queue()
    await queue.start()
    logger.info("Глобальная очередь задач инициализирована")


async def shutdown_task_queue():
    """Останавливает глобальную очередь задач."""
    global _global_task_queue
    if _global_task_queue is not None:
        await _global_task_queue.stop()
        _global_task_queue = None
        logger.info("Глобальная очередь задач остановлена")
