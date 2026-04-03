# app_state.py
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, BitsAndBytesConfig
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
import logging
import os
import csv 
from config import (
    MODEL_PATH, EMBEDDING_MODEL_NAME,
    PERSIST_DIRECTORY_TECHNIC,
    PERSIST_DIRECTORY_WORK_PLAN, PERSIST_DIRECTORY_ALL_DOCS,
    PERSIST_DIRECTORY_EMPLOYEES,  # добавлено
    PERSIST_DIRECTORY_SUBDIVISIONS,  # добавлено
    CSV_FILE_PATH,PERSIST_DIRECTORY_EMPLOYEES_EXAMPLES,
    PERSIST_DIRECTORY_SUBDIVISIONS_EXAMPLES,
    TECHNIC_REFERENCE_CSV, EMPLOYEES_REFERENCE_CSV
)

logger = logging.getLogger(__name__)

# Глобальные переменные состояния
tokenizer = None
model = None
pipe = None
embedding_model = None

vectorstore_technic = None
retriever_technic = None
vectorstore_work_plan = None
retriever_work_plan = None
vectorstore_all_docs = None
retriever_all_docs = None
# Новые переменные для сотрудников
vectorstore_employees = None
retriever_employees = None
vectorstore_employees_examples = None
retriever_employees_examples = None
vectorstore_subdivisions_examples = None
retriever_subdivisions_examples = None
# Переменные для подразделений
vectorstore_subdivisions = None
retriever_subdivisions = None

accidents_examples = []
employees_examples = []
technic_reference = []
employees_reference = []

def load_reference_csv(csv_file_path: str) -> list:
    """Загружает справочник из CSV-файла (разделитель ;)."""
    reference = []
    try:
        logger.info(f"[CSV] Попытка загрузить справочник: {csv_file_path}")
        abs_path = os.path.abspath(csv_file_path)
        if os.path.exists(abs_path):
            with open(abs_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                for row in reader:
                    reference.append(dict(row))
            logger.info(f"[CSV] Загружено {len(reference)} записей из справочника.")
        else:
            logger.error(f"[CSV] Файл {abs_path} не найден")
    except Exception as e:
        logger.error(f"[CSV] Ошибка загрузки справочника: {e}", exc_info=True)
    return reference

def init_system():
    """Инициализирует все компоненты RAG-системы."""
    global tokenizer, model, pipe, embedding_model
    global vectorstore_technic, retriever_technic
    global vectorstore_work_plan, retriever_work_plan
    global vectorstore_all_docs, retriever_all_docs
    global vectorstore_employees, retriever_employees  # добавлено
    global vectorstore_subdivisions, retriever_subdivisions  # добавлено
    global accidents_examples
    global employees_examples
    global technic_reference
    global employees_reference

    try:
        # Инициализация пула соединений PostgreSQL
        from db import init_pg_pool
        if not init_pg_pool():
            logger.error("[ИНИЦИАЛИЗАЦИЯ] Не удалось инициализировать пул соединений PostgreSQL")
            return False
        
        logger.info("[ИНИЦИАЛИЗАЦИЯ] Пул соединений PostgreSQL инициализирован")
        
        logger.info("[ИНИЦИАЛИЗАЦИЯ] Загрузка токенизатора...")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

        logger.info("[ИНИЦИАЛИЗАЦИЯ] Настройка квантизации...")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )

        logger.info("[ИНИЦИАЛИЗАЦИЯ] Загрузка модели...")
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            device_map="auto",
            quantization_config=bnb_config,
        )

        logger.info("[ИНИЦИАЛИЗАЦИЯ] Создание пайплайна...")
        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=4096,
            temperature=0.2,
            return_full_text=False,
            pad_token_id=tokenizer.eos_token_id,
            batch_size=1,
            truncation=True,
            do_sample=True,
            top_k=75,
            top_p=0.95,
            repetition_penalty=1.1
        )

        logger.info("[ИНИЦИАЛИЗАЦИЯ] Загрузка эмбеддинг-модели...")
        embedding_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

        # Загрузка векторных БД
        reload_vectorstores()

        # Загрузка примеров аварий из CSV
        from ingestion import load_accidents_examples
        accidents_examples = load_accidents_examples(CSV_FILE_PATH)

        logger.info(f"[ИНИЦИАЛИЗАЦИЯ] Загружено {len(accidents_examples)} примеров аварий.")

        # Загрузка справочников
        technic_reference = load_reference_csv(TECHNIC_REFERENCE_CSV)
        employees_reference = load_reference_csv(EMPLOYEES_REFERENCE_CSV)

        logger.info(f"[ИНИЦИАЛИЗАЦИЯ] Загружено {len(technic_reference)} записей в справочнике техники.")
        logger.info(f"[ИНИЦИАЛИЗАЦИЯ] Загружено {len(employees_reference)} записей в справочнике сотрудников.")

        logger.info("[ИНИЦИАЛИЗАЦИЯ] Система успешно инициализирована.")
        return True

    except Exception as e:
        logger.error(f"[ИНИЦИАЛИЗАЦИЯ] Ошибка: {e}", exc_info=True)
        return False


