# ingestion.py
import os
import csv
import logging
from langchain_community.document_loaders import Docx2txtLoader
from simple_md_loader import SimpleMarkdownLoader
from langchain.schema import Document
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.vectorstores import Chroma

from config import (
    DOCS_FOLDER_TECHNIC, DOCS_FOLDER_WORK_PLAN, DOCS_FOLDER_ALL_DOCS,
    DOCS_FOLDER_EMPLOYEES,  # добавлено
    DOCS_FOLDER_SUBDIVISIONS,  # добавлено
    PERSIST_DIRECTORY_TECHNIC, PERSIST_DIRECTORY_WORK_PLAN, PERSIST_DIRECTORY_ALL_DOCS,
    PERSIST_DIRECTORY_EMPLOYEES,  # добавлено
    PERSIST_DIRECTORY_SUBDIVISIONS,  # добавлено
    CSV_FILE_PATH,EMPLOYEE_EXAMPLES_CSV,
    PERSIST_DIRECTORY_EMPLOYEES_EXAMPLES,
    PERSIST_DIRECTORY_SUBDIVISIONS_EXAMPLES,
    SUBDIVISION_EXAMPLES_CSV,
    TECHNIC_REFERENCE_CSV,
    EMPLOYEES_REFERENCE_CSV,
    ALLOWED_SUBDIVISIONS
)
import app_state

logger = logging.getLogger(__name__)


def load_accidents_examples(csv_file_path: str):
    """Загружает примеры аварий из CSV-файла (разделитель $)."""
    examples = []
    try:
        logger.info(f"[CSV] Попытка загрузить CSV файл: {csv_file_path}")
        abs_path = os.path.abspath(csv_file_path)
        if os.path.exists(abs_path):
            with open(abs_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile, delimiter='$')
                row_count = 0
                error_count = 0
                for i, row in enumerate(reader):
                    row_count += 1
                    try:
                        description = row.get("Описание аварии", "")
                        subdivisions = row.get("Список подразделений", "")
                        if description is None: description = ""
                        if subdivisions is None: subdivisions = ""
                        if description.strip() or subdivisions.strip():
                            examples.append({
                                "description": description.strip(),
                                "subdivisions": subdivisions.strip()
                            })
                    except Exception as row_error:
                        error_count += 1
                        logger.error(f"[CSV] Ошибка в строке {i+1}: {row_error}")

                logger.info(f"[CSV] Всего строк: {row_count}, ошибок: {error_count}, загружено: {len(examples)}")
        else:
            logger.error(f"[CSV] Файл {abs_path} не найден")
    except Exception as e:
        logger.error(f"[CSV] Ошибка загрузки: {e}", exc_info=True)
    return examples


