# response_processing.py
import sys
import os

# Добавляем родительскую директорию в sys.path для импортов
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import csv
from typing import List, Dict, Optional, Tuple, Set
import logging
from scripts.rag.retrieval import extract_keywords
from scripts.config import (
    ALLOWED_SUBDIVISIONS,
    EMPLOYEES_REFERENCE_CSV,
    TECHNIC_REFERENCE_CSV
)


def get_subdivisions_reference() -> Set[str]:
    """
    Возвращает справочник подразделений.
    
    Returns:
        Множество допустимых подразделений
    """
    return set(ALLOWED_SUBDIVISIONS.keys())
from thefuzz import fuzz
from scripts.rag import app_state

logger = logging.getLogger(__name__)

SPECIAL_TOKENS = [
    r'<\|im_start\|>',
    r'<\|im_end\|>',
    r'<\|im_sep\|>',
    r'<\|endoftext\|>',
]

# Кэширование справочников для оптимизации
_EMPLOYEES_REFERENCE: Optional[Set[str]] = None
_TECHNIC_REFERENCE: Optional[Set[str]] = None


def load_reference_data(csv_path: str) -> Set[str]:
    """
    Загружает справочник из CSV файла.
    Возвращает множество названий для быстрого поиска.
    """
    if not os.path.exists(csv_path):
        logger.warning(f"Справочник не найден: {csv_path}")
        return set()
    
    try:
        reference_set = set()
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                # Для сотрудников - первый столбец (должность)
                # Для техники - первый столбец (название)
                if row:
                    first_key = list(row.keys())[0]
                    value = row.get(first_key, '').strip()
                    if value:
                        reference_set.add(value)
        
        logger.info(f"Загружен справочник из {csv_path}: {len(reference_set)} записей")
        return reference_set
    except Exception as e:
        logger.error(f"Ошибка загрузки справочника {csv_path}: {e}", exc_info=True)
        return set()


def get_employees_reference() -> Set[str]:
    """
    Возвращает справочник должностей.
    Использует предварительно загруженный справочник из app_state.
    Если app_state не инициализирован, загружает из файла с кэшированием.
    """
    # Сначала пробуем использовать предварительно загруженный справочник из app_state
    if app_state.employees_reference:
        # Преобразуем список словарей в множество названий должностей
        return {item.get('должность', '').strip() for item in app_state.employees_reference if item.get('должность')}
    
    # Fallback: загружаем из файла с кэшированием
    global _EMPLOYEES_REFERENCE
    if _EMPLOYEES_REFERENCE is None:
        _EMPLOYEES_REFERENCE = load_reference_data(EMPLOYEES_REFERENCE_CSV)
    return _EMPLOYEES_REFERENCE


def get_technic_reference() -> Set[str]:
    """
    Возвращает справочник техники.
    Использует предварительно загруженный справочник из app_state.
    Если app_state не инициализирован, загружает из файла с кэшированием.
    """
    # Сначала пробуем использовать предварительно загруженный справочник из app_state
    if app_state.technic_reference:
        # Преобразуем список словарей в множество названий техники
        return {item.get('название_техники', '').strip() for item in app_state.technic_reference if item.get('название_техники')}
    
    # Fallback: загружаем из файла с кэшированием
    global _TECHNIC_REFERENCE
    if _TECHNIC_REFERENCE is None:
        _TECHNIC_REFERENCE = load_reference_data(TECHNIC_REFERENCE_CSV)
    return _TECHNIC_REFERENCE


def normalize_technic_name(item: str, reference_set: Set[str] = None) -> str:
    """
    Нормализует название техники, извлекая базовое название.
    
    Например:
    - "Экскаватор Komatsu PC200-8" -> "Экскаватор"
    - "бульдозер Caterpillar D6T" -> "Бульдозер"
    - "Гидравлический домкрат HYP" -> "Домкрат"
    - "путевой кран УК-25/18" -> "Кран"
    - "Экскаватор Komatsu PC200-8, Бульдозер Caterpillar D6T" -> ["Экскаватор", "Бульдозер"]
    
    Args:
        item: Полное название техники (может содержать несколько через запятую)
        reference_set: Справочник техники для проверки
        
    Returns:
        Нормализованное базовое название или список названий
    """
    if not item:
        return item
    
    # Список базовых названий техники для извлечения
    base_names = [
        'экскаватор', 'бульдозер', 'кран', 'домкрат', 'лебёдка', 'лебедка',
        'погрузчик', 'автовышка', 'дрезина', 'мотодрезина', 'компрессор',
        'виброплита', 'каток', 'рельсорез', 'рельсосвар', 'шпалоподбойник',
        'балласторазбрасыватель', 'впо', 'щом', 'бум', 'мср', 'сварочн',
        'автосцепка', 'генератор', 'насос', 'трактор', 'прицеп', 'бензорез',
        'перфоратор', 'отбойный молоток', 'шлифовальная машина', 'пресс',
        'подъёмник', 'лес', 'строп', 'таль', 'цеп', 'канат', 'блок',
        'подставка', 'козл', 'верстак', 'ящик', 'инструмент', 'прибор',
        'средство', 'машина', 'автомобиль', 'поезд', 'установка', 'пушка',
        'вентилятор', 'тележка', 'комплект', 'заграждение', 'сорбент',
        'нефтесборщик', 'кюветокопатель', 'лаборатория', 'комплекс',
        'кран-манипулятор', 'бетономешалка', 'асфальтоукладчик', 'аппарат',
        'станок', 'машина', 'средства', 'путеукладчик', 'путеизмерительн',
        'георадар', 'нивелир', 'датчик', 'измерительн', 'измерительные приборы',
        'путевые измерительные тележки', 'измерительные тележки'
    ]
    
    # Проверяем, содержит ли строка запятые (несколько элементов)
    if ',' in item:
        # Разбиваем по запятым и обрабатываем каждый элемент
        items = [i.strip() for i in item.split(',')]
        normalized_items = []
        for sub_item in items:
            normalized = _normalize_single_technic(sub_item, base_names, reference_set)
            if normalized:
                normalized_items.append(normalized)
        return ', '.join(normalized_items) if normalized_items else item
    else:
        # Одиночный элемент
        return _normalize_single_technic(item, base_names, reference_set)


def _normalize_single_technic(item: str, base_names: List[str], reference_set: Set[str] = None) -> str:
    """
    Нормализует одно название техники.
    
    Args:
        item: Название техники
        base_names: Список базовых названий
        reference_set: Справочник техники для проверки
        
    Returns:
        Нормализованное название или пустая строка, если не найдено
    """
    if not item:
        return ""
    
    item_lower = item.lower().strip()
    
    # Проверяем каждое базовое название
    for base_name in base_names:
        if base_name in item_lower:
            # Извлекаем базовое название с правильным регистром
            # Находим позицию базового названия в оригинальной строке
            pos = item_lower.find(base_name)
            if pos >= 0:
                # Возвращаем базовое название с правильным регистром
                normalized = item[pos:pos + len(base_name)].strip()
                
                # Если справочник предоставлен, проверяем наличие базового названия
                if reference_set:
                    # Сначала проверяем точное совпадение
                    if normalized in reference_set:
                        return normalized
                    
                    # Если базового названия нет в справочнике, ищем любую технику с этим базовым названием
                    for ref in reference_set:
                        ref_lower = ref.lower()
                        if base_name in ref_lower:
                            # Возвращаем первое найденное совпадение
                            return ref
                
                return normalized
    
    # Если базовое название не найдено, возвращаем пустую строку
    return ""


def validate_item_with_fuzzy_match(
    item: str,
    reference_set: Set[str],
    threshold: float = 0.76,
    is_technic: bool = False
) -> Tuple[bool, str]:
    """
    Валидирует элемент по справочнику с использованием нечёткого сопоставления.
    
    Args:
        item: Проверяемый элемент
        reference_set: Справочник (множество допустимых значений)
        threshold: Порог схожести для нечёткого сопоставления (0-1)
        is_technic: Является ли элемент техникой (для нормализации названий)
    
    Returns:
        Кортеж (валиден_ли, исправленное_название)
    """
    if not item or not reference_set:
        return False, item
    
    # Нормализуем название техники
    if is_technic:
        item = normalize_technic_name(item, reference_set)
    
    item_normalized = item.strip().lower()
    
    # 1. Проверка точного совпадения (с учётом регистра)
    if item in reference_set:
        return True, item
    
    # 2. Проверка точного совпадения без учёта регистра
    for ref in reference_set:
        if ref.lower() == item_normalized:
            return True, ref
    
    # 3. Проверка на вхождение (если элемент содержит название из справочника)
    for ref in reference_set:
        ref_lower = ref.lower()
        if ref_lower in item_normalized or item_normalized in ref_lower:
            # Проверяем, что совпадение достаточно длинное
            if len(ref_lower) >= 4 and len(item_normalized) >= 4:
                ratio = fuzz.ratio(item_normalized, ref_lower)
                if ratio >= threshold * 100:
                    logger.debug(f"Вхождение: '{item}' -> '{ref}' (ratio: {ratio})")
                    return True, ref
    
    # 4. Нечёткое сопоставление
    best_match = None
    best_ratio = 0
    
    for ref in reference_set:
        ratio = fuzz.ratio(item_normalized, ref.lower())
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = ref
    
    if best_ratio >= threshold * 100:
        logger.debug(f"Нечёткое совпадение: '{item}' -> '{best_match}' (ratio: {best_ratio})")
        return True, best_match
    
    logger.debug(f"Элемент '{item}' не найден в справочнике (лучшее совпадение: {best_ratio}%)")
    return False, item


def clean_text_from_special_tokens(text: str) -> str:
    """Удаляет специальные токены из текста, нормализует пробелы и тире."""
    if not text:
        return text
    
    # Удаляем специальные токены
    for token in SPECIAL_TOKENS:
        text = re.sub(token, '', text)
    
    # Нормализуем пробелы внутри строк (несколько пробелов -> один), но сохраняем переносы строк
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Нормализуем переносы строк (несколько подряд -> один)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    # Нормализуем тире (разные варианты -> обычное тире)
    text = re.sub(r'[–—−]', '-', text)
    
    return text.strip()


