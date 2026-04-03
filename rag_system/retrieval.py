# retrieval.py
import logging
from typing import List, Dict, Tuple, Optional
import os
import json

import app_state
import config

logger = logging.getLogger(__name__)


def _load_keywords_from_json() -> List[str]:
    """
    Загружает ключевые слова из JSON файла.
    Если файл не существует или содержит ошибки, возвращает пустой список.
    """
    try:
        if os.path.exists(config.KEYWORDS_JSON_PATH):
            with open(config.KEYWORDS_JSON_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                keywords = data.get('accident_keywords', [])
                logger.info(f"Загружено {len(keywords)} ключевых слов из {config.KEYWORDS_JSON_PATH}")
                return keywords
    except Exception as e:
        logger.warning(f"Ошибка загрузки ключевых слов из JSON: {e}")
    return []


def get_keywords() -> List[str]:
    """
    Возвращает список ключевых слов для извлечения из описания аварий.
    Приоритет: JSON файл > конфигурация в config.py.
    """
    # Сначала пробуем загрузить из JSON файла
    json_keywords = _load_keywords_from_json()
    if json_keywords:
        return json_keywords
    
    # Если JSON не загрузился, используем значения из config.py
    logger.info("Использование ключевых слов из config.py")
    return config.ACCIDENT_KEYWORDS


def get_technic_reference_data() -> List[Dict]:
    """
    Возвращает справочник техники из app_state.
    Используется для форматирования в промпт.
    """
    if app_state.technic_reference:
        return app_state.technic_reference
    logger.warning("Справочник техники не загружен в app_state")
    return []


def get_employees_reference_data() -> List[Dict]:
    """
    Возвращает справочник сотрудников из app_state.
    Используется для форматирования в промпт.
    """
    if app_state.employees_reference:
        return app_state.employees_reference
    logger.warning("Справочник сотрудников не загружен в app_state")
    return []


def extract_keywords(description: str) -> List[str]:
    """
    Извлекает ключевые слова из описания ситуации.
    
    Ключевые слова загружаются из JSON файла (keywords.json) или из config.py.
    Максимальное количество извлекаемых ключевых слов настраивается через
    MAX_KEYWORDS_TO_EXTRACT в config.py или через переменную окружения.
    
    Args:
        description: Текстовое описание аварийной ситуации
        
    Returns:
        Список найденных ключевых слов (уникальных, до MAX_KEYWORDS_TO_EXTRACT)
    """
    if not description:
        return []

    description_lower = description.lower()
    base_keywords = get_keywords()
    
    found_keywords = [kw for kw in base_keywords if kw in description_lower]
    
    # Используем значение из config.py для ограничения количества
    max_keywords = config.MAX_KEYWORDS_TO_EXTRACT
    return list(set(found_keywords))[:max_keywords]


def enhanced_retriever(retriever, question: str, max_docs: int = 15, filter_subdivision: str = None):
    """
    Расширенный поиск: по исходному запросу + по ключевым словам,
    удаление дубликатов. Использует multi-query retrieval для оптимизации.
    
    Args:
        retriever: Ретривер для поиска
        question: Текст запроса
        max_docs: Максимальное количество документов
        filter_subdivision: Опциональный фильтр по коду подразделения
    """
    if not question or retriever is None:
        return []

    keywords = extract_keywords(question)

    try:
        # Используем invoke вместо устаревшего get_relevant_documents
        main_results = retriever.invoke(question)
    except Exception as e:
        logger.warning(f"Ошибка получения основных результатов: {e}")
        main_results = []

    # Multi-query retrieval: объединяем ключевые слова в один запрос
    keyword_results = []
    if keywords:
        # Создаем составной запрос из ключевых слов
        # Используем оператор OR для поиска по любому из ключевых слов
        combined_query = " OR ".join(keywords)
        
        try:
            keyword_docs = retriever.invoke(combined_query)
            keyword_results.extend(keyword_docs)
            logger.debug(f"Multi-query retrieval: найдено {len(keyword_docs)} документов по запросу '{combined_query}'")
        except Exception as e:
            logger.warning(f"Ошибка при multi-query по ключевым словам: {e}")
            # Fallback: если составной запрос не сработал, пробуем по отдельности
            for keyword in keywords:
                try:
                    keyword_docs = retriever.invoke(keyword)
                    keyword_results.extend(keyword_docs)
                except Exception as e2:
                    logger.warning(f"Ошибка по ключевому слову '{keyword}': {e2}")

    all_docs = main_results + keyword_results
    
    # Фильтрация по подразделению, если указан
    if filter_subdivision:
        all_docs = [doc for doc in all_docs
                   if hasattr(doc, 'metadata') and
                   doc.metadata.get('subdivision') == filter_subdivision]
        logger.debug(f"Фильтрация по подразделению '{filter_subdivision}': {len(all_docs)} документов")
    
    unique_docs = []
    seen_ids = set()
    for doc in all_docs:
        # Используем составной идентификатор: page_content + source (источник документа)
        # Это позволяет сохранять документы с одинаковым содержанием, но из разных источников
        if hasattr(doc, 'page_content'):
            doc_id = doc.page_content
            # Добавляем источник в идентификатор, если он есть в метаданных
            if hasattr(doc, 'metadata') and doc.metadata:
                source = doc.metadata.get('source', '')
                if source:
                    doc_id = f"{doc.page_content}|{source}"
            
            if doc_id not in seen_ids:
                unique_docs.append(doc)
                seen_ids.add(doc_id)

    return unique_docs[:max_docs]


def format_docs(docs) -> str:
    """Форматирует документы в простую строку."""
    if not docs:
        return "Нет информации о подразделениях"
    return "\n\n".join([d.page_content for d in docs])


def format_docs_with_sources(docs) -> Tuple[str, List[Dict]]:
    """Форматирует документы с указанием источников и возвращает также список источников."""
    if not docs:
        return "Нет информации о подразделениях", []

    formatted_text = ""
    sources = []

    for i, doc in enumerate(docs, 1):
        if hasattr(doc, 'page_content') and doc.page_content.strip():
            # Извлекаем имя файла из метаданных
            source_file = "Неизвестный файл"
            if hasattr(doc, 'metadata'):
                full_path = doc.metadata.get('source', '')
                if full_path:
                    source_file = os.path.basename(full_path)

            formatted_text += f"[Документ {i}] {doc.page_content}\n\n"
            sources.append({
                "document_id": i,
                "source_file": source_file,
                "content_preview": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            })

    return formatted_text, sources

def format_subdivisions_examples_for_prompt(examples_docs: List) -> str:
    """Форматирует найденные документы примеров подразделений для вставки в промпт."""
    if not examples_docs:
        return "Похожие примеры отсутствуют."
    formatted = []
    for i, doc in enumerate(examples_docs[:3], 1):
        # doc.page_content содержит текст вида "Авария: ...\nНеобходимые подразделения: ..."
        formatted.append(f"Пример {i}:\n{doc.page_content}")
    return "\n\n".join(formatted)

def format_employees_examples_for_prompt(examples: List[Dict], limit: int = 5) -> str:
    if not examples:
        return "Примеры аварий и задействованных сотрудников отсутствуют."
    formatted = []
    for i, ex in enumerate(examples[:limit], 1):
        employees_str = "; ".join(ex['employees'])
        formatted.append(f"{i}. {ex['description']}\n   Сотрудники: {employees_str}")
    return "\n\n".join(formatted)

def format_examples_for_prompt(examples: List[Dict[str, str]], limit: int = 5) -> str:
    """Форматирует примеры аварий для включения в промпт."""
    if not examples:
        return "Примеры аварий отсутствуют"

    formatted = []
    for i, ex in enumerate(examples[:limit], 1):
        formatted.append(f"{i}. {ex['description']}\n   Подразделения: {ex['subdivisions']}")
    return "\n\n".join(formatted)

def format_technic_reference_for_prompt(technic_ref: List[Dict], subdivisions: List[str] = None) -> str:
    """Форматирует справочник техники для включения в промпт, фильтруя по подразделениям."""
    if not technic_ref:
        return "Справочник техники не загружен."
    
    filtered = technic_ref
    if subdivisions:
        # Фильтруем по указанным подразделениям
        filtered = [t for t in technic_ref if t.get('подразделение', '') in subdivisions]
    
    if not filtered:
        return "Для указанных подразделений техника не найдена в справочнике."
    
    formatted = ["СПРАВОЧНИК ТЕХНИКИ:"]
    for i, item in enumerate(filtered[:250], 1):  # Ограничиваем 50 записями
        name = item.get('название_техники', '')
        dept = item.get('подразделение', '')
        purpose = item.get('назначение', '')
        formatted.append(f"{i}. {name} ({dept}) - {purpose}")
    
    return "\n".join(formatted)

def format_employees_reference_for_prompt(employees_ref: List[Dict], subdivisions: List[str] = None) -> str:
    """Форматирует справочник сотрудников для включения в промпт, фильтруя по подразделениям."""
    if not employees_ref:
        return "Справочник сотрудников не загружен."
    
    filtered = employees_ref
    if subdivisions:
        # Фильтруем по указанным подразделениям
        filtered = [e for e in employees_ref if e.get('подразделение', '') in subdivisions]
    
    if not filtered:
        return "Для указанных подразделений сотрудники не найдены в справочнике."
    
    formatted = ["СПРАВОЧНИК СОТРУДНИКОВ:"]
    for i, item in enumerate(filtered[:250], 1):  # Ограничиваем 50 записями
        position = item.get('должность', '')
        dept = item.get('подразделение', '')
        formatted.append(f"{i}. {position} ({dept})")
    
    return "\n".join(formatted)