def ingest_docs_for_type(folder_path: str, persist_directory: str, use_subfolders: bool = False):
    """
    Индексирует документы .docx и .md из указанной папки в векторную БД,
    используя семантическое разделение на чанки (SemanticChunker).
    
    Args:
        folder_path: Путь к папке с документами
        persist_directory: Путь для сохранения векторной БД
        use_subfolders: Если True, ищет файлы рекурсивно в подпапках и добавляет метаданные о подразделении
    """
    logger.info(f"[INGEST] Начало индексации: {folder_path} -> {persist_directory}, use_subfolders={use_subfolders}")
    try:
        if not os.path.exists(folder_path):
            logger.error(f"[INGEST] Папка не найдена: {folder_path}")
            return False, "Папка не найдена"

        # Ищем файлы .docx и .md
        if use_subfolders:
            # Рекурсивный поиск в подпапках + файлы в корне
            doc_files = []
            # Сначала файлы в корне
            for f in os.listdir(folder_path):
                if os.path.isfile(os.path.join(folder_path, f)) and (f.endswith('.docx') or f.endswith('.md')):
                    # Пропускаем временные файлы Word (начинаются с ~$)
                    if not f.startswith('~$'):
                        doc_files.append(os.path.join(folder_path, f))
            # Затем файлы в подпапках
            for root, dirs, files in os.walk(folder_path):
                # Пропускаем корневую директорию (уже обработали)
                if root == folder_path:
                    continue
                for f in files:
                    if f.endswith('.docx') or f.endswith('.md'):
                        # Пропускаем временные файлы Word (начинаются с ~$)
                        if not f.startswith('~$'):
                            doc_files.append(os.path.join(root, f))
        else:
            # Поиск только в корневой папке
            doc_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path)
                         if (f.endswith('.docx') or f.endswith('.md')) and not f.startswith('~$')]
        
        logger.info(f"[INGEST] Найдено файлов: {len(doc_files)}")
        
        if not doc_files:
            logger.warning(f"[INGEST] Файлы .docx или .md не найдены в {folder_path}")
            return False, "Файлы .docx или .md не найдены"

        text_splitter = SemanticChunker(
            embeddings=app_state.embedding_model,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=0.8,
            min_chunk_size=100,
        )

        all_splits = []
        for i, file_path in enumerate(doc_files):
            logger.info(f"[INGEST] Обработка файла {i+1}/{len(doc_files)}: {os.path.basename(file_path)}")
            # Выбираем загрузчик в зависимости от расширения файла
            try:
                if file_path.endswith('.docx'):
                    loader = Docx2txtLoader(file_path)
                elif file_path.endswith('.md'):
                    loader = SimpleMarkdownLoader(file_path)
                else:
                    continue
                
                docs = loader.load()
            except Exception as e:
                logger.error(f"[INGEST] Ошибка загрузки файла {file_path}: {e}")
                continue
            for doc in docs:
                # Определяем подразделение из пути к файлу
                subdivision = None
                if use_subfolders:
                    # Получаем имя папки, в которой находится файл
                    relative_path = os.path.relpath(file_path, folder_path)
                    parts = relative_path.split(os.sep)
                    if len(parts) > 1:
                        folder_name = parts[0]
                        # Проверяем, соответствует ли имя папки коду подразделения
                        if folder_name in ALLOWED_SUBDIVISIONS:
                            subdivision = folder_name
                
                # Важно: сохраняем метаданные, где есть поле source с путём к файлу
                chunks = text_splitter.split_text(doc.page_content)
                for chunk_text in chunks:
                    metadata = doc.metadata.copy()
                    # Добавляем информацию о подразделении в метаданные (если файл в подпапке)
                    if subdivision:
                        metadata['subdivision'] = subdivision
                        metadata['subdivision_name'] = ALLOWED_SUBDIVISIONS[subdivision]
                    all_splits.append(Document(
                        page_content=chunk_text,
                        metadata=metadata
                    ))

        logger.info(f"[INGEST] Создано чанков: {len(all_splits)} из {len(doc_files)} файлов")
        
        if not all_splits:
            logger.error(f"[INGEST] Не удалось создать ни одного чанка")
            return False, "Не удалось создать ни одного чанка"

        # Удаляем старую коллекцию, если есть
        try:
            temp_store = Chroma(persist_directory=persist_directory, embedding_function=app_state.embedding_model)
            temp_store.delete_collection()
        except:
            pass

        # Создаём новую векторную БД
        vectorstore = Chroma.from_documents(
            documents=all_splits,
            embedding=app_state.embedding_model,
            persist_directory=persist_directory
        )
        # Не сохраняем ретривер здесь, он будет перезагружен глобально после всей индексации

        logger.info(f"[INGEST] Успешно проиндексировано: {len(all_splits)} чанков из {len(doc_files)} документов")
        return True, f"Проиндексировано {len(all_splits)} чанков из {len(doc_files)} документов"

    except Exception as e:
        logger.error(f"[INGEST] Ошибка индексации: {str(e)}", exc_info=True)
        return False, f"Ошибка индексации: {str(e)}"
    
