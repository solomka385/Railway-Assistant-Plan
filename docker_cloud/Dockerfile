# Dockerfile для RAG системы на ВМ с GPU
FROM python:3.11-slim

# Установка минимальных системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка переменных окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Рабочая директория
WORKDIR /app

# Копирование requirements для Docker
COPY dip_kop/docker_cloud/requirements-docker.txt /app/requirements.txt

# Установка Python зависимостей (с индексом PyTorch для CUDA)
RUN pip install --upgrade pip && \
    pip install torch==2.5.1 torchaudio==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121 && \
    pip install -r /app/requirements.txt

# Копирование файлов RAG системы (из rag_system)
COPY dip_kop/rag_system/*.py /app/
COPY dip_kop/rag_system/*.json /app/
COPY dip_kop/rag_system/*.sql /app/

# Создание директорий для данных и docs (для монтирования)
RUN mkdir -p /app/chroma_db_technic \
    /app/chroma_db_work_plan \
    /app/chroma_db_all_docs \
    /app/chroma_db_employees \
    /app/chroma_db_subdivisions \
    /app/chroma_db_employees_examples \
    /app/chroma_db_subdivisions_examples \
    /app/logs \
    /app/docs \
    /app/models \
    /app/database

# Открытие порта для API
EXPOSE 8000

# Команда запуска
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