def _extract_items_from_section(section: str, stop_words: List[str] = None) -> List[str]:
    """
    Улучшенная функция извлечения элементов из секции.
    Поддерживает:
    - Маркеры списка (1., -, •, *)
    - Текст без маркеров (разделение по переносам строк)
    - Многострочные описания (фильтрация коротких строк)
    
    Args:
        section: Текст секции для извлечения
        stop_words: Список стоп-слов для фильтрации
    
    Returns:
        Список извлечённых элементов
    """
    if stop_words is None:
        stop_words = ['техника', 'не требуется', 'список', 'сотрудники', 'подразделения', 'ответ', 'шаг']
    
    # Дополнительная функция для фильтрации элементов
    def should_filter_item(item: str) -> bool:
        """Проверяет, нужно ли отфильтровать элемент."""
        item_lower = item.lower()
        
        # Проверка на стоп-слова в начале
        if any(item_lower.startswith(word) for word in stop_words):
            return True
        
        # Проверка на наличие двоеточия (признак заголовка секции)
        if ':' in item:
            return True
        
        return False
    
    if not section:
        return []
    
    # Нормализация текста
    section = section.strip()
    
    # Попытка 1: Поиск маркеров списка (цифра с точкой)
    # Ищем все позиции маркеров "цифра. "
    digit_marker_re = r'\d+\.\s+'
    digit_markers = list(re.finditer(digit_marker_re, section))
    
    items = []
    
    if digit_markers:
        # Обработка с маркерами списка
        for i, match in enumerate(digit_markers):
            start = match.end()
            end = digit_markers[i+1].start() if i+1 < len(digit_markers) else len(section)
            text = section[start:end].strip()
            
            # Извлекаем название (до первого тире с пробелами или переноса строки)
            if ' - ' in text:
                name = text.split(' - ')[0].strip()
            elif '\n' in text:
                # Берём только первую строку
                name = text.split('\n')[0].strip()
            else:
                name = text
            
            if name and len(name) > 2 and not should_filter_item(name):
                items.append(name)
    else:
        # Попытка 2: Поиск других маркеров списка (-, •, *)
        other_marker_re = r'(?:^|\n|\s)\s*(\-|\•|\*)\s+'
        other_markers = list(re.finditer(other_marker_re, section))
        
        if other_markers:
            for i, match in enumerate(other_markers):
                start = match.end()
                end = other_markers[i+1].start() if i+1 < len(other_markers) else len(section)
                text = section[start:end].strip()
                
                # Извлекаем название (до первого тире с пробелами или переноса строки)
                if ' - ' in text:
                    name = text.split(' - ')[0].strip()
                elif '\n' in text:
                    # Берём только первую строку
                    name = text.split('\n')[0].strip()
                else:
                    name = text
                
                if name and len(name) > 2 and not should_filter_item(name):
                    items.append(name)
        else:
            # Попытка 3: Обработка без маркеров (разделение по строкам)
            lines = section.split('\n')
            current_item = ""
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Проверка на стоп-слова в начале строки
                if should_filter_item(line):
                    continue
                
                # Если строка начинается с заглавной буквы и достаточно длинная - это новый элемент
                if line and len(line) > 3 and line[0].isupper():
                    if current_item:
                        items.append(current_item.strip())
                    current_item = line
                elif current_item:
                    # Продолжение описания текущего элемента (игнорируем)
                    pass
                else:
                    # Первая строка без маркера
                    current_item = line
            
            if current_item:
                items.append(current_item.strip())
            
            # Попытка 4: Если всё ещё пусто, пробуем простой split по цифрам
            if not items:
                parts = re.split(r'\s*\d+\.\s+', section)
                # Удаляем пустые элементы
                parts = [p.strip() for p in parts if p.strip()]
                
                for part in parts:
                    # Извлекаем название (до первого тире с пробелами)
                    if ' - ' in part:
                        name = part.split(' - ')[0].strip()
                    else:
                        name = part
                    
                    if name and len(name) > 2 and not should_filter_item(name):
                        items.append(name)
    
    # Фильтрация коротких строк и строк, которые выглядят как описания
    filtered_items = []
    for item in items:
        # Удаляем лишние пробелы
        item = ' '.join(item.split())
        
        # Фильтрация по стоп-словам и заголовкам секций
        if should_filter_item(item):
            continue
        
        # Фильтрация по длине
        if len(item) < 3:
            continue
        
        # Фильтрация строк, которые начинаются с предлогов или союзов
        if re.match(r'^(для|в|на|с|из|по|к|от|у|при|без|о|об|о|про|через|между|во|за|под|над|надо)\s+', item.lower()):
            continue
        
        # Фильтрация строк, которые выглядят как продолжение описания
        if re.match(r'^(для|с|в|на|и|а|но|или|также|кроме|включая)\s+', item.lower()):
            continue
        
        # Фильтрация строк, которые слишком длинные (вероятно, это описание)
        if len(item) > 100:
            continue
        
        filtered_items.append(item)
    
    logger.debug(f"[_extract_items_from_section] Извлечено {len(filtered_items)} элементов: {filtered_items}")
    return filtered_items


def extract_technics_from_model_response(response_text: str) -> List[str]:
    """
    Извлекает список техники из ответа модели с валидацией по справочнику.
    
    Args:
        response_text: Текст ответа от LLM
    
    Returns:
        Список валидированных названий техники
    """
    if not response_text:
        return []
    
    response_text = clean_text_from_special_tokens(response_text)
    
    # Извлекаем секцию с техникой
    pattern = r'(?:Необходимая\s+техника:?)\s*(.*?)(?=\n\n(?:Необходимые|План|Ответ|Этап|\*\*Этап|$))'
    match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
    
    if not match:
        # Альтернативный паттерн - до конца текста
        pattern = r'(?:Необходимая\s+техника:?)\s*(.*)'
        match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
    
    section = None
    if match:
        section = match.group(1)
        logger.debug(f"[extract_technics] Секция техники:\n{repr(section[:500])}")
    else:
        # Если секция не найдена, пробуем извлечь из всего текста
        logger.debug("[extract_technics] Секция не найдена, пробуем извлечь из всего текста")
        section = response_text
    
    # Извлекаем элементы
    items = _extract_items_from_section(section, stop_words=['техника', 'не требуется', 'список', 'ответ', 'шаг'])
    
    # Загружаем справочник
    reference_set = get_technic_reference()
    
    # Валидация элементов
    validated_items = []
    rejected_items = []
    
    for item in items:
        is_valid, corrected_name = validate_item_with_fuzzy_match(item, reference_set, threshold=0.80, is_technic=True)
        
        if is_valid:
            if corrected_name not in validated_items:
                validated_items.append(corrected_name)
        else:
            rejected_items.append(item)
    
    if rejected_items:
        logger.info(f"[extract_technics] Отклонены элементы: {rejected_items}")
    
    logger.info(f"[extract_technics] Результат: {validated_items}")
    return validated_items


def extract_employees_from_model_response(response_text: str) -> List[str]:
    """
    Извлекает список сотрудников из ответа модели с валидацией по справочнику.
    
    Args:
        response_text: Текст ответа от LLM
    
    Returns:
        Список валидированных должностей сотрудников
    """
    if not response_text:
        return []
    
    response_text = clean_text_from_special_tokens(response_text)
    
    # Извлекаем секцию с сотрудниками
    pattern = r'(?:Необходимые\s+сотрудники:?)\s*(.*?)(?=\n\n(?:План|Ответ|Этап|\*\*Этап|$))'
    match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
    
    if not match:
        # Альтернативный паттерн - до конца текста
        pattern = r'(?:Необходимые\s+сотрудники:?)\s*(.*)'
        match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
    
    section = None
    if match:
        section = match.group(1)
        logger.debug(f"[extract_employees] Секция сотрудников:\n{repr(section[:500])}")
    else:
        # Если секция не найдена, пробуем извлечь из всего текста
        logger.debug("[extract_employees] Секция не найдена, пробуем извлечь из всего текста")
        section = response_text
    
    # Извлекаем элементы
    items = _extract_items_from_section(section, stop_words=['техника', 'сотрудники', 'подразделения', 'ответ', 'шаг'])
    
    # Загружаем справочник
    reference_set = get_employees_reference()
    
    # Валидация элементов
    validated_items = []
    rejected_items = []
    
    for item in items:
        is_valid, corrected_name = validate_item_with_fuzzy_match(item, reference_set, threshold=0.80)
        
        if is_valid:
            if corrected_name not in validated_items:
                validated_items.append(corrected_name)
        else:
            rejected_items.append(item)
    
    if rejected_items:
        logger.info(f"[extract_employees] Отклонены элементы: {rejected_items}")
    
    logger.info(f"[extract_employees] Результат: {validated_items}")
    return validated_items


def extract_subdivisions_from_model_response(response_text: str) -> List[str]:
    """Извлекает подразделения из ответа модели (по аббревиатурам)."""
    if not response_text:
        return []
    response_text = clean_text_from_special_tokens(response_text)
    found = set()
    for abbr in ALLOWED_SUBDIVISIONS:
        if re.search(r'\b' + re.escape(abbr) + r'\b', response_text):
            found.add(abbr)
    return list(found)


