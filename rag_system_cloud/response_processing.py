# response_processing.py
import re
import csv
import os
from typing import List, Dict, Optional, Tuple, Set
import logging
from retrieval import extract_keywords
from config import (
    ALLOWED_SUBDIVISIONS,
    EMPLOYEES_REFERENCE_CSV,
    TECHNIC_REFERENCE_CSV
)
from thefuzz import fuzz
import app_state

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


def validate_item_with_fuzzy_match(
    item: str,
    reference_set: Set[str],
    threshold: float = 0.76
) -> Tuple[bool, str]:
    """
    Валидирует элемент по справочнику с использованием нечёткого сопоставления.
    
    Args:
        item: Проверяемый элемент
        reference_set: Справочник (множество допустимых значений)
        threshold: Порог схожести для нечёткого сопоставления (0-1)
    
    Returns:
        Кортеж (валиден_ли, исправленное_название)
    """
    if not item or not reference_set:
        return False, item
    
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
        is_valid, corrected_name = validate_item_with_fuzzy_match(item, reference_set, threshold=0.80)
        
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


def extract_work_plan_from_model_response(response_text: str) -> str:
    """Извлекает план работ из ответа модели."""
    if not response_text:
        return ""
    response_text = clean_text_from_special_tokens(response_text)
    clean_plan = re.sub(r"ИНСТРУКЦИИ.*?(?=\n\n|\Z)", "", response_text, flags=re.DOTALL)
    clean_plan = re.sub(r"Ответ:\s*", "", clean_plan)
    
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
    # Исключаем заголовки этапов из удаления
    clean_plan = re.sub(r'\n\n\*\*(?!Этап\s+\d+:)[А-Яа-яA-Za-z\s:]+\*\*.*', '', clean_plan, flags=re.DOTALL)
    
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
    
    if any(keyword in header_lower for keyword in ['оценка', 'безопасность', 'разведка', 'эвакуация']):
        return 'assessment'
    elif any(keyword in header_lower for keyword in ['диагностика', 'обследование', 'анализ']):
        return 'diagnosis'
    elif any(keyword in header_lower for keyword in ['расчистка', 'подготовка', 'завалы']):
        return 'clearance'
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
    clearance_tech = []   # Для этапа расчистки
    restoration_tech = [] # Для этапа восстановления
    final_check_tech = [] # Для этапа финальной проверки
    
    for tech in technics:
        tech_lower = tech.lower()
        
        # Техника для оценки и безопасности
        if any(keyword in tech_lower for keyword in ['рация', 'связь', 'реанимобил', 'скорой', 'пожарн', 'спасательн', 'светоотраж']):
            assessment_tech.append(tech)
        # Техника для расчистки и подготовки
        elif any(keyword in tech_lower for keyword in ['экскаватор', 'бульдозер', 'погрузчик', 'автомобиль камаз', 'грузовик']):
            clearance_tech.append(tech)
        # Техника для восстановления
        elif any(keyword in tech_lower for keyword in ['кран', 'путеукладчик', 'домкрат', 'виброплита', 'каток', 'рельсорез', 'рельсосвар', 'шпалоподбойник', 'балласторазбрасыватель', 'впо', 'щом', 'бум', 'мср']):
            restoration_tech.append(tech)
        # Техника для финальной проверки
        elif any(keyword in tech_lower for keyword in ['дрезина', 'измерительн', 'нивелир', 'георадар', 'датчик']):
            final_check_tech.append(tech)
        else:
            # По умолчанию - для восстановления
            restoration_tech.append(tech)
    
    # Распределяем технику по этапам
    for stage in stage_info:
        stage_type = _get_stage_type(stage['header'])
        
        if stage_type == 'assessment':
            stage['techs'].extend(assessment_tech)
        elif stage_type == 'clearance':
            stage['techs'].extend(clearance_tech)
        elif stage_type == 'restoration':
            stage['techs'].extend(restoration_tech)
        elif stage_type == 'final_check':
            stage['techs'].extend(final_check_tech)
        elif stage_type == 'diagnosis':
            # Для диагностики добавляем измерительную технику
            stage['techs'].extend(final_check_tech)
        # Для этапов документирования техника не добавляется


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
    restoration_emps = [] # Для этапа восстановления
    final_check_emps = [] # Для этапа финальной проверки
    
    for emp in employees:
        emp_lower = emp.lower()
        
        # Сотрудники для оценки и безопасности
        if any(keyword in emp_lower for keyword in ['медицинск', 'врач', 'фельдшер', 'охран', 'диспетчер']):
            assessment_emps.append(emp)
        # Сотрудники для диагностики
        elif any(keyword in emp_lower for keyword in ['инженер-путеец', 'инженер путеец', 'геодезист']):
            diagnosis_emps.append(emp)
        # Сотрудники для расчистки
        elif any(keyword in emp_lower for keyword in ['машинист экскаватор', 'машинист бульдозер', 'водитель']):
            clearance_emps.append(emp)
        # Сотрудники для восстановления
        elif any(keyword in emp_lower for keyword in ['машинист кран', 'машинист путеукладчик', 'машинист балласторазбрасыватель', 'машинист впо', 'стропальщик', 'сварщик', 'монтер пути', 'механик']):
            restoration_emps.append(emp)
        # Сотрудники для финальной проверки
        elif any(keyword in emp_lower for keyword in ['мастер пути', 'инженер-путеец', 'машинист дрезины']):
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
            stage['emps'].extend(restoration_emps)
        elif stage_type == 'final_check':
            stage['emps'].extend(final_check_emps)
        # Для этапов документирования сотрудники не добавляются


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
        
        stage_data = {
            'header': header,
            'content': content,
            'subs': [],
            'techs': [],
            'emps': []
        }
        
        # Валидируем подразделения в строке "Подразделения: ..."
        sub_match = re.search(r'-\s*Подразделения:\s*(.*?)(?=\n-\s*|$)', content, re.DOTALL)
        if sub_match:
            sub_line = sub_match.group(1).strip()
            # Извлекаем аббревиатуры подразделений
            found_subs = re.findall(r'\b([А-ЯA-Z]{2,6})\b', sub_line)
            validated_subs = []
            for sub in found_subs:
                if sub in allowed_sub_set:
                    validated_subs.append(sub)
                    used_subs.add(sub)
                    stage_data['subs'].append(sub)
                else:
                    warnings.append(f"Подразделение '{sub}' не в списке допустимых")
            # Заменяем строку подразделений
            if validated_subs:
                new_sub_line = f"- Подразделения: {', '.join(validated_subs)}"
                content = content.replace(sub_match.group(0), new_sub_line)
            else:
                content = content.replace(sub_match.group(0), "- Подразделения: Не требуется")
        
        # Валидируем технику в строке "Техника: ..."
        tech_match = re.search(r'-\s*Техника:\s*(.*?)(?=\n-\s*|$)', content, re.DOTALL)
        if tech_match:
            tech_line = tech_match.group(1).strip()
            # Разбиваем по запятым и точкам с запятой
            tech_items = [t.strip() for t in re.split(r'[;,]', tech_line)]
            validated_techs = []
            for tech in tech_items:
                # Пропускаем пустые элементы и элементы, начинающиеся с "не требуется"
                if not tech or tech.lower().startswith("не требуется"):
                    continue
                if tech in allowed_tech_set:
                    validated_techs.append(tech)
                    used_techs.add(tech)
                    stage_data['techs'].append(tech)
                else:
                    # Проверяем нечёткое совпадение
                    found = False
                    for allowed in allowed_tech_set:
                        ratio = fuzz.ratio(tech.lower(), allowed.lower())
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
        
        # Проверяем наличие строки "Сотрудники:" и добавляем её, если отсутствует
        emp_match = re.search(r'-\s*Сотрудники:\s*(.*?)(?=\n-\s*|$)', content, re.DOTALL)
        if not emp_match:
            # Если строки "Сотрудники:" нет, добавляем её перед строкой "Действия:" или "Пояснение:"
            actions_match = re.search(r'-\s*Действия:', content)
            explanation_match = re.search(r'-\s*Пояснение:', content)
            
            if actions_match:
                # Вставляем перед "Действия:"
                content = content.replace(actions_match.group(0), "- Сотрудники: Не требуются\n" + actions_match.group(0))
                warnings.append(f"Добавлена отсутствующая строка 'Сотрудники:' в этап")
            elif explanation_match:
                # Вставляем перед "Пояснение:"
                content = content.replace(explanation_match.group(0), "- Сотрудники: Не требуются\n" + explanation_match.group(0))
                warnings.append(f"Добавлена отсутствующая строка 'Сотрудники:' в этап")
            else:
                # Добавляем в конец этапа
                content += "\n- Сотрудники: Не требуются"
                warnings.append(f"Добавлена отсутствующая строка 'Сотрудники:' в этап")
            # Теперь валидируем добавленную строку
            emp_match = re.search(r'-\s*Сотрудники:\s*(.*?)(?=\n-\s*|$)', content, re.DOTALL)
        
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
        
        # Добавляем заголовок и валидированное содержание
        validated_plan += header + content
        stage_info.append(stage_data)
    
    # Проверяем, что все допустимые элементы были использованы
    missing_subs = allowed_sub_set - used_subs
    missing_techs = allowed_tech_set - used_techs
    missing_emps = allowed_emp_set - used_emps
    
    # ПРОВЕРКА: Если в первом этапе перечислена ВСЯ техника и ВСЕ сотрудники
    # ПЕРЕРАСПРЕДЕЛЯЕМ их по этапам логически
    # НО только если ресурсы НЕ распределены по другим этапам
    if len(stage_info) > 1:
        first_stage = stage_info[0]
        
        # Проверяем, распределена ли техника по другим этапам
        techs_in_other_stages = sum(len(s['techs']) for s in stage_info[1:])
        # Проверяем, содержит ли первый этап всю технику И техника не распределена по другим этапам
        if len(first_stage['techs']) >= len(allowed_technics) * 0.8 and techs_in_other_stages == 0:
            warnings.append("ОБНАРУЖЕНО: Вся техника сосредоточена в первом этапе. Перераспределяем по этапам.")
            # Очищаем технику из первого этапа
            all_techs = list(first_stage['techs'])
            first_stage['techs'] = []
            # Распределяем технику по этапам
            redistribute_technics(stage_info, all_techs)
        
        # Проверяем, распределены ли сотрудники по другим этапам
        emps_in_other_stages = sum(len(s['emps']) for s in stage_info[1:])
        # Проверяем, содержит ли первый этап всех сотрудников И сотрудники не распределены по другим этапам
        if len(first_stage['emps']) >= len(allowed_employees) * 0.8 and emps_in_other_stages == 0:
            warnings.append("ОБНАРУЖЕНО: Все сотрудники сосредоточены в первом этапе. Перераспределяем по этапам.")
            # Очищаем сотрудников из первого этапа
            all_emps = list(first_stage['emps'])
            first_stage['emps'] = []
            # Распределяем сотрудников по этапам
            redistribute_employees(stage_info, all_emps)
    
    # Пересобираем план с учётом перераспределения
    validated_plan = stages[0]  # Заголовок плана
    for i, stage_data in enumerate(stage_info):
        # Обновляем строки техники и сотрудников в контенте
        content = stage_data['content']
        
        # Обновляем технику
        tech_match = re.search(r'-\s*Техника:\s*(.*?)(?=\n-\s*|$)', content, re.DOTALL)
        if tech_match:
            if stage_data['techs']:
                new_tech_line = f"- Техника: {', '.join(stage_data['techs'])}"
                content = content.replace(tech_match.group(0), new_tech_line)
            else:
                content = content.replace(tech_match.group(0), "- Техника: Не требуется")
        
        # Обновляем сотрудников
        emp_match = re.search(r'-\s*Сотрудники:\s*(.*?)(?=\n-\s*|$)', content, re.DOTALL)
        if emp_match:
            if stage_data['emps']:
                new_emp_line = f"- Сотрудники: {', '.join(stage_data['emps'])}"
                content = content.replace(emp_match.group(0), new_emp_line)
            else:
                content = content.replace(emp_match.group(0), "- Сотрудники: Не требуются")
        
        validated_plan += stage_data['header'] + content
    
    # Пересчитываем использованные элементы после перераспределения
    used_techs = set()
    used_emps = set()
    for stage in stage_info:
        used_techs.update(stage['techs'])
        used_emps.update(stage['emps'])
    
    # Проверяем, что все допустимые элементы были использованы
    missing_subs = allowed_sub_set - used_subs
    missing_techs = allowed_tech_set - used_techs
    missing_emps = allowed_emp_set - used_emps
    
    # Если есть пропущенные элементы, добавляем их в подходящие этапы
    # КРИТИЧЕСКИ ВАЖНО: Добавляем пропущенные элементы в подходящие этапы автоматически
    # Это гарантирует, что все ресурсы будут использованы в плане
    
    # Находим все этапы в валидированном плане
    stage_pattern = r'(\*\*Этап\s+\d+:[^*]+\*\*)'
    stages = re.split(stage_pattern, validated_plan)
    
    if len(stages) > 1:
        # Добавляем пропущенную технику в подходящие этапы
        if missing_techs:
            # Определяем подходящие этапы для добавления техники
            # Пропускаем этапы документирования и анализа
            for i in range(1, len(stages), 2):
                if i + 1 >= len(stages):
                    break
                
                header = stages[i]
                content = stages[i + 1]
                
                # Проверяем, что это не этап документирования
                if re.search(r'(документ|анализ|оформление|завершение)', header, re.IGNORECASE):
                    continue
                
                # Находим строку техники
                tech_match = re.search(r'-\s*Техника:\s*(.*?)(?=\n-\s*|$)', content, re.DOTALL)
                if tech_match:
                    tech_line = tech_match.group(1).strip()
                    # Если там "Не требуется", заменяем на пропущенную технику
                    if tech_line.lower().startswith("не требуется"):
                        # Добавляем пропущенную технику
                        tech_to_add = list(missing_techs)
                        new_tech_line = f"- Техника: {', '.join(tech_to_add)}"
                        content = content.replace(tech_match.group(0), new_tech_line)
                        stages[i + 1] = content
                        used_techs.update(missing_techs)
                        missing_techs.clear()
                        warnings.append(f"Добавлена пропущенная техника в этап: {', '.join(tech_to_add)}")
                        break
                    else:
                        # Добавляем пропущенную технику к существующей
                        tech_items = [t.strip() for t in re.split(r'[;,]', tech_line)]
                        tech_items.extend(list(missing_techs))
                        new_tech_line = f"- Техника: {', '.join(tech_items)}"
                        content = content.replace(tech_match.group(0), new_tech_line)
                        stages[i + 1] = content
                        used_techs.update(missing_techs)
                        tech_added = list(missing_techs)
                        missing_techs.clear()
                        warnings.append(f"Добавлена пропущенная техника в этап: {', '.join(tech_added)}")
                        break
        
        # Добавляем пропущенных сотрудников в подходящие этапы
        if missing_emps:
            for i in range(1, len(stages), 2):
                if i + 1 >= len(stages):
                    break
                
                header = stages[i]
                content = stages[i + 1]
                
                # Находим строку сотрудников
                emp_match = re.search(r'-\s*Сотрудники:\s*(.*?)(?=\n-\s*|$)', content, re.DOTALL)
                if emp_match:
                    emp_line = emp_match.group(1).strip()
                    # Если там "Не требуются", заменяем на пропущенных сотрудников
                    if emp_line.lower().startswith("не требуются"):
                        # Добавляем пропущенных сотрудников
                        emps_to_add = list(missing_emps)
                        new_emp_line = f"- Сотрудники: {', '.join(emps_to_add)}"
                        content = content.replace(emp_match.group(0), new_emp_line)
                        stages[i + 1] = content
                        used_emps.update(missing_emps)
                        missing_emps.clear()
                        warnings.append(f"Добавлены пропущенные сотрудники в этап: {', '.join(emps_to_add)}")
                        break
                    else:
                        # Добавляем пропущенных сотрудников к существующим
                        emp_items = [e.strip() for e in re.split(r'[;,]', emp_line)]
                        emp_items.extend(list(missing_emps))
                        new_emp_line = f"- Сотрудники: {', '.join(emp_items)}"
                        content = content.replace(emp_match.group(0), new_emp_line)
                        stages[i + 1] = content
                        used_emps.update(missing_emps)
                        emps_added = list(missing_emps)
                        missing_emps.clear()
                        warnings.append(f"Добавлены пропущенные сотрудники в этап: {', '.join(emps_added)}")
                        break
        
        # Пересобираем план с изменениями
        validated_plan = ""
        for i in range(len(stages)):
            validated_plan += stages[i]
    
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