def index_employee_examples():
    """Индексирует примеры аварий с сотрудниками в отдельную векторную БД."""
    if not os.path.exists(EMPLOYEE_EXAMPLES_CSV):
        logger.error(f"Файл примеров сотрудников не найден: {EMPLOYEE_EXAMPLES_CSV}")
        return "Файл не найден"

    # Словарь для группировки: ключ = (авария, подразделение) -> список сотрудников
    examples_dict = {}
    try:
        with open(EMPLOYEE_EXAMPLES_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                desc = row.get("пример аварии", "").strip()
                dept = row.get("подразделение", "").strip()
                employee = row.get("сотрудник", "").strip()
                if desc and dept and employee:
                    key = (desc, dept)
                    if key not in examples_dict:
                        examples_dict[key] = []
                    examples_dict[key].append(employee)

        documents = []
        for (desc, dept), employees in examples_dict.items():
            # Формируем текст для поиска
            employees_str = "; ".join(employees)
            text = f"Авария: {desc}\nПодразделение: {dept}\nЗадействованные сотрудники: {employees_str}"
            metadata = {"source": "employees_examples.csv", "description": desc, "department": dept}
            documents.append(Document(page_content=text, metadata=metadata))

        if not documents:
            logger.warning("Нет документов для индексации примеров сотрудников.")
            return "Нет данных"

        # Удаляем старую коллекцию, если есть
        try:
            temp_store = Chroma(persist_directory=PERSIST_DIRECTORY_EMPLOYEES_EXAMPLES, embedding_function=app_state.embedding_model)
            temp_store.delete_collection()
        except:
            pass

        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=app_state.embedding_model,
            persist_directory=PERSIST_DIRECTORY_EMPLOYEES_EXAMPLES
        )
        logger.info(f"Проиндексировано {len(documents)} примеров аварий с сотрудниками.")
        return f"Индексация завершена: {len(documents)} примеров"
    except Exception as e:
        logger.error(f"Ошибка индексации примеров сотрудников: {e}", exc_info=True)
        return f"Ошибка: {e}"

def index_subdivision_examples():
    logger.info("Начало индексации примеров подразделений")
    if not os.path.exists(SUBDIVISION_EXAMPLES_CSV):
        logger.error(f"Файл не найден: {SUBDIVISION_EXAMPLES_CSV}")
        return "Файл не найден"

    examples_dict = {}
    try:
        with open(SUBDIVISION_EXAMPLES_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            row_count = 0
            for row in reader:
                row_count += 1
                desc = row.get("авария", "").strip()
                sub = row.get("подразделение", "").strip()
                if desc and sub:
                    if desc not in examples_dict:
                        examples_dict[desc] = set()
                    examples_dict[desc].add(sub)
            logger.info(f"Прочитано строк: {row_count}, уникальных аварий: {len(examples_dict)}")
    except Exception as e:
        logger.error(f"Ошибка чтения CSV: {e}", exc_info=True)
        return f"Ошибка чтения: {e}"

    documents = []
    for desc, subdivisions in examples_dict.items():
        subdivisions_str = "; ".join(sorted(subdivisions))
        text = f"Авария: {desc}\nНеобходимые подразделения: {subdivisions_str}"
        metadata = {"source": "subdivisions_examples.csv", "description": desc}
        documents.append(Document(page_content=text, metadata=metadata))

    if not documents:
        logger.warning("Нет документов для индексации")
        return "Нет данных"

    # Удаляем старую коллекцию, если есть
    try:
        temp_store = Chroma(persist_directory=PERSIST_DIRECTORY_SUBDIVISIONS_EXAMPLES, embedding_function=app_state.embedding_model)
        temp_store.delete_collection()
    except:
        pass

    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=app_state.embedding_model,
        persist_directory=PERSIST_DIRECTORY_SUBDIVISIONS_EXAMPLES
    )
    logger.info(f"Проиндексировано {len(documents)} примеров подразделений.")
    return f"Индексация завершена: {len(documents)} примеров"

def index_technic_reference():
    """Добавляет справочник техники в существующую векторную БД."""
    
    if not os.path.exists(TECHNIC_REFERENCE_CSV):
        logger.error(f"Файл справочника техники не найден: {TECHNIC_REFERENCE_CSV}")
        return "Файл не найден"
    
    documents = []
    try:
        with open(TECHNIC_REFERENCE_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                name = row.get('название_техники', '').strip()
                dept = row.get('подразделение', '').strip()
                purpose = row.get('назначение', '').strip()
                if name and dept:
                    text = f"Техника: {name}\nПодразделение: {dept}\nНазначение: {purpose}"
                    metadata = {"source": "technic_reference.csv", "name": name, "department": dept}
                    documents.append(Document(page_content=text, metadata=metadata))
    except Exception as e:
        logger.error(f"Ошибка чтения справочника техники: {e}", exc_info=True)
        return f"Ошибка чтения: {e}"
    
    if not documents:
        logger.warning("Нет документов для индексации справочника техники.")
        return "Нет данных"
    
    # Добавляем к существующей коллекции или создаём новую
    try:
        vectorstore = Chroma(
            persist_directory=PERSIST_DIRECTORY_TECHNIC,
            embedding_function=app_state.embedding_model
        )
        vectorstore.add_documents(documents)
        logger.info(f"Добавлено {len(documents)} записей справочника техники к существующей БД.")
        return f"Добавлено: {len(documents)} записей"
    except:
        # Если коллекция не существует, создаём новую
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=app_state.embedding_model,
            persist_directory=PERSIST_DIRECTORY_TECHNIC
        )
        logger.info(f"Проиндексировано {len(documents)} записей справочника техники.")
        return f"Индексация завершена: {len(documents)} записей"