def extract_technics_from_work_plan(work_plan: str) -> List[str]:
    """
    Извлекает технику из плана работ.
    
    Args:
        work_plan: Текст плана работ
        
    Returns:
        Список извлечённой техники
    """
    if not work_plan:
        return []
    
    # Находим все этапы
    stage_pattern = r'(\*\*Этап\s+\d+:[^*]+\*\*)'
    stages = re.split(stage_pattern, work_plan)
    
    technics = set()
    
    # Обрабатываем пары (заголовок, содержание)
    for i in range(1, len(stages), 2):
        if i + 1 >= len(stages):
            break
        
        content = stages[i + 1]
        
        # Находим строку техники - ищем только строку, которая начинается с "- Техника:"
        # и извлекаем только до следующего пункта (например, "- Сотрудники:")
        tech_match = re.search(r'-\s*Техника:\s*([^\n]*?)(?=\n-\s*(?:Сотрудники|Действия|Пояснение)|$)', content, re.DOTALL)
        if tech_match:
            tech_line = tech_match.group(1).strip()
            # Разбиваем по запятым и точкам с запятой
            tech_items = [t.strip() for t in re.split(r'[;,]', tech_line)]
            for tech in tech_items:
                # Пропускаем пустые элементы и "Не требуется"
                if tech and not tech.lower().startswith("не требуется"):
                    # Дополнительная фильтрация: исключаем строки, которые выглядят как действия
                    # Действия обычно содержат глаголы в инфинитиве или повелительном наклонении
                    action_indicators = ['провести', 'выполнить', 'осуществить', 'организовать', 'установить',
                                       'удалить', 'поднять', 'определить', 'зафиксировать', 'очистить',
                                       'сформировать', 'проверить', 'оценить', 'измерить', 'записать']
                    tech_lower = tech.lower()
                    if not any(indicator in tech_lower for indicator in action_indicators):
                        # Проверяем, что это не слишком длинная строка (действия обычно длиннее)
                        if len(tech) < 100:  # Техника обычно имеет короткое название
                            technics.add(tech)
    
    return list(technics)


def extract_employees_from_work_plan(work_plan: str) -> List[str]:
    """
    Извлекает сотрудников из плана работ.
    
    Args:
        work_plan: Текст плана работ
        
    Returns:
        Список извлечённых сотрудников
    """
    if not work_plan:
        return []
    
    # Находим все этапы
    stage_pattern = r'(\*\*Этап\s+\d+:[^*]+\*\*)'
    stages = re.split(stage_pattern, work_plan)
    
    employees = set()
    
    # Обрабатываем пары (заголовок, содержание)
    for i in range(1, len(stages), 2):
        if i + 1 >= len(stages):
            break
        
        content = stages[i + 1]
        
        # Находим строку сотрудников - разбиваем по строкам и ищем строку с "Сотрудники:"
        lines = content.split('\n')
        for line in lines:
            if re.match(r'-\s*Сотрудники:', line):
                # Извлекаем часть после двоеточия
                emp_line = re.sub(r'-\s*Сотрудники:\s*', '', line).strip()
                # Разбиваем по запятым и точкам с запятой
                emp_items = [e.strip() for e in re.split(r'[;,]', emp_line)]
                for emp in emp_items:
                    # Пропускаем пустые элементы и "Не требуются" (без учета регистра)
                    if emp and not emp.lower().startswith("не требуется"):
                        employees.add(emp)
                break  # Нашли строку сотрудников, переходим к следующему этапу
    
    return list(employees)


def extract_work_plan_from_model_response(response_text: str) -> str:
    """Извлекает план работ из ответа модели."""
    if not response_text:
        return ""
    response_text = clean_text_from_special_tokens(response_text)
    clean_plan = re.sub(r"ИНСТРУКЦИИ.*?(?=\n\n|\Z)", "", response_text, flags=re.DOTALL)
    clean_plan = re.sub(r"Ответ:\s*", "", clean_plan)
    
    # Сначала разделяем этапы, если они объединены
    # Используем более агрессивный паттерн для разделения этапов
    # Например: "призмы**Этап 2:" -> "призмы\n\n**Этап 2:"
    # Или "D6T**Этап 3:" -> "D6T\n\n**Этап 3:"
    clean_plan = re.sub(r'([а-яА-ЯёЁa-zA-Z0-9.,\s])\*\*\*Этап\s+(\d+):', r'\1\n\n**Этап \2:', clean_plan)
    clean_plan = re.sub(r'([а-яА-ЯёЁa-zA-Z0-9.,\s])\*\*Этап\s+(\d+):', r'\1\n\n**Этап \2:', clean_plan)
    
    # Дополнительная очистка: если перед **Этап нет переноса строки, добавляем его
    # Используем двухэтапный подход для избежания lookbehind с переменной длиной
    # Сначала заменяем все **Этап на временный маркер с переносом строки
    clean_plan = re.sub(r'\*\*\*Этап\s+(\d+):', r'__STAGE_SEPARATOR__**Этап \1:', clean_plan)
    # Затем заменяем маркер на перенос строки, если перед ним нет переноса
    clean_plan = re.sub(r'([^\n])__STAGE_SEPARATOR__', r'\1\n\n', clean_plan)
    clean_plan = clean_plan.replace('__STAGE_SEPARATOR__', '')
    
    # Добавляем перенос строки перед **Этап, если его нет
    clean_plan = re.sub(r'(?<!\n\n)(\*\*Этап\s+\d+:)', r'\n\n\1', clean_plan)
    
    # Дополнительная обработка: разделяем этапы, если они объединены без пробела
    # Например: "призмы**Этап 2:" -> "призмы\n\n**Этап 2:"
    clean_plan = re.sub(r'([а-яА-ЯёЁa-zA-Z0-9.,\s])\*\*Этап\s+(\d+):', r'\1\n\n**Этап \2:', clean_plan)
    
    # Ещё один паттерн для случаев, когда этапы объединены без пробела
    clean_plan = re.sub(r'([а-яА-ЯёЁa-zA-Z0-9.,\s])\*\*\*Этап\s+(\d+):', r'\1\n\n**Этап \2:', clean_plan)
    
    # Добавляем перенос строки перед **Этап, если его нет (ещё раз)
    clean_plan = re.sub(r'(?<!\n\n)(\*\*Этап\s+\d+:)', r'\n\n\1', clean_plan)
    
    # Ещё один паттерн для разделения этапов, если они объединены
    clean_plan = re.sub(r'([а-яА-ЯёЁa-zA-Z0-9.,\s])\*\*\*Этап\s+(\d+):', r'\1\n\n**Этап \2:', clean_plan)
    
    # Добавляем перенос строки перед **Этап, если его нет (ещё раз)
    clean_plan = re.sub(r'(?<!\n\n)(\*\*Этап\s+\d+:)', r'\n\n\1', clean_plan)
    
    # Ещё один паттерн для разделения этапов, если они объединены
    clean_plan = re.sub(r'([а-яА-ЯёЁa-zA-Z0-9.,\s])\*\*\*Этап\s+(\d+):', r'\1\n\n**Этап \2:', clean_plan)
    
    # Добавляем перенос строки перед **Этап, если его нет (ещё раз)
    clean_plan = re.sub(r'(?<!\n\n)(\*\*Этап\s+\d+:)', r'\n\n\1', clean_plan)
    
    # Разделяем план на этапы для обработки каждого этапа отдельно
    stage_pattern = r'(\*\*Этап\s+\d+:[^*]+\*\*)'
    stages = re.split(stage_pattern, clean_plan)
    
    # Обрабатываем каждый этап отдельно
    processed_stages = []
    for i in range(1, len(stages), 2):
        if i + 1 >= len(stages):
            break
        stage_header = stages[i]
        stage_content = stages[i + 1] if i + 1 < len(stages) else ""
        
        # Очищаем этап от артефактов
        # Сначала разделяем объединенные строки (например, "Техника: - Действия:")
        stage_content = re.sub(r'-\s*Техника:\s*([^\n]*?)-\s*Действия:', r'- Техника: \1\n- Действия:', stage_content)
        stage_content = re.sub(r'-\s*Техника:\s*([^\n]*?)-\s*Пояснение:', r'- Техника: \1\n- Пояснение:', stage_content)
        stage_content = re.sub(r'-\s*Сотрудники:\s*([^\n]*?)-\s*Действия:', r'- Сотрудники: \1\n- Действия:', stage_content)
        stage_content = re.sub(r'-\s*Сотрудники:\s*([^\n]*?)-\s*Пояснение:', r'- Сотрудники: \1\n- Пояснение:', stage_content)
        
        # Очищаем случаи, когда действия попадают в строку техники
        # Ищем паттерн "Техника: [текст] - Действия:" и разделяем
        stage_content = re.sub(r'-\s*Техника:\s*([^\n]*?)(?=\s*-\s*Действия:)', lambda m: '- Техника: ' + m.group(1).strip() + '\n' if m.group(1).strip() else '- Техника: Не требуется\n', stage_content)
        
        # Удаляем технику из строки подразделений
        stage_content = re.sub(r'-\s*Подразделения:\s*([^\n]*?)(?=\n|$)',
                              lambda m: '- Подразделения: ' + ('Не требуется' if any(word in m.group(1).lower() for word in ['кран', 'экскаватор', 'бульдозер', 'домкрат', 'лебёдка', 'погрузчик', 'автовышка', 'дрезина', 'мотодрезина', 'компрессор', 'виброплита', 'каток', 'рельсорез', 'рельсосвар', 'шпалоподбойник', 'балласторазбрасыватель', 'впо', 'щом', 'бум', 'мср', 'сварочн', 'автосцепка', 'генератор', 'насос', 'трактор', 'прицеп', 'бензорез', 'перфоратор', 'отбойный молоток', 'шлифовальная машина', 'пресс', 'подъёмник', 'лес', 'строп', 'таль', 'цеп', 'канат', 'блок', 'подставка', 'козл', 'верстак', 'ящик', 'инструмент', 'прибор', 'средство', 'машина', 'автомобиль', 'поезд', 'установка', 'пушка', 'вентилятор', 'тележка', 'комплект', 'заграждение', 'сорбент', 'нефтесборщик', 'кюветокопатель', 'лаборатория', 'комплекс', 'кран-манипулятор', 'бетономешалка', 'асфальтоукладчик', 'аппарат', 'станок', 'путеукладчик', 'путеизмерительн', 'георадар', 'нивелир', 'датчик', 'измерительн', 'измерительные приборы', 'путевые измерительные тележки', 'измерительные тележки']) else m.group(1).strip()) + '\n',
                              stage_content, flags=re.MULTILINE)
        
        # Очищаем случаи, когда в строке подразделений остались артефакты от действий
        # Например: "- Подразделения: зафиксировать данные, определить степень деформации"
        stage_content = re.sub(r'-\s*Подразделения:\s*([а-яА-ЯёЁa-zA-Z0-9,\s]+?)(?=\n|$)',
                              lambda m: '- Подразделения: ' + ('Не требуется' if any(word in m.group(1).lower() for word in ['провести', 'выполнить', 'зафиксировать', 'определить', 'оценить', 'измерить', 'установить', 'удалить', 'поднять', 'очистить', 'сформировать', 'проверить', 'записать']) else m.group(1).strip()) + '\n',
                              stage_content, flags=re.MULTILINE)
        
        # Очищаем случаи, когда техника попадает в строку подразделений после разделения этапов
        # Например: "- Подразделения: Путевой кран УК-25/18"
        stage_content = re.sub(r'-\s*Подразделения:\s*([^\n]*?)(?=\n|$)',
                              lambda m: '- Подразделения: ' + ('Не требуется' if any(word in m.group(1).lower() for word in ['кран', 'экскаватор', 'бульдозер', 'домкрат', 'лебёдка', 'погрузчик', 'автовышка', 'дрезина', 'мотодрезина', 'компрессор', 'виброплита', 'каток', 'рельсорез', 'рельсосвар', 'шпалоподбойник', 'балласторазбрасыватель', 'впо', 'щом', 'бум', 'мср', 'сварочн', 'автосцепка', 'генератор', 'насос', 'трактор', 'прицеп', 'бензорез', 'перфоратор', 'отбойный молоток', 'шлифовальная машина', 'пресс', 'подъёмник', 'лес', 'строп', 'таль', 'цеп', 'канат', 'блок', 'подставка', 'козл', 'верстак', 'ящик', 'инструмент', 'прибор', 'средство', 'машина', 'автомобиль', 'поезд', 'установка', 'пушка', 'вентилятор', 'тележка', 'комплект', 'заграждение', 'сорбент', 'нефтесборщик', 'кюветокопатель', 'лаборатория', 'комплекс', 'кран-манипулятор', 'бетономешалка', 'асфальтоукладчик', 'аппарат', 'станок', 'путеукладчик', 'путеизмерительн', 'георадар', 'нивелир', 'датчик', 'измерительн', 'измерительные приборы', 'путевые измерительные тележки', 'измерительные тележки']) else m.group(1).strip()) + '\n',
                              stage_content, flags=re.MULTILINE)
        
        processed_stages.append(stage_header + stage_content)
    
    clean_plan = ''.join(processed_stages)
    
    # Очищаем артефакты слияния этапов (например, "Не требуются**Этап 2:")
    clean_plan = re.sub(r'Не\s+требуется\*\*\*Этап', '\n\n**Этап', clean_plan)
    clean_plan = re.sub(r'Не\s+требуемые\*\*\*Этап', '\n\n**Этап', clean_plan)
    
    # Очищаем некорректные элементы типа "Не требуется-1", "Не требуется-25/18", "Не требуется-путеец"
    # Удаляем их вместе с запятой, если она есть
    clean_plan = re.sub(r'Не\s+требуется[-\s]+\d+[^,\n]*,?\s*', '', clean_plan)
    clean_plan = re.sub(r'Не\s+требуется[-\s]+[а-яА-ЯёЁa-zA-Z]+[^,\n]*,?\s*', '', clean_plan)
    
    # Удаляем лишний текст после критерия завершения работ
    clean_plan = re.sub(r'\*\*Критерий завершения работ:\*\*.*', '', clean_plan, flags=re.DOTALL)
    
    # Удаляем списки ресурсов в конце плана
    clean_plan = re.sub(r'\n\n\*\*Список подразделений для использования в плане:\*\*.*', '', clean_plan, flags=re.DOTALL)
    clean_plan = re.sub(r'\n\n\*\*Техника:\*\*.*', '', clean_plan, flags=re.DOTALL)
    clean_plan = re.sub(r'\n\n\*\*Сотрудники:\*\*.*', '', clean_plan, flags=re.DOTALL)
    clean_plan = re.sub(r'\n\n\*\*Согласно предоставленным данным.*', '', clean_plan, flags=re.DOTALL)
    
    # Удаляем лишний текст после последнего этапа (объяснения, анализы и т.д.)
    # Ищем последний этап и удаляем всё после его пояснения
    last_stage_pattern = r'(\*\*Этап\s+\d+:[^*]+\*\*.*?-\s*Пояснение:\s*[^\n]+)'
    # Используем findall, чтобы найти все этапы, и берём последний
    all_stages = re.findall(last_stage_pattern, clean_plan, re.DOTALL)
    if all_stages:
        # Берём последний этап
        last_stage = all_stages[-1]
        # Находим позицию конца последнего этапа
        last_stage_end = clean_plan.rfind(last_stage) + len(last_stage)
        # Проверяем, есть ли текст после последнего этапа
        if last_stage_end < len(clean_plan):
            # Удаляем всё после последнего этапа
            clean_plan = clean_plan[:last_stage_end]
    
    # Удаляем лишние объяснения после плана (например, "**Техника: Не требуется** в этапах...")
    # Исключаем заголовки этапов из удаления, а также "Действия:" и "Пояснение:"
    clean_plan = re.sub(r'\n\n\*\*(?!Этап\s+\d+:|Действия:|Пояснение:)[А-Яа-яA-Za-z\s:]+\*\*.*', '', clean_plan, flags=re.DOTALL)
    
    # Очищаем лишние запятые и пробелы
    clean_plan = re.sub(r',\s*,', ',', clean_plan)  # Двойные запятые
    clean_plan = re.sub(r'^\s*,\s*', '', clean_plan)  # Запятая в начале строки
    clean_plan = re.sub(r',\s*$', '', clean_plan)  # Запятая в конце строки
    
    return clean_plan.strip()


