# session.py
import uuid
from collections import deque
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging
import re

logger = logging.getLogger(__name__)

# Хранилище сессий: session_id -> данные
chat_sessions = {}

# Ключевые слова для детекции намерения правки
EDIT_KEYWORDS = [
    'измени', 'правка', 'добавь', 'удали', 'замени', 'исправь',
    'изменить', 'править', 'добавить', 'удалить', 'заменить', 'исправить',
    'обнови', 'обновить', 'переделай', 'переделать', 'скорректируй',
    'скорректировать', 'модифицируй', 'модифицировать', 'отредактируй',
    'отредактировать', 'внеси', 'внести', 'изменения', 'правки'
]


def is_edit_request(question: str) -> Tuple[bool, str]:
    """
    Определяет, является ли запрос запросом на правку плана.
    
    Args:
        question: Текст вопроса пользователя
    
    Returns:
        Кортеж (является_ли_правкой, тип_правки)
        Тип правки может быть: 'add', 'remove', 'replace', 'general'
    """
    if not question:
        return False, ""
    
    question_lower = question.lower()
    
    # Проверяем наличие ключевых слов правки
    has_edit_keyword = any(kw in question_lower for kw in EDIT_KEYWORDS)
    
    if not has_edit_keyword:
        return False, ""
    
    # Определяем тип правки
    if any(kw in question_lower for kw in ['добавь', 'добавить', 'включи', 'включить', 'дополн']):
        return True, "add"
    elif any(kw in question_lower for kw in ['удали', 'удалить', 'убери', 'убрать', 'исключи', 'исключить']):
        return True, "remove"
    elif any(kw in question_lower for kw in ['замени', 'заменить', 'измени', 'изменить', 'обнови', 'обновить']):
        return True, "replace"
    else:
        return True, "general"


def get_or_create_session(session_id: Optional[str] = None) -> str:
    """Получает существующую сессию или создает новую."""
    if not session_id:
        session_id = str(uuid.uuid4())

    if session_id not in chat_sessions:
        chat_sessions[session_id] = {
            "history": deque(maxlen=30),  # Увеличено с 10 до 30 для сохранения большего контекста
            "last_subdivisions": [],
            "last_technics": [],
            "last_employees": [],
            "last_work_plan": "",
            "created_at": datetime.now()
        }

    return session_id


def add_message_to_session(session_id: str, role: str, content: str, structured_data: Optional[Dict] = None):
    """
    Добавляет сообщение в историю сессии.
    
    Args:
        session_id: ID сессии
        role: Роль (user/assistant)
        content: Текст сообщения
        structured_data: Опциональные структурированные данные для режима plan
    """
    if session_id in chat_sessions:
        # Если переданы структурированные данные, сохраняем их напрямую
        if structured_data and role == "assistant":
            chat_sessions[session_id]["last_subdivisions"] = structured_data.get("subdivisions", [])
            chat_sessions[session_id]["last_technics"] = structured_data.get("technics", [])
            chat_sessions[session_id]["last_employees"] = structured_data.get("employees", [])
            chat_sessions[session_id]["last_work_plan"] = structured_data.get("work_plan", "")
        # Иначе пробуем извлечь из текста (fallback)
        elif role == "assistant":
            try:
                from response_processing import extract_subdivisions_from_model_response, extract_technics_from_model_response, extract_employees_from_model_response, extract_work_plan_from_model_response
                subdivisions = extract_subdivisions_from_model_response(content)
                technics = extract_technics_from_model_response(content)
                employees = extract_employees_from_model_response(content)
                work_plan = extract_work_plan_from_model_response(content)
                
                # Сохраняем только если что-то удалось извлечь
                if subdivisions or technics or employees or work_plan:
                    chat_sessions[session_id]["last_subdivisions"] = subdivisions
                    chat_sessions[session_id]["last_technics"] = technics
                    chat_sessions[session_id]["last_employees"] = employees
                    chat_sessions[session_id]["last_work_plan"] = work_plan
            except Exception as e:
                logger.warning(f"Не удалось извлечь структуру из ответа: {e}")

        chat_sessions[session_id]["history"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })


def get_last_subdivisions(session_id: str) -> List[str]:
    """Возвращает список подразделений из последнего ответа ассистента."""
    if session_id in chat_sessions:
        return chat_sessions[session_id].get("last_subdivisions", [])
    return []


def get_last_technics(session_id: str) -> List[str]:
    """Возвращает список техники из последнего ответа ассистента."""
    if session_id in chat_sessions:
        return chat_sessions[session_id].get("last_technics", [])
    return []


def get_last_employees(session_id: str) -> List[str]:
    """Возвращает список сотрудников из последнего ответа ассистента."""
    if session_id in chat_sessions:
        return chat_sessions[session_id].get("last_employees", [])
    return []


def set_last_employees(session_id: str, employees: List[str]):
    """Устанавливает список сотрудников для сессии (используется в процессе генерации)."""
    if session_id in chat_sessions:
        chat_sessions[session_id]["last_employees"] = employees


def get_last_work_plan(session_id: str) -> str:
    """Возвращает план работ из последнего ответа ассистента."""
    if session_id in chat_sessions:
        return chat_sessions[session_id].get("last_work_plan", "")
    return ""


def get_session_history(session_id: str) -> List[Dict[str, str]]:
    """Возвращает историю разговора для сессии."""
    if session_id in chat_sessions:
        return list(chat_sessions[session_id]["history"])
    return []


def format_history_for_prompt(history: List[Dict[str, str]], max_messages: int = 10) -> str:
    """
    Форматирует историю для включения в промпт.
    
    Args:
        history: История сообщений
        max_messages: Максимальное количество сообщений для включения (по умолчанию 10)
    
    Returns:
        Отформатированная история
    """
    if not history:
        return "История разговора отсутствует."

    formatted_history = []
    for msg in history[-max_messages:]:
        role = "Пользователь" if msg["role"] == "user" else "Ассистент"
        formatted_history.append(f"{role}: {msg['content']}")

    return "\n".join(formatted_history)