def reload_vectorstores():
    """Перезагружает ретриверы из существующих директорий Chroma."""
    global vectorstore_technic, retriever_technic
    global vectorstore_work_plan, retriever_work_plan
    global vectorstore_all_docs, retriever_all_docs
    global vectorstore_employees, retriever_employees  # добавлено
    global vectorstore_subdivisions, retriever_subdivisions  # добавлено
    global vectorstore_employees_examples, retriever_employees_examples
    global vectorstore_subdivisions_examples, retriever_subdivisions_examples

    if os.path.exists(PERSIST_DIRECTORY_TECHNIC):
        vectorstore_technic = Chroma(persist_directory=PERSIST_DIRECTORY_TECHNIC, embedding_function=embedding_model)
        retriever_technic = vectorstore_technic.as_retriever(search_kwargs={"k": 15})
        logger.info("[RELOAD] Загружена БД техники.")
    else:
        logger.warning(f"[RELOAD] Папка {PERSIST_DIRECTORY_TECHNIC} не найдена.")

    if os.path.exists(PERSIST_DIRECTORY_WORK_PLAN):
        vectorstore_work_plan = Chroma(persist_directory=PERSIST_DIRECTORY_WORK_PLAN, embedding_function=embedding_model)
        retriever_work_plan = vectorstore_work_plan.as_retriever(search_kwargs={"k": 7})
        logger.info("[RELOAD] Загружена БД планов работ.")
    else:
        logger.warning(f"[RELOAD] Папка {PERSIST_DIRECTORY_WORK_PLAN} не найдена.")

    if os.path.exists(PERSIST_DIRECTORY_ALL_DOCS):
        vectorstore_all_docs = Chroma(persist_directory=PERSIST_DIRECTORY_ALL_DOCS, embedding_function=embedding_model)
        retriever_all_docs = vectorstore_all_docs.as_retriever(search_kwargs={"k": 7})
        logger.info("[RELOAD] Загружена общая БД документов.")
    else:
        logger.warning(f"[RELOAD] Папка {PERSIST_DIRECTORY_ALL_DOCS} не найдена.")

    # Загрузка БД сотрудников
    if os.path.exists(PERSIST_DIRECTORY_EMPLOYEES):
        vectorstore_employees = Chroma(persist_directory=PERSIST_DIRECTORY_EMPLOYEES, embedding_function=embedding_model)
        retriever_employees = vectorstore_employees.as_retriever(search_kwargs={"k": 15})
        logger.info("[RELOAD] Загружена БД сотрудников.")
    else:
        logger.warning(f"[RELOAD] Папка {PERSIST_DIRECTORY_EMPLOYEES} не найдена.")
    
    if os.path.exists(PERSIST_DIRECTORY_EMPLOYEES_EXAMPLES):
        vectorstore_employees_examples = Chroma(persist_directory=PERSIST_DIRECTORY_EMPLOYEES_EXAMPLES, embedding_function=embedding_model)
        retriever_employees_examples = vectorstore_employees_examples.as_retriever(search_kwargs={"k": 5})  # число примеров, которое будем подтягивать
        logger.info("[RELOAD] Загружена БД примеров сотрудников.")
    else:
        logger.warning(f"Папка {PERSIST_DIRECTORY_EMPLOYEES_EXAMPLES} не найдена.")

    if os.path.exists(PERSIST_DIRECTORY_SUBDIVISIONS_EXAMPLES):
        vectorstore_subdivisions_examples = Chroma(persist_directory=PERSIST_DIRECTORY_SUBDIVISIONS_EXAMPLES, embedding_function=embedding_model)
        retriever_subdivisions_examples = vectorstore_subdivisions_examples.as_retriever(search_kwargs={"k": 5})
        logger.info("[RELOAD] Загружена БД примеров подразделений.")
    else:
        logger.warning(f"Папка {PERSIST_DIRECTORY_SUBDIVISIONS_EXAMPLES} не найдена.")

    # Загрузка БД подразделений
    if os.path.exists(PERSIST_DIRECTORY_SUBDIVISIONS):
        vectorstore_subdivisions = Chroma(persist_directory=PERSIST_DIRECTORY_SUBDIVISIONS, embedding_function=embedding_model)
        retriever_subdivisions = vectorstore_subdivisions.as_retriever(search_kwargs={"k": 10})
        logger.info("[RELOAD] Загружена БД подразделений.")
    else:
        logger.warning(f"Папка {PERSIST_DIRECTORY_SUBDIVISIONS} не найдена.")

def batch_generate(texts):
    """
    Генерирует ответы для батча текстов с использованием глобального пайплайна.
    """
    global pipe, tokenizer
    if not texts or not isinstance(texts, list) or len(texts) == 0:
        return [""]

    try:
        results = pipe(
            texts,
            max_new_tokens=4096,
            temperature=0.2,
            return_full_text=False,
            pad_token_id=tokenizer.eos_token_id,
            batch_size=1,
            truncation=True,
            do_sample=True,
            top_k=75,
            top_p=0.95,
            repetition_penalty=1.1
        )

        outputs = []
        if results and isinstance(results, list):
            for result in results:
                if isinstance(result, list) and len(result) > 0:
                    generated_text = result[0].get('generated_text', '').strip()
                    if generated_text:
                        import re
                        cleaned_text = re.sub(r'<\|im_start\|>.*?<\|im_end\|>', '', generated_text, flags=re.DOTALL)
                        outputs.append(cleaned_text.strip())
                    else:
                        outputs.append("")
                else:
                    outputs.append("")
        else:
            outputs.append("")

        return outputs

    except Exception as e:
        logger.error(f"[BATCH_GENERATE] Ошибка: {e}", exc_info=True)
        return [""]


def get_system_status():
    return {
        "model_loaded": model is not None,
        "vector_db_ready": vectorstore_subdivisions is not None and vectorstore_technic is not None and vectorstore_work_plan is not None,
        "vector_db_all_docs_ready": vectorstore_all_docs is not None,
        "vector_db_employees_ready": vectorstore_employees is not None,
        "vector_db_subdivisions_ready": vectorstore_subdivisions is not None,
        "gpu_available": torch.cuda.is_available() if hasattr(torch, 'cuda') else False,
        "examples_loaded": len(accidents_examples) > 0,
        "technic_reference_loaded": len(technic_reference) > 0,
        "employees_reference_loaded": len(employees_reference) > 0
    }