def _get_stage_type(header: str) -> str:
    """
    Определяет тип этапа по его заголовку.
    
    Returns:
        'assessment' - этап оценки и безопасности
        'diagnosis' - этап диагностики
        'clearance' - этап расчистки и подготовки
        'restoration' - этап восстановления
        'final_check' - этап финальной проверки
        'documentation' - этап документирования
        'other' - другой тип этапа
    """
    header_lower = header.lower()
    
    # Сначала проверяем clearance, чтобы "эвакуация" в контексте оцепления не попадала в assessment
    if any(keyword in header_lower for keyword in ['расчистка', 'подготовка', 'завалы', 'оцепление']):
        return 'clearance'
    elif any(keyword in header_lower for keyword in ['диагностика', 'обследование', 'анализ']):
        return 'diagnosis'
    elif any(keyword in header_lower for keyword in ['оценка', 'безопасность', 'разведка']):
        return 'assessment'
    elif any(keyword in header_lower for keyword in ['восстановление', 'выравнивание', 'ремонт', 'ликвидация']):
        return 'restoration'
    elif any(keyword in header_lower for keyword in ['проверка', 'контроль', 'возобновление', 'финальный']):
        return 'final_check'
    elif any(keyword in header_lower for keyword in ['документ', 'оформление', 'анализ причин']):
        return 'documentation'
    else:
        return 'other'


def redistribute_technics(stage_info: List[Dict], technics: List[str]) -> None:
    """
    Перераспределяет технику по этапам логически.
    
    Args:
        stage_info: Список информации о этапах (изменяется in-place)
        technics: Список техники для распределения
    """
    # Классификация техники по типам
    assessment_tech = []  # Для этапа оценки
    diagnosis_tech = []   # Для этапа диагностики
    clearance_tech = []   # Для этапа расчистки
    stabilization_tech = [] # Для этапа стабилизации
    restoration_tech = [] # Для этапа восстановления
    final_check_tech = [] # Для этапа финальной проверки
    
    for tech in technics:
        tech_lower = tech.lower()
        
        # Техника для оценки и безопасности
        if any(keyword in tech_lower for keyword in ['рация', 'связь', 'реанимобил', 'скорой', 'пожарн', 'спасательн', 'светоотраж', 'огнетушитель']):
            assessment_tech.append(tech)
        # Техника для диагностики и обследования
        elif any(keyword in tech_lower for keyword in ['георадар', 'нивелир', 'теодолит', 'измерительн', 'датчик', 'дрезина', 'мотодрезина']):
            diagnosis_tech.append(tech)
        # Техника для расчистки и подготовки
        elif any(keyword in tech_lower for keyword in ['экскаватор', 'бульдозер', 'погрузчик', 'автомобиль камаз', 'грузовик', 'бензопила', 'цепная пила']):
            clearance_tech.append(tech)
        # Техника для стабилизации и фиксации
        elif any(keyword in tech_lower for keyword in ['домкрат', 'лебёдка', 'лебедка', 'крепеж', 'опора', 'подпорка', 'трос', 'строп']):
            stabilization_tech.append(tech)
        # Техника для восстановления
        elif any(keyword in tech_lower for keyword in ['кран', 'путеукладчик', 'виброплита', 'каток', 'рельсорез', 'рельсосвар', 'шпалоподбойник', 'балласторазбрасыватель', 'впо', 'щом', 'бум', 'мср', 'сварочн', 'автосцепка']):
            restoration_tech.append(tech)
        # Техника для финальной проверки
        elif any(keyword in tech_lower for keyword in ['измерительн', 'контрольн', 'проверочн']):
            final_check_tech.append(tech)
        else:
            # По умолчанию - для восстановления
            restoration_tech.append(tech)
    
    # Распределяем технику по этапам
    for stage in stage_info:
        stage_type = _get_stage_type(stage['header'])
        
        if stage_type == 'assessment':
            stage['techs'].extend(assessment_tech)
        elif stage_type == 'diagnosis':
            stage['techs'].extend(diagnosis_tech)
        elif stage_type == 'clearance':
            stage['techs'].extend(clearance_tech)
        elif stage_type == 'restoration':
            # Проверяем, есть ли в заголовке слова стабилизации
            header_lower = stage['header'].lower()
            if any(keyword in header_lower for keyword in ['фиксация', 'стабилизация', 'закрепление', 'подпорка']):
                stage['techs'].extend(stabilization_tech)
            else:
                stage['techs'].extend(restoration_tech)
        elif stage_type == 'final_check':
            stage['techs'].extend(final_check_tech)
        # Для этапов документирования техника не добавляется
    
    # Гарантируем, что каждый этап имеет хотя бы одну технику
    # Если этап остался без техники, добавляем из restoration_tech
    for stage in stage_info:
        if not stage['techs'] and restoration_tech:
            stage['techs'].extend(restoration_tech)