def index_employees_reference():
    """Добавляет справочник сотрудников в существующую векторную БД."""
    
    if not os.path.exists(EMPLOYEES_REFERENCE_CSV):
        logger.error(f"Файл справочника сотрудников не найден: {EMPLOYEES_REFERENCE_CSV}")
        return "Файл не найден"
    
    documents = []
    try:
        with open(EMPLOYEES_REFERENCE_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                position = row.get('должность', '').strip()
                dept = row.get('подразделение', '').strip()
                if position and dept:
                    text = f"Должность: {position}\nПодразделение: {dept}"
                    metadata = {"source": "employees_reference.csv", "position": position, "department": dept}
                    documents.append(Document(page_content=text, metadata=metadata))
    except Exception as e:
        logger.error(f"Ошибка чтения справочника сотрудников: {e}", exc_info=True)
        return f"Ошибка чтения: {e}"
    
    if not documents:
        logger.warning("Нет документов для индексации справочника сотрудников.")
        return "Нет данных"
    
    # Добавляем к существующей коллекции или создаём новую
    try:
        vectorstore = Chroma(
            persist_directory=PERSIST_DIRECTORY_EMPLOYEES,
            embedding_function=app_state.embedding_model
        )
        vectorstore.add_documents(documents)
        logger.info(f"Добавлено {len(documents)} записей справочника сотрудников к существующей БД.")
        return f"Добавлено: {len(documents)} записей"
    except:
        # Если коллекция не существует, создаём новую
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=app_state.embedding_model,
            persist_directory=PERSIST_DIRECTORY_EMPLOYEES
        )
        logger.info(f"Проиндексировано {len(documents)} записей справочника сотрудников.")
        return f"Индексация завершена: {len(documents)} записей"
    
    
def reindex_documents():
    """Переиндексация всех документов и перезагрузка ретриверов."""
    results = []
    logger.info("[ПЕРЕИНДЕКСАЦИЯ] Начало...")

    # Индексация для техники (с поддержкой подпапок по подразделениям)
    res1, msg1 = ingest_docs_for_type(DOCS_FOLDER_TECHNIC, PERSIST_DIRECTORY_TECHNIC, use_subfolders=True)
    results.append(("list_technic", res1, msg1))

    res2, msg2 = ingest_docs_for_type(DOCS_FOLDER_WORK_PLAN, PERSIST_DIRECTORY_WORK_PLAN)
    results.append(("work_plan", res2, msg2))

    res3, msg3 = ingest_docs_for_type(DOCS_FOLDER_ALL_DOCS, PERSIST_DIRECTORY_ALL_DOCS)
    results.append(("all_docs", res3, msg3))

    # Индексация для сотрудников (с поддержкой подпапок по подразделениям)
    res4, msg4 = ingest_docs_for_type(DOCS_FOLDER_EMPLOYEES, PERSIST_DIRECTORY_EMPLOYEES, use_subfolders=True)
    results.append(("employees", res4, msg4))

    # Индексация для подразделений (с поддержкой подпапок по подразделениям)
    res5, msg5 = ingest_docs_for_type(DOCS_FOLDER_SUBDIVISIONS, PERSIST_DIRECTORY_SUBDIVISIONS, use_subfolders=True)
    results.append(("subdivisions", res5, msg5))

    msg_examples = index_employee_examples()
    results.append(("employees_examples", True, msg_examples))

    msg_sub_examples = index_subdivision_examples()
    results.append(("subdivisions_examples", True, msg_sub_examples))

    # Индексация справочников
    msg_technic_ref = index_technic_reference()
    results.append(("technic_reference", True, msg_technic_ref))

    msg_employees_ref = index_employees_reference()
    results.append(("employees_reference", True, msg_employees_ref))

    # Перезагружаем ретриверы в глобальном состоянии
    app_state.reload_vectorstores()
    logger.info("[ПЕРЕИНДЕКСАЦИЯ] Завершена, ретриверы перезагружены.")

    return "\n".join([f"{name}: {status} - {message}" for name, status, message in results])