def redistribute_employees(stage_info: List[Dict], employees: List[str]) -> None:
    """
    Перераспределяет сотрудников по этапам логически.
    
    Args:
        stage_info: Список информации о этапах (изменяется in-place)
        employees: Список сотрудников для распределения
    """
    # Классификация сотрудников по типам
    assessment_emps = []  # Для этапа оценки
    diagnosis_emps = []   # Для этапа диагностики
    clearance_emps = []   # Для этапа расчистки
    stabilization_emps = [] # Для этапа стабилизации
    restoration_emps = [] # Для этапа восстановления
    final_check_emps = [] # Для этапа финальной проверки
    
    for emp in employees:
        emp_lower = emp.lower()
        
        # Сотрудники для расчистки и оцепления (включая диспетчеров для координации)
        if any(keyword in emp_lower for keyword in ['машинист экскаватор', 'машинист бульдозер', 'водитель', 'оператор погрузчик', 'диспетчер', 'сигналист']):
            clearance_emps.append(emp)
        # Сотрудники для оценки и безопасности
        elif any(keyword in emp_lower for keyword in ['медицинск', 'врач', 'фельдшер', 'охран', 'начальник', 'руководитель']):
            assessment_emps.append(emp)
        # Сотрудники для диагностики
        elif any(keyword in emp_lower for keyword in ['инженер-путеец', 'инженер путеец', 'геодезист', 'обследователь']):
            diagnosis_emps.append(emp)
        # Сотрудники для стабилизации и фиксации
        elif any(keyword in emp_lower for keyword in ['стропальщик', 'такелажник', 'сигналист']):
            stabilization_emps.append(emp)
        # Сотрудники для восстановления
        elif any(keyword in emp_lower for keyword in ['машинист кран', 'машинист путеукладчик', 'машинист балласторазбрасыватель', 'машинист впо', 'сварщик', 'монтер пути', 'механик', 'электромонтер', 'электросварщик']):
            restoration_emps.append(emp)
        # Сотрудники для финальной проверки
        elif any(keyword in emp_lower for keyword in ['мастер пути', 'инженер-путеец', 'машинист дрезины', 'приемщик', 'контролер']):
            final_check_emps.append(emp)
        else:
            # По умолчанию - для восстановления
            restoration_emps.append(emp)
    
    # Распределяем сотрудников по этапам
    for stage in stage_info:
        stage_type = _get_stage_type(stage['header'])
        
        if stage_type == 'assessment':
            stage['emps'].extend(assessment_emps)
        elif stage_type == 'diagnosis':
            stage['emps'].extend(diagnosis_emps)
        elif stage_type == 'clearance':
            stage['emps'].extend(clearance_emps)
        elif stage_type == 'restoration':
            # Проверяем, есть ли в заголовке слова стабилизации
            header_lower = stage['header'].lower()
            if any(keyword in header_lower for keyword in ['фиксация', 'стабилизация', 'закрепление', 'подпорка']):
                stage['emps'].extend(stabilization_emps)
            else:
                stage['emps'].extend(restoration_emps)
        elif stage_type == 'final_check':
            stage['emps'].extend(final_check_emps)
        # Для этапов документирования сотрудники не добавляются
    
    # Гарантируем, что каждый этап имеет хотя бы одного сотрудника
    # Если этап остался без сотрудников, добавляем из restoration_emps
    for stage in stage_info:
        if not stage['emps'] and restoration_emps:
            stage['emps'].extend(restoration_emps)


def redistribute_subdivisions(stage_info: List[Dict], subdivisions: List[str]) -> None:
    """
    Перераспределяет подразделения по этапам логически.
    
    Args:
        stage_info: Список информации о этапах (изменяется in-place)
        subdivisions: Список подразделений для распределения
    """
    # Классификация подразделений по типам
    assessment_subs = []  # Для этапа оценки
    diagnosis_subs = []   # Для этапа диагностики
    clearance_subs = []   # Для этапа расчистки
    stabilization_subs = [] # Для этапа стабилизации
    restoration_subs = [] # Для этапа восстановления
    final_check_subs = [] # Для этапа финальной проверки
    
    for sub in subdivisions:
        sub_lower = sub.lower()
        
        # Подразделения для расчистки и оцепления (МЧС, РСЧС)
        if any(keyword in sub_lower for keyword in ['мчс', 'рсчс']):
            clearance_subs.append(sub)
        # Подразделения для оценки и безопасности (ДА, ДАБ, ДАБС)
        elif any(keyword in sub_lower for keyword in ['да', 'даб', 'дабс']):
            assessment_subs.append(sub)
        # Подразделения для диагностики (ДИ, ЦДИ, ДЦС)
        elif any(keyword in sub_lower for keyword in ['ди', 'цди', 'дцс']):
            diagnosis_subs.append(sub)
        # Подразделения для управления и координации (ДЦУП, ДВС)
        elif any(keyword in sub_lower for keyword in ['дцуп', 'двс']):
            assessment_subs.append(sub)
        # Подразделения для стабилизации и фиксации (ДИП, ДВП)
        elif any(keyword in sub_lower for keyword in ['дип', 'двп']):
            stabilization_subs.append(sub)
        # Подразделения для восстановления (МЧ)
        elif any(keyword in sub_lower for keyword in ['мч']):
            restoration_subs.append(sub)
        # Подразделения для финальной проверки (используем те же, что и для диагностики)
        elif any(keyword in sub_lower for keyword in ['ди', 'цди', 'дцс']):
            final_check_subs.append(sub)
        else:
            # По умолчанию - для восстановления
            restoration_subs.append(sub)
    
    # Распределяем подразделения по этапам
    for stage in stage_info:
        stage_type = _get_stage_type(stage['header'])
        
        if stage_type == 'assessment':
            stage['subs'].extend(assessment_subs)
        elif stage_type == 'diagnosis':
            stage['subs'].extend(diagnosis_subs)
        elif stage_type == 'clearance':
            stage['subs'].extend(clearance_subs)
        elif stage_type == 'restoration':
            # Проверяем, есть ли в заголовке слова стабилизации
            header_lower = stage['header'].lower()
            if any(keyword in header_lower for keyword in ['фиксация', 'стабилизация', 'закрепление', 'подпорка']):
                stage['subs'].extend(stabilization_subs)
            else:
                stage['subs'].extend(restoration_subs)
        elif stage_type == 'final_check':
            stage['subs'].extend(final_check_subs)
        # Для этапов документирования подразделения не добавляются
    
    # Гарантируем, что каждый этап имеет хотя бы одно подразделение
    # Если этап остался без подразделений, добавляем из restoration_subs
    for stage in stage_info:
        if not stage['subs'] and restoration_subs:
            stage['subs'].extend(restoration_subs)


def validate_work_plan(
    work_plan: str,
    allowed_subdivisions: List[str],
    allowed_technics: List[str],
    allowed_employees: List[str]
) -> Tuple[str, List[str]]:
    """
    Валидирует план работ и заменяет недопустимые элементы на допустимые.
    Также проверяет, что все допустимые элементы были использованы в плане.
    ПЕРЕРАСПРЕДЕЛЯЕТ технику и сотрудников по этапам, если они были неправильно сгруппированы.
    
    Args:
        work_plan: Текст плана работ
        allowed_subdivisions: Список допустимых подразделений
        allowed_technics: Список допустимой техники
        allowed_employees: Список допустимых сотрудников
    
    Returns:
        Кортеж (валидированный_план, список_предупреждений)
    """
    if not work_plan:
        return "", []
    
    warnings = []
    
    # Создаём множества для быстрого поиска
    allowed_sub_set = set(allowed_subdivisions)
    allowed_tech_set = set(allowed_technics)
    allowed_emp_set = set(allowed_employees)
    
    # Флаги, показывающие, были ли списки загружены из справочника
    tech_from_reference = False
    emp_from_reference = False
    sub_from_reference = False
    
    # Если список допустимых подразделений пустой, загружаем справочник для валидации
    if not allowed_sub_set:
        allowed_sub_set = get_subdivisions_reference()
        sub_from_reference = True
        logger.info(f"[validate_work_plan] Список допустимых подразделений пустой, загружен справочник: {len(allowed_sub_set)} элементов")
    
    # Если список допустимой техники пустой, загружаем справочник для валидации
    if not allowed_tech_set:
        allowed_tech_set = get_technic_reference()
        tech_from_reference = True
        logger.info(f"[validate_work_plan] Список допустимой техники пустой, загружен справочник: {len(allowed_tech_set)} элементов")
    
    # Если список допустимых сотрудников пустой, загружаем справочник для валидации
    if not allowed_emp_set:
        allowed_emp_set = get_employees_reference()
        emp_from_reference = True
        logger.info(f"[validate_work_plan] Список допустимых сотрудников пустой, загружен справочник: {len(allowed_emp_set)} элементов")
    
    # Множества для отслеживания использованных элементов
    used_subs = set()
    used_techs = set()
    used_emps = set()
    
    # Находим все этапы с их заголовками
    stage_pattern = r'(\*\*Этап\s+\d+:[^*]+\*\*)'
    stages = re.split(stage_pattern, work_plan)
    
    # Если этапы не найдены, возвращаем план как есть
    if len(stages) <= 1:
        return work_plan, warnings
    
    # Валидируем каждый этап отдельно
    validated_plan = ""
    
    # Первый элемент - это текст до первого этапа (заголовок плана)
    validated_plan += stages[0]
    
    # Храним информацию о каждом этапе для последующего перераспределения
    stage_info = []
    
    # Обрабатываем пары (заголовок, содержание)
    for i in range(1, len(stages), 2):
        if i + 1 >= len(stages):
            break
        
        header = stages[i]
        content = stages[i + 1]
        
        # Сохраняем строки "Действия:" и "Пояснение:" до валидации
        actions_match = re.search(r'-\s*Действия:\s*([^\n]*)', content)
        explanation_match = re.search(r'-\s*Пояснение:\s*([^\n]*)', content)
        
        stage_data = {
            'header': header,
            'content': content,
            'subs': [],
            'techs': [],
            'emps': [],
            'actions': actions_match.group(0) if actions_match else None,
            'explanation': explanation_match.group(0) if explanation_match else None
        }
        
        # Валидируем подразделения в строке "Подразделения: ..."
        sub_match = re.search(r'-\s*Подразделения:\s*([^\n]*)', content)
        if sub_match:
            sub_line = sub_match.group(1).strip()
            # Разбиваем по запятым и проверяем каждое значение целиком
            sub_items = [s.strip() for s in re.split(r'[;,]', sub_line)]
            validated_subs = []
            for sub in sub_items:
                # Пропускаем пустые элементы и "Не требуется"
                if not sub or sub.lower().startswith("не требуется"):
                    continue
                
                # Если список подразделений пустой, сохраняем как есть
                if not allowed_sub_set:
                    validated_subs.append(sub)
                    used_subs.add(sub)
                    stage_data['subs'].append(sub)
                    continue
                
                # Проверяем точное совпадение или нечёткое
                if sub in allowed_sub_set:
                    validated_subs.append(sub)
                    used_subs.add(sub)
                    stage_data['subs'].append(sub)
                else:
                    # Проверяем нечёткое совпадение
                    found = False
                    for allowed in allowed_sub_set:
                        ratio = fuzz.ratio(sub.upper(), allowed.upper())
                        if ratio >= 85:
                            validated_subs.append(allowed)
                            used_subs.add(allowed)
                            stage_data['subs'].append(allowed)
                            warnings.append(f"Подразделение '{sub}' заменено на '{allowed}' (ratio: {ratio})")
                            found = True
                            break
                    if not found:
                        warnings.append(f"Подразделение '{sub}' не в списке допустимых")
            # Заменяем строку подразделений
            if validated_subs:
                new_sub_line = f"- Подразделения: {', '.join(validated_subs)}"
                content = content.replace(sub_match.group(0), new_sub_line)
            else:
                content = content.replace(sub_match.group(0), "- Подразделения: Не требуется")
        
        # Обновляем stage_data['content'] с валидированным контентом
        stage_data['content'] = content
        
        # Валидируем технику в строке "Техника: ..."
        tech_match = re.search(r'-\s*Техника:\s*([^\n]*)', content)
        if tech_match:
            tech_line = tech_match.group(1).strip()
            # Разбиваем по запятым и точкам с запятой
            tech_items = [t.strip() for t in re.split(r'[;,]', tech_line)]
            validated_techs = []
            for tech in tech_items:
                # Пропускаем пустые элементы и элементы, начинающиеся с "не требуется"
                if not tech or tech.lower().startswith("не требуется"):
                    continue
                
                # Если список техники загружен из справочника, сохраняем как есть
                if tech_from_reference:
                    validated_techs.append(tech)
                    used_techs.add(tech)
                    stage_data['techs'].append(tech)
                    continue
                
                # Нормализуем название техники
                normalized_tech = normalize_technic_name(tech, allowed_tech_set)
                
                # Проверяем, содержит ли нормализованное название запятые (несколько элементов)
                if ',' in normalized_tech:
                    # Разбиваем на отдельные элементы и валидируем каждый
                    sub_items = [t.strip() for t in normalized_tech.split(',')]
                    for sub_tech in sub_items:
                        if sub_tech in allowed_tech_set:
                            validated_techs.append(sub_tech)
                            used_techs.add(sub_tech)
                            stage_data['techs'].append(sub_tech)
                        else:
                            # Проверяем нечёткое совпадение
                            found = False
                            for allowed in allowed_tech_set:
                                ratio = fuzz.ratio(sub_tech.lower(), allowed.lower())
                                if ratio >= 80:
                                    validated_techs.append(allowed)
                                    used_techs.add(allowed)
                                    stage_data['techs'].append(allowed)
                                    warnings.append(f"Техника '{sub_tech}' заменена на '{allowed}' (ratio: {ratio})")
                                    found = True
                                    break
                            if not found:
                                warnings.append(f"Техника '{sub_tech}' не в списке допустимых")
                else:
                    # Одиночный элемент
                    if normalized_tech in allowed_tech_set:
                        validated_techs.append(normalized_tech)
                        used_techs.add(normalized_tech)
                        stage_data['techs'].append(normalized_tech)
                    else:
                        # Проверяем нечёткое совпадение
                        found = False
                        for allowed in allowed_tech_set:
                            ratio = fuzz.ratio(normalized_tech.lower(), allowed.lower())
                            if ratio >= 80:
                                validated_techs.append(allowed)
                                used_techs.add(allowed)
                                stage_data['techs'].append(allowed)
                                warnings.append(f"Техника '{tech}' заменена на '{allowed}' (ratio: {ratio})")
                                found = True
                                break
                        if not found:
                            warnings.append(f"Техника '{tech}' не в списке допустимых")
            # Заменяем строку техники
            if validated_techs:
                new_tech_line = f"- Техника: {', '.join(validated_techs)}"
                content = content.replace(tech_match.group(0), new_tech_line)
            else:
                content = content.replace(tech_match.group(0), "- Техника: Не требуется")
        
        # Обновляем stage_data['content'] с валидированным контентом
        stage_data['content'] = content
        
        # Проверяем наличие строки "Сотрудники:" и добавляем её, если отсутствует
        emp_match = re.search(r'-\s*Сотрудники:\s*([^\n]*)', content)
        if not emp_match:
            # Если строки "Сотрудники:" нет, добавляем её перед строкой "Действия:" или "Пояснение:"
            actions_match = re.search(r'-\s*Действия:', content)
            explanation_match = re.search(r'-\s*Пояснение:', content)
            
            if actions_match:
                # Вставляем перед "Действия:" с пустым списком сотрудников
                content = content.replace(actions_match.group(0), "- Сотрудники: \n" + actions_match.group(0))
                warnings.append(f"Добавлена отсутствующая строка 'Сотрудники:' в этап")
            elif explanation_match:
                # Вставляем перед "Пояснение:" с пустым списком сотрудников
                content = content.replace(explanation_match.group(0), "- Сотрудники: \n" + explanation_match.group(0))
                warnings.append(f"Добавлена отсутствующая строка 'Сотрудники:' в этап")
            else:
                # Добавляем в конец этапа с пустым списком сотрудников
                content += "\n- Сотрудники: "
                warnings.append(f"Добавлена отсутствующая строка 'Сотрудники:' в этап")
            # Теперь валидируем добавленную строку
            emp_match = re.search(r'-\s*Сотрудники:\s*([^\n]*)', content)
            
            # Если список сотрудников пустой или содержит только пробелы, пропускаем валидацию
            if emp_match:
                emp_line = emp_match.group(1).strip()
                if not emp_line or emp_line.lower().startswith("не требуется"):
                    emp_match = None
        
        # Валидируем сотрудников в строке "Сотрудники: ..."
        if emp_match:
            emp_line = emp_match.group(1).strip()
            # Очищаем от артефактов типа "Не требуется-путеец"
            emp_line = re.sub(r'Не\s+требуется[-\s]+', '', emp_line)
            # Разбиваем по запятым и точкам с запятой
            emp_items = [e.strip() for e in re.split(r'[;,]', emp_line)]
            validated_emps = []
            for emp in emp_items:
                # Пропускаем пустые элементы и элементы, начинающиеся с "не требуется"
                if not emp or emp.lower().startswith("не требуется"):
                    continue
                
                # Если список сотрудников загружен из справочника, сохраняем как есть
                if emp_from_reference:
                    validated_emps.append(emp)
                    used_emps.add(emp)
                    stage_data['emps'].append(emp)
                    continue
                
                if emp in allowed_emp_set:
                    validated_emps.append(emp)
                    used_emps.add(emp)
                    stage_data['emps'].append(emp)
                else:
                    # Проверяем нечёткое совпадение
                    found = False
                    for allowed in allowed_emp_set:
                        ratio = fuzz.ratio(emp.lower(), allowed.lower())
                        if ratio >= 80:
                            validated_emps.append(allowed)
                            used_emps.add(allowed)
                            stage_data['emps'].append(allowed)
                            warnings.append(f"Сотрудник '{emp}' заменён на '{allowed}' (ratio: {ratio})")
                            found = True
                            break
                    if not found:
                        warnings.append(f"Сотрудник '{emp}' не в списке допустимых")
            # Заменяем строку сотрудников
            if validated_emps:
                new_emp_line = f"- Сотрудники: {', '.join(validated_emps)}"
                content = content.replace(emp_match.group(0), new_emp_line)
            else:
                content = content.replace(emp_match.group(0), "- Сотрудники: Не требуются")
        
        # Сохраняем строки "Действия:" и "Пояснение:" - они не должны удаляться
        # Эти строки не валидируются, а просто сохраняются в плане
        
        # Обновляем stage_data['content'] с валидированным контентом
        stage_data['content'] = content
        
        # Добавляем заголовок и валидированное содержание с переносом строки между этапами
        if validated_plan:
            validated_plan += "\n\n" + header + content
        else:
            validated_plan = header + content
        stage_info.append(stage_data)
    
    # Проверяем, что все допустимые элементы были использованы
    # Но только если списки не были загружены из справочника
    missing_subs = allowed_sub_set - used_subs if not sub_from_reference else set()
    missing_techs = allowed_tech_set - used_techs if not tech_from_reference else set()
    missing_emps = allowed_emp_set - used_emps if not emp_from_reference else set()
    
    # ПРОВЕРКА: Если в первом этапе перечислены ВСЕ ресурсы (подразделения, техника, сотрудники)
    # ПЕРЕРАСПРЕДЕЛЯЕМ их по этапам логически
    # НО только если ресурсы НЕ распределены по другим этапам
    # И только если списки не были загружены из справочника
    if len(stage_info) > 1:
        first_stage = stage_info[0]
        
        # Проверяем, распределены ли подразделения по другим этапам
        subs_in_other_stages = sum(len(s['subs']) for s in stage_info[1:])
        # Проверяем, содержит ли первый этап все подразделения И подразделения не распределены по другим этапам
        if not sub_from_reference and len(first_stage['subs']) >= len(allowed_subdivisions) * 0.8 and subs_in_other_stages == 0:
            warnings.append("ОБНАРУЖЕНО: Все подразделения сосредоточены в первом этапе. Перераспределяем по этапам.")
            # Очищаем подразделения из первого этапа
            all_subs = list(first_stage['subs'])
            first_stage['subs'] = []
            # Распределяем подразделения по этапам
            redistribute_subdivisions(stage_info, all_subs)
        
        # Проверяем, распределена ли техника по другим этапам
        techs_in_other_stages = sum(len(s['techs']) for s in stage_info[1:])
        # Проверяем, содержит ли первый этап всю технику И техника не распределена по другим этапам
        # ИЛИ если техника распределена, но первый этап содержит больше 50% всей техники
        if not tech_from_reference and ((len(first_stage['techs']) >= len(allowed_technics) * 0.8 and techs_in_other_stages == 0) or
                                     (len(first_stage['techs']) >= len(allowed_technics) * 0.5 and techs_in_other_stages > 0)):
            warnings.append("ОБНАРУЖЕНО: Техника распределена неравномерно. Перераспределяем по этапам.")
            # Собираем всю технику из всех этапов
            all_techs = []
            for stage in stage_info:
                all_techs.extend(stage['techs'])
                stage['techs'] = []
            # Распределяем технику по этапам
            redistribute_technics(stage_info, all_techs)
        
        # Проверяем, распределены ли сотрудники по другим этапам
        emps_in_other_stages = sum(len(s['emps']) for s in stage_info[1:])
        # Проверяем, содержит ли первый этап всех сотрудников И сотрудники не распределены по другим этапам
        # ИЛИ если сотрудники распределены, но первый этап содержит больше 50% всех сотрудников
        if not emp_from_reference and ((len(first_stage['emps']) >= len(allowed_employees) * 0.8 and emps_in_other_stages == 0) or
                                     (len(first_stage['emps']) >= len(allowed_employees) * 0.5 and emps_in_other_stages > 0)):
            warnings.append("ОБНАРУЖЕНО: Сотрудники распределены неравномерно. Перераспределяем по этапам.")
            # Собираем всех сотрудников из всех этапов
            all_emps = []
            for stage in stage_info:
                all_emps.extend(stage['emps'])
                stage['emps'] = []
            # Распределяем сотрудников по этапам
            redistribute_employees(stage_info, all_emps)
    
    # Пересобираем план с учётом перераспределения
    validated_plan = stages[0]  # Заголовок плана
    for i, stage_data in enumerate(stage_info):
        # Обновляем строки подразделений, техники и сотрудников в контенте
        content = stage_data['content']
        
        # Обновляем подразделения
        sub_match = re.search(r'-\s*Подразделения:\s*([^\n]*)', content)
        if sub_match:
            if stage_data['subs']:
                new_sub_line = f"- Подразделения: {', '.join(stage_data['subs'])}"
                content = content.replace(sub_match.group(0), new_sub_line)
            else:
                content = content.replace(sub_match.group(0), "- Подразделения: Не требуется")
        
        # Обновляем технику
        tech_match = re.search(r'-\s*Техника:\s*([^\n]*)', content)
        if tech_match:
            if stage_data['techs']:
                new_tech_line = f"- Техника: {', '.join(stage_data['techs'])}"
                content = content.replace(tech_match.group(0), new_tech_line)
            else:
                content = content.replace(tech_match.group(0), "- Техника: Не требуется")
        
        # Обновляем сотрудников
        emp_match = re.search(r'-\s*Сотрудники:\s*([^\n]*)', content)
        if emp_match:
            if stage_data['emps']:
                new_emp_line = f"- Сотрудники: {', '.join(stage_data['emps'])}"
                content = content.replace(emp_match.group(0), new_emp_line)
            else:
                content = content.replace(emp_match.group(0), "- Сотрудники: Не требуются")
        
        # Добавляем сохранённые строки "Действия:" и "Пояснение:" если они были
        if stage_data.get('actions'):
            # Проверяем, есть ли уже строка "Действия:" в контенте
            if not re.search(r'-\s*Действия:', content):
                # Добавляем после строки сотрудников
                content += "\n" + stage_data['actions']
        
        if stage_data.get('explanation'):
            # Проверяем, есть ли уже строка "Пояснение:" в контенте
            if not re.search(r'-\s*Пояснение:', content):
                # Добавляем после строки действий или в конец
                content += "\n" + stage_data['explanation']
        
        validated_plan += stage_data['header'] + content
    
    # Пересчитываем использованные элементы после перераспределения
    used_subs = set()
    used_techs = set()
    used_emps = set()
    for stage in stage_info:
        used_subs.update(stage['subs'])
        used_techs.update(stage['techs'])
        used_emps.update(stage['emps'])
    
    # Проверяем, что все допустимые элементы были использованы
    # Но только если списки не были загружены из справочника
    missing_subs = allowed_sub_set - used_subs if not sub_from_reference else set()
    missing_techs = allowed_tech_set - used_techs if not tech_from_reference else set()
    missing_emps = allowed_emp_set - used_emps if not emp_from_reference else set()
    
    # Если есть пропущенные элементы, добавляем их в подходящие этапы
    # КРИТИЧЕСКИ ВАЖНО: Добавляем пропущенные элементы в подходящие этапы автоматически
    # Это гарантирует, что все ресурсы будут использованы в плане
    # НО только если списки не были загружены из справочника (тогда не нужно добавлять пропущенные)
    
    # Находим все этапы в валидированном плане
    stage_pattern = r'(\*\*Этап\s+\d+:[^*]+\*\*)'
    stages = re.split(stage_pattern, validated_plan)
    
    if len(stages) > 1:
        # Добавляем пропущенные подразделения в подходящие этапы
        if missing_subs and not sub_from_reference:
            logger.debug(f"[validate_work_plan] Добавляем пропущенные подразделения: {missing_subs}")
            
            # Классифицируем пропущенные подразделения по типам этапов
            assessment_subs = []
            diagnosis_subs = []
            clearance_subs = []
            stabilization_subs = []
            restoration_subs = []
            final_check_subs = []
            
            for sub in missing_subs:
                sub_lower = sub.lower()
                if any(keyword in sub_lower for keyword in ['мчс', 'рсчс']):
                    clearance_subs.append(sub)
                elif any(keyword in sub_lower for keyword in ['да', 'даб', 'дабс']):
                    assessment_subs.append(sub)
                elif any(keyword in sub_lower for keyword in ['ди', 'цди', 'дцс']):
                    diagnosis_subs.append(sub)
                elif any(keyword in sub_lower for keyword in ['дцуп', 'двс']):
                    assessment_subs.append(sub)
                elif any(keyword in sub_lower for keyword in ['дип', 'двп']):
                    stabilization_subs.append(sub)
                elif any(keyword in sub_lower for keyword in ['мч']):
                    restoration_subs.append(sub)
                else:
                    restoration_subs.append(sub)
            
            # Добавляем подразделения в подходящие этапы
            for i in range(1, len(stages), 2):
                if i + 1 >= len(stages):
                    break
                
                header = stages[i]
                content = stages[i + 1]
                stage_type = _get_stage_type(header)
                
                # Определяем, какие подразделения добавить для этого этапа
                subs_to_add = []
                if stage_type == 'assessment':
                    subs_to_add = assessment_subs
                elif stage_type == 'diagnosis':
                    subs_to_add = diagnosis_subs
                elif stage_type == 'clearance':
                    subs_to_add = clearance_subs
                elif stage_type == 'restoration':
                    header_lower = header.lower()
                    if any(keyword in header_lower for keyword in ['фиксация', 'стабилизация', 'закрепление', 'подпорка']):
                        subs_to_add = stabilization_subs
                    else:
                        subs_to_add = restoration_subs
                elif stage_type == 'final_check':
                    subs_to_add = final_check_subs
                
                if not subs_to_add:
                    continue
                
                # Находим строку подразделений
                sub_match = re.search(r'-\s*Подразделения:\s*([^\n]*)', content)
                if sub_match:
                    sub_line = sub_match.group(1).strip()
                    # Если там "Не требуется", заменяем на подходящие подразделения
                    if sub_line.lower().startswith("не требуется"):
                        new_sub_line = f"- Подразделения: {', '.join(subs_to_add)}"
                        content = content.replace(sub_match.group(0), new_sub_line)
                        stages[i + 1] = content
                        used_subs.update(subs_to_add)
                        logger.debug(f"[validate_work_plan] Этап {i//2 + 1} ({stage_type}): заменено 'Не требуется' на {subs_to_add}")
                    else:
                        # Добавляем подходящие подразделения к существующим (без дублирования)
                        sub_items = [s.strip() for s in re.split(r'[;,]', sub_line)]
                        added = []
                        for sub in subs_to_add:
                            if sub not in sub_items:
                                sub_items.append(sub)
                                added.append(sub)
                        if added:
                            new_sub_line = f"- Подразделения: {', '.join(sub_items)}"
                            content = content.replace(sub_match.group(0), new_sub_line)
                            stages[i + 1] = content
                            used_subs.update(added)
                            logger.debug(f"[validate_work_plan] Этап {i//2 + 1} ({stage_type}): добавлены подразделения {added}")
            if used_subs:
                warnings.append(f"Добавлены пропущенные подразделения в этапы: {', '.join(used_subs)}")
    
    if len(stages) > 1 and not tech_from_reference and not emp_from_reference:
        # Добавляем пропущенную технику в подходящие этапы
        if missing_techs:
            logger.debug(f"[validate_work_plan] Добавляем пропущенную технику: {missing_techs}")
            
            # Классифицируем пропущенную технику по типам этапов
            diagnosis_techs = []  # Для этапа диагностики
            clearance_techs = []   # Для этапа расчистки
            restoration_techs = []  # Для этапа восстановления
            
            for tech in missing_techs:
                tech_lower = tech.lower()
                # Техника для диагностики
                if any(keyword in tech_lower for keyword in ['георадар', 'датчик', 'нивелир', 'измерительный', 'прибор']):
                    diagnosis_techs.append(tech)
                # Техника для расчистки
                elif any(keyword in tech_lower for keyword in ['экскаватор', 'бульдозер', 'погрузчик']):
                    clearance_techs.append(tech)
                # Техника для восстановления
                else:
                    restoration_techs.append(tech)
            
            # Добавляем технику в подходящие этапы
            for i in range(1, len(stages), 2):
                if i + 1 >= len(stages):
                    break
                
                header = stages[i]
                content = stages[i + 1]
                stage_type = _get_stage_type(header)
                
                # Пропускаем этапы документирования
                if stage_type == 'documentation':
                    continue
                
                # Определяем, какую технику добавить для этого этапа
                techs_to_add = []
                if stage_type == 'diagnosis':
                    techs_to_add = diagnosis_techs
                elif stage_type == 'clearance':
                    techs_to_add = clearance_techs
                elif stage_type == 'restoration':
                    techs_to_add = restoration_techs
                elif stage_type == 'assessment':
                    techs_to_add = diagnosis_techs  # Для оценки тоже используем диагностическую технику
                elif stage_type == 'final_check':
                    techs_to_add = diagnosis_techs  # Для проверки тоже используем диагностическую технику
                
                if not techs_to_add:
                    continue
                
                # Находим строку техники
                tech_match = re.search(r'-\s*Техника:\s*([^\n]*)', content)
                if tech_match:
                    tech_line = tech_match.group(1).strip()
                    # Если там "Не требуется", заменяем на подходящую технику
                    if tech_line.lower().startswith("не требуется"):
                        new_tech_line = f"- Техника: {', '.join(techs_to_add)}"
                        content = content.replace(tech_match.group(0), new_tech_line)
                        stages[i + 1] = content
                        used_techs.update(techs_to_add)
                        logger.debug(f"[validate_work_plan] Этап {i//2 + 1} ({stage_type}): заменено 'Не требуется' на {techs_to_add}")
                    else:
                        # Добавляем подходящую технику к существующей (без дублирования)
                        tech_items = [t.strip() for t in re.split(r'[;,]', tech_line)]
                        added = []
                        for tech in techs_to_add:
                            if tech not in tech_items:
                                tech_items.append(tech)
                                added.append(tech)
                        if added:
                            new_tech_line = f"- Техника: {', '.join(tech_items)}"
                            content = content.replace(tech_match.group(0), new_tech_line)
                            stages[i + 1] = content
                            used_techs.update(added)
                            logger.debug(f"[validate_work_plan] Этап {i//2 + 1} ({stage_type}): добавлена техника {added}")
            if used_techs:
                warnings.append(f"Добавлена пропущенная техника в этапы: {', '.join(used_techs)}")
        
        # Добавляем пропущенных сотрудников в подходящие этапы
        if missing_emps:
            logger.debug(f"[validate_work_plan] Добавляем пропущенных сотрудников: {missing_emps}")
            
            # Классифицируем пропущенных сотрудников по типам этапов
            assessment_emps = []
            diagnosis_emps = []
            clearance_emps = []
            stabilization_emps = []
            restoration_emps = []
            final_check_emps = []
            
            for emp in missing_emps:
                emp_lower = emp.lower()
                if any(keyword in emp_lower for keyword in ['машинист экскаватор', 'машинист бульдозер', 'водитель', 'оператор погрузчик', 'диспетчер', 'сигналист']):
                    clearance_emps.append(emp)
                elif any(keyword in emp_lower for keyword in ['медицинск', 'врач', 'фельдшер', 'охран', 'начальник', 'руководитель']):
                    assessment_emps.append(emp)
                elif any(keyword in emp_lower for keyword in ['инженер-путеец', 'инженер путеец', 'геодезист', 'обследователь']):
                    diagnosis_emps.append(emp)
                elif any(keyword in emp_lower for keyword in ['стропальщик', 'такелажник', 'сигналист']):
                    stabilization_emps.append(emp)
                elif any(keyword in emp_lower for keyword in ['машинист кран', 'машинист путеукладчик', 'машинист балласторазбрасыватель', 'машинист впо', 'сварщик', 'монтер пути', 'механик', 'электромонтер', 'электросварщик']):
                    restoration_emps.append(emp)
                elif any(keyword in emp_lower for keyword in ['мастер пути', 'инженер-путеец', 'машинист дрезины', 'приемщик', 'контролер']):
                    final_check_emps.append(emp)
                else:
                    restoration_emps.append(emp)
            
            # Добавляем сотрудников в подходящие этапы
            for i in range(1, len(stages), 2):
                if i + 1 >= len(stages):
                    break
                
                header = stages[i]
                content = stages[i + 1]
                stage_type = _get_stage_type(header)
                
                # Определяем, каких сотрудников добавить для этого этапа
                emps_to_add = []
                if stage_type == 'assessment':
                    emps_to_add = assessment_emps
                elif stage_type == 'diagnosis':
                    emps_to_add = diagnosis_emps
                elif stage_type == 'clearance':
                    emps_to_add = clearance_emps
                elif stage_type == 'restoration':
                    header_lower = header.lower()
                    if any(keyword in header_lower for keyword in ['фиксация', 'стабилизация', 'закрепление', 'подпорка']):
                        emps_to_add = stabilization_emps
                    else:
                        emps_to_add = restoration_emps
                elif stage_type == 'final_check':
                    emps_to_add = final_check_emps
                
                if not emps_to_add:
                    continue
                
                # Находим строку сотрудников
                emp_match = re.search(r'-\s*Сотрудники:\s*([^\n]*)', content)
                if emp_match:
                    emp_line = emp_match.group(1).strip()
                    # Если там "Не требуются", заменяем на подходящих сотрудников
                    if emp_line.lower().startswith("не требуются"):
                        new_emp_line = f"- Сотрудники: {', '.join(emps_to_add)}"
                        content = content.replace(emp_match.group(0), new_emp_line)
                        stages[i + 1] = content
                        used_emps.update(emps_to_add)
                        logger.debug(f"[validate_work_plan] Этап {i//2 + 1} ({stage_type}): заменено 'Не требуются' на {emps_to_add}")
                    else:
                        # Добавляем подходящих сотрудников к существующим (без дублирования)
                        emp_items = [e.strip() for e in re.split(r'[;,]', emp_line)]
                        added = []
                        for emp in emps_to_add:
                            if emp not in emp_items:
                                emp_items.append(emp)
                                added.append(emp)
                        if added:
                            new_emp_line = f"- Сотрудники: {', '.join(emp_items)}"
                            content = content.replace(emp_match.group(0), new_emp_line)
                            stages[i + 1] = content
                            used_emps.update(added)
                            logger.debug(f"[validate_work_plan] Этап {i//2 + 1} ({stage_type}): добавлены сотрудники {added}")
            if used_emps:
                warnings.append(f"Добавлены пропущенные сотрудники в этапы: {', '.join(used_emps)}")
        
        # Пересобираем план с изменениями из stages (обновлённого)
        validated_plan = stages[0]  # Заголовок плана
        for i in range(1, len(stages), 2):
            if i + 1 < len(stages):
                validated_plan += stages[i] + stages[i + 1]
    
    # Если после добавления остались пропущенные элементы, добавляем предупреждения
    if missing_subs:
        warnings.append(f"ВНИМАНИЕ: Следующие подразделения не были использованы в плане: {', '.join(missing_subs)}")
    if missing_techs:
        warnings.append(f"ВНИМАНИЕ: Следующая техника не была использована в плане: {', '.join(missing_techs)}")
    if missing_emps:
        warnings.append(f"ВНИМАНИЕ: Следующие сотрудники не были использованы в плане: {', '.join(missing_emps)}")
    
    return validated_plan, warnings


def process_model_response(response_text: str, original_question: str, sources: List[Dict], session_id: str = None) -> Dict:
    """Обрабатывает ответ модели для шага 1 (подразделения)."""
    if not response_text:
        return {
            "subdivisions": [],
            "analysis": "Модель не вернула ответ",
            "sources": sources,
            "status": "error"
        }

    subdivisions = extract_subdivisions_from_model_response(response_text)
    analysis_parts = []
    for sub in subdivisions:
        if sub in ALLOWED_SUBDIVISIONS:
            analysis_parts.append(f"{sub} - {ALLOWED_SUBDIVISIONS[sub]}")

    if analysis_parts:
        analysis = "\n".join(analysis_parts)
        status = "success"
    else:
        analysis = "Не удалось определить необходимые подразделения на основе предоставленной информации."
        status = "error"

    return {
        "subdivisions": list(set(subdivisions)),
        "analysis": analysis,
        "sources": sources,
        "status": status
    }


# Функция для сброса кэша справочников (полезно для тестирования)
def reset_reference_cache():
    """Сбрасывает кэшированные справочники."""
    global _EMPLOYEES_REFERENCE, _TECHNIC_REFERENCE
    _EMPLOYEES_REFERENCE = None
    _TECHNIC_REFERENCE = None
    logger.info("Кэш справочников сброшен")
