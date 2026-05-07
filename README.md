# 🚂 Railway Assistant Plan

Интеллектуальная система анализа железнодорожных аварий и чрезвычайных ситуаций с использованием RAG-технологии (Retrieval-Augmented Generation).

---

## 📋 Оглавление

- [О проекте](#о-проекте)
- [Архитектура](#архитектура)
- [Технологический стек](#технологический-стек)
- [Установка и запуск](#установка-и-запуск)
- [Развертывание RAG системы](#развертывание-rag-системы)
- [Развертывание сайта](#развертывание-сайта)
- [Как это работает](#как-это-работает)
- [API документация](#api-документация)
- [Структура проекта](#структура-проекта)
- [Разработка](#разработка)

---

## 🎯 О проекте

Система предназначена для оперативного анализа железнодорожных аварий и предоставления рекомендаций по ликвидации последствий. Она помогает определить:

- 🏢 **Необходимые подразделения** - какие службы должны быть задействованы
- 🚜 **Требуемую технику** - какое оборудование необходимо на месте происшествия
- 👥 **Ответственных сотрудников** - кто должен быть вызван
- 📋 **План работ** - последовательность действий по устранению последствий

### Основные возможности

- 💬 **Два режима работы**:
  - `chat` - простой диалог с историей сообщений
  - `plan` - полный анализ со структурированным ответом

- 📍 **Геолокация** - определение ближайших станций и ответственных лиц
- 📊 **Витрины данных** - интеграция с PostgreSQL для получения актуальной информации
- 🔄 **Потоковая генерация** - ответы генерируются в реальном времени
- 📚 **База знаний** - документы о технике, сотрудниках и подразделениях

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────┐
│                     Telegram Web App (tg/)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Frontend   │  │   Backend    │  │   Database   │      │
│  │  (HTML/JS)   │  │  (Express)   │  │ (PostgreSQL) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────┘
                            │
                            │ HTTP API
                            ▼
┌─────────────────────────────────────────────────────┐
│                    RAG System (rag_system/)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   FastAPI    │  │  LangChain   │  │  ChromaDB    │      │
│  │   Server     │  │   + LLM      │  │ (Vector DB)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────┘
```

---

## 🛠️ Технологический стек

### Telegram Web App (`tg/`)

| Компонент | Технология |
|-----------|------------|
| Backend | Node.js, Express.js |
| Frontend | HTML5, JavaScript (Vanilla) |
| Database | PostgreSQL |
| Cache | Redis |
| Session | express-session + connect-pg-simple |
| Auth | bcrypt |

### RAG System (`rag_system/`)

| Компонент | Технология |
|-----------|------------|
| API | FastAPI, Uvicorn |
| LLM | T-lite-it-2.1 8B (HuggingFace) |
| Embeddings | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| Vector DB | ChromaDB |
| RAG Framework | LangChain |
| Database | PostgreSQL (psycopg2) |
| Document Processing | python-docx, docx2txt |

---

## 🚀 Установка и запуск

### Требования

- **Node.js** >= 18.x
- **Python** >= 3.10
- **PostgreSQL** >= 15
- **Redis** (опционально)
- **Docker** (опционально)
- **GPU** с поддержкой CUDA (для LLM)

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd dip_kop
```

### 2. Настройка окружения

#### Telegram Web App

```bash
cd tg
npm install
cp .env.example .env
```

Отредактируйте `.env`:

```env
# PostgreSQL
PG_HOST=localhost
PG_PORT=
PG_DB=
PG_USER=
PG_PASSWORD=your_password

# RAG API
RAG_API_URL=http://localhost:8001

# Session
SESSION_SECRET=your_secret_key

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

#### RAG System

```bash
cd rag_system
pip install -r requirements.txt
```

Создайте файл `.env`:

```env
# PostgreSQL
PG_HOST=localhost
PG_PORT=5432
PG_DB=db1
PG_USER=test_cla
PG_PASSWORD=your_password

# Models
MODEL_PATH=/path/to/T-lite-it-2.1 8B
EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

### 3. Инициализация базы данных

```bash
# Примените миграции PostgreSQL
psql -U test_cla -d db1 -f tg/migrate_add_mode_column.sql
psql -U test_cla -d db1 -f tg/migrate_create_station_responsibles_view.sql
```

### 4. Индексация документов

```bash
cd rag_system
python scripts/rag/ingestion.py
```

### 5. Запуск

#### Локальный запуск

```bash
# Терминал 1: RAG System
cd rag_system
python scripts/api/api.py

# Терминал 2: Telegram Web App
cd tg
npm start
```

#### Запуск с Docker

```bash
cd docker
docker-compose up -d
```

### 6. Доступ к приложению

- **Telegram Web App**: http://localhost:3000
- **RAG API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs

---

## 🌐 Развертывание RAG системы

### Требования к серверу

- **ОС**: Linux (Ubuntu 20.04+ или CentOS 7+)
- **CPU**: 4+ ядер
- **RAM**: 16+ GB
- **GPU**: NVIDIA с поддержкой CUDA 11.8+ (рекомендуется 8+ GB VRAM)
- **Диск**: 50+ GB SSD
- **Python**: 3.10+
- **PostgreSQL**: 15+

### Пошаговая инструкция

#### 1. Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python и зависимостей
sudo apt install -y python3.10 python3.10-venv python3-pip git

# Установка PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Установка CUDA (для GPU)
# Следуйте инструкциям с https://developer.nvidia.com/cuda-downloads
```

#### 2. Настройка PostgreSQL

```bash
# Создание пользователя и базы данных
sudo -u postgres psql
```

```sql
CREATE USER rag_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE rag_db OWNER rag_user;
GRANT ALL PRIVILEGES ON DATABASE rag_db TO rag_user;
\q
```

#### 3. Развертывание RAG System

```bash
# Клонирование репозитория
cd /opt
git clone <repository-url> rag_system
cd rag_system

# Создание виртуального окружения
python3.10 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
cp .env_example .env
nano .env
```

Отредактируйте `.env`:

```env
# PostgreSQL
PG_HOST=localhost
PG_PORT=5432
PG_DB=rag_db
PG_USER=rag_user
PG_PASSWORD=your_secure_password

# Models
MODEL_PATH=/opt/models/T-lite-it-2.1 8B
EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# Директории для векторных БД
PERSIST_DIRECTORY_TECHNIC=chroma_db_technic
PERSIST_DIRECTORY_WORK_PLAN=chroma_db_work_plan
PERSIST_DIRECTORY_ALL_DOCS=chroma_db_all_docs
PERSIST_DIRECTORY_EMPLOYEES=chroma_db_employees
PERSIST_DIRECTORY_SUBDIVISIONS=chroma_db_subdivisions
```

#### 4. Загрузка модели

```bash
# Создание директории для моделей
mkdir -p /opt/models

# Загрузка модели Vikhr Nemo 12B
# Используйте huggingface-cli или wget для загрузки модели
```

#### 5. Индексация документов

```bash
# Применение миграций базы данных
psql -U rag_user -d rag_db -f database/init.sql

# Индексация документов
python scripts/rag/ingestion.py
```

#### 6. Настройка systemd сервиса

```bash
sudo nano /etc/systemd/system/rag-system.service
```

```ini
[Unit]
Description=RAG System API
After=network.target postgresql.service

[Service]
Type=simple
User=rag_user
WorkingDirectory=/opt/rag_system
Environment="PATH=/opt/rag_system/venv/bin"
ExecStart=/opt/rag_system/venv/bin/python scripts/api/api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Активация сервиса
sudo systemctl daemon-reload
sudo systemctl enable rag-system
sudo systemctl start rag-system

# Проверка статуса
sudo systemctl status rag-system
```

---

#### 7. Запуск RAG System

```bash
cd rag_system
python -m scripts.api.api
```

RAG API будет доступен по адресу: http://localhost:8001

API документация: http://localhost:8001/docs


## 🌐 Развертывание сайта (Telegram Web App)

### Требования к серверу

- **ОС**: Linux (Ubuntu 20.04+ или CentOS 7+)
- **CPU**: 2+ ядер
- **RAM**: 4+ GB
- **Диск**: 10+ GB SSD
- **Node.js**: 18+
- **PostgreSQL**: 15+

### Пошаговая инструкция

#### 1. Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Установка PostgreSQL (если не установлен)
sudo apt install -y postgresql postgresql-contrib
```

#### 2. Настройка PostgreSQL

```bash
# Создание пользователя и базы данных
sudo -u postgres psql
```

```sql
CREATE USER tg_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE tg_db OWNER tg_user;
GRANT ALL PRIVILEGES ON DATABASE tg_db TO tg_user;
\q
```

## 🌐 Развертывание сайта на Windows

### Требования

- **ОС**: Windows 10/11 или Windows Server 2019+
- **Node.js**: 18+
- **PostgreSQL**: 15+
- **RAM**: 4+ GB
- **Диск**: 10+ GB SSD

### Пошаговая инструкция

#### 1. Установка Node.js

Скачайте и установите Node.js с официального сайта: https://nodejs.org/

При установке обязательно отметьте галочку **"Add to PATH"**.

#### 2. Установка PostgreSQL

Скачайте и установите PostgreSQL с официального сайта: https://www.postgresql.org/download/windows/

При установке запомните пароль пользователя `postgres`.

#### 3. Настройка PostgreSQL

1. Откройте **pgAdmin 4** (устанавливается вместе с PostgreSQL)
2. Подключитесь к серверу (localhost, пользователь postgres)
3. Создайте базу данных и пользователя:

```sql
CREATE USER tg_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE tg_db OWNER tg_user;
GRANT ALL PRIVILEGES ON DATABASE tg_db TO tg_user;
```

#### 4. Клонирование репозитория

```bash
git clone <repository-url>
cd dip_kop\tg
```

#### 5. Установка зависимостей

```bash
npm install
```

#### 6. Настройка переменных окружения

Скопируйте файл `.env.example` в `.env`:

```bash
copy .env.example .env
```

Отредактируйте `.env`:

```env
# PostgreSQL
PG_HOST=localhost
PG_PORT=5432
PG_DB=tg_db
PG_USER=tg_user
PG_PASSWORD=your_secure_password

# RAG API
RAG_API_URL=http://rag-server:8001

# Session
SESSION_SECRET=your_very_secure_secret_key

# Redis (опционально)
REDIS_HOST=localhost
REDIS_PORT=6379
```

#### 7. Применение миграций базы данных

Откройте **pgAdmin 4** и выполните SQL-скрипты:

1. Откройте файл `migrate_add_mode_column.sql`
2. Нажмите **Execute** (F5)
3. Откройте файл `migrate_create_station_responsibles_view.sql`
4. Нажмите **Execute** (F5)

#### 8. Запуск приложения

```bash
npm start
```

Приложение будет доступно по адресу: http://localhost:3000


## ⚙️ Как это работает

### 1. Пользователь отправляет запрос

Пользователь описывает ситуацию через Telegram Web App:

> "Произошло столкновение поездов на станции Москва-Сортировочная. Какие подразделения и техника необходимы?"

### 2. Обработка запроса

```
┌─────────────┐
│   Frontend  │ → Отправляет запрос на backend
└─────────────┘
       │
       ▼
┌─────────────┐
│   Backend   │ → Проксирует запрос в RAG System
└─────────────┘
       │
       ▼
┌─────────────┐
│  RAG System │ → Обрабатывает запрос
└─────────────┘
```

### 3. RAG Pipeline

```
1. Извлечение ключевых слов
   ↓
2. Поиск в векторной базе данных (ChromaDB)
   ↓
3. Реранкинг релевантных документов
   ↓
4. Формирование контекста для LLM
   ↓
5. Генерация ответа (Vikhr Nemo 12B)
   ↓
6. Извлечение структурированных данных
   (подразделения, техника, сотрудники, план работ)
```

### 4. Ответ пользователю

```json
{
  "answer": "Необходимая техника:\n- Кран железнодорожный КДЭ-251\n- Автомобиль самосвал КамАЗ\n\nНеобходимые подразделения:\n- ВЧД-1 (Дистанция пути)\n- ВЧС-2 (Дистанция сигнализации)",
  "subdivisions": {
    "list": ["ВЧД-1 (Дистанция пути)", "ВЧС-2 (Дистанция сигнализации)"],
    "sources": ["Инструкция по ликвидации последствий аварий.docx"]
  },
  "technics": {
    "list": ["Кран железнодорожный КДЭ-251", "Автомобиль самосвал КамАЗ"],
    "sources": ["Номенклатура техники.pdf"]
  },
  "employees": {
    "list": ["Иванов И.И. (Мастер пути)", "Петров П.П. (Электромеханик)"],
    "sources": ["Штатное расписание.xlsx"]
  },
  "work_plan": {
    "plan": "1. Оценить повреждения путевого хозяйства\n2. Организовать восстановление контактной сети\n3. Провести расследование причин аварии",
    "sources": ["Регламент работ при авариях.docx"]
  }
}
```

---

## 📚 API документация

### Основные эндпоинты RAG System

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | `/ask` | Задать вопрос |
| GET | `/health` | Проверка статуса системы |
| POST | `/reindex` | Переиндексация документов |
| POST | `/marts-data` | Получение данных витрин |

### Пример запроса

```bash
curl -X 'POST' \
  'http://localhost:8001/ask' \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "Произошло столкновение поездов на станции Москва-Сортировочная. Какие подразделения и техника необходимы?",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "mode": "plan"
  }'
```

Подробная документация API доступна в [`документация/API_DESCRIPTION.md`](документация/API_DESCRIPTION.md)

---

## 📁 Структура проекта

```
dip_kop/
├── tg/                          # Telegram Web App
│   ├── app.js                   # Express приложение
│   ├── server.js                # Точка входа
│   ├── config/                  # Конфигурация
│   │   └── config.js          # Основная конфигурация приложения
│   ├── controllers/             # Контроллеры обработки запросов
│   │   ├── auth.js            # Контроллер аутентификации
│   │   ├── chat.js            # Контроллер чата
│   │   └── marts.js           # Контроллер витрин данных
│   ├── db/                      # База данных
│   │   └── db.js              # Подключение к PostgreSQL
│   ├── middleware/              # Middleware
│   │   ├── auth.js            # Проверка аутентификации
│   │   └── errorHandler.js    # Обработка ошибок
│   ├── public/                  # Frontend
│   │   ├── index.html           # Главная страница
│   │   ├── login.html           # Страница входа
│   │   └── js/                # JavaScript модули
│   │       ├── api.js          # API клиент
│   │       ├── auth.js         # Модуль аутентификации
│   │       ├── chat.js         # Модуль чата
│   │       ├── constants.js     # Константы приложения
│   │       ├── location.js      # Модуль геолокации
│   │       ├── marts.js        # Модуль витрин данных
│   │       ├── main.js         # Основной скрипт
│   │       ├── state.js        # Управление состоянием
│   │       └── ui.js           # UI компоненты
│   ├── routes/                  # Маршруты API
│   │   ├── auth.js            # Маршруты аутентификации
│   │   ├── chat.js            # Маршруты чата
│   │   └── marts.js           # Маршруты витрин данных
│   ├── services/                # Сервисы бизнес-логики
│   │   └── authService.js     # Сервис аутентификации
│   ├── package.json              # Зависимости Node.js
│   └── .env.example             # Пример переменных окружения
│
├── rag_system/                  # RAG System
│   ├── scripts/                 # Основной код системы
│   │   ├── api/               # API сервер
│   │   │   └── api.py       # FastAPI приложение с эндпоинтами
│   │   ├── config/            # Конфигурация
│   │   │   └── config.py    # Загрузка переменных окружения
│   │   ├── database/           # Работа с базой данных
│   │   │   ├── db.py        # Подключение и пул соединений PostgreSQL
│   │   │   └── marts_db.py  # Витрины данных (станции, техника, сотрудники)
│   │   ├── evaluation/         # Модули оценки качества
│   │   │   ├── evaluation_config.py  # Конфигурация оценки
│   │   │   ├── generate_accident_scenarios.py  # Генерация тестовых сценариев
│   │   │   ├── ragas_evaluation.py  # Оценка с RAGAS
│   │   │   └── test_data_generator.py  # Генератор тестовых данных
│   │   ├── rag/               # Основной RAG функционал
│   │   │   ├── app_state.py  # Управление состоянием системы
│   │   │   ├── async_generator.py  # Асинхронная генерация
│   │   │   ├── async_rag.py  # Асинхронный RAG пайплайн
│   │   │   ├── ingestion.py  # Загрузка документов в векторную БД
│   │   │   ├── prompts.py    # Промпты для LLM
│   │   │   ├── response_processing.py  # Обработка ответов модели
│   │   │   ├── retrieval.py  # Поиск документов
│   │   │   └── session.py    # Управление сессиями
│   │   ├── tests/             # Тесты
│   │   │   ├── test_app_state_references.py  # Тесты справочников
│   │   │   ├── test_keywords.py  # Тесты ключевых слов
│   │   │   ├── test_normalize.py  # Тесты нормализации
│   │   │   ├── test_redistribution.py  # Тесты перераспределения
│   │   │   ├── test_reference_loading.py  # Тесты загрузки справочников
│   │   │   ├── test_response_processing.py  # Тесты обработки ответов
│   │   │   ├── test_task_queue.py  # Тесты очереди задач
│   │   │   └── test_work_plan_fixes.py  # Тесты планов работ
│   │   └── utils/             # Утилиты
│   │       └── task_queue.py  # Очередь задач
│   ├── database/                # SQL скрипты базы данных
│   │   ├── alter_messages.sql  # Изменение таблицы сообщений
│   │   ├── create_rag_schema.sql  # Создание схемы RAG
│   │   ├── db_manager.py      # Менеджер базы данных
│   │   └── init.sql          # Инициализация базы данных
│   ├── docs/                   # Исходные документы
│   │   ├── list_technic/      # Документы о технике
│   │   │   ├── техника_подробное_описание.md
│   │   │   ├── БВС/          # Буксировочная вагонная служба
│   │   │   ├── ДГПС/         # Дистанция гашения и посадки поездов
│   │   │   ├── ДИ/           # Дистанция инфраструктуры
│   │   │   ├── ДИ ЦУСИ/      # Дистанция инфраструктуры ЦУСИ
│   │   │   ├── ДРП/          # Дистанция пути
│   │   │   ├── ДЦС/          # Дистанция сигнализации
│   │   │   ├── ДЦУП/         # Дистанция централизованного управления перевозками
│   │   │   └── МАБ/          # Машинно-автоматическая будка
│   │   ├── list_employee/      # Документы о сотрудниках
│   │   ├── list_subdivisions/ # Документы о подразделениях
│   │   ├── work_plan/         # План работ
│   │   └── all_docs/          # Все документы для индексации
│   ├── chroma_db_*/            # Векторные базы данных ChromaDB
│   │   ├── chroma_db_technic/          # База техники
│   │   ├── chroma_db_work_plan/         # База планов работ
│   │   ├── chroma_db_all_docs/          # База всех документов
│   │   ├── chroma_db_employees/         # База сотрудников
│   │   ├── chroma_db_subdivisions/      # База подразделений
│   │   ├── chroma_db_employees_examples/ # Примеры сотрудников
│   │   └── chroma_db_subdivisions_examples/ # Примеры подразделений
│   ├── evaluation_results/       # Результаты оценки
│   │   ├── evaluation_*.csv  # Детальные результаты
│   │   └── summary_*.json    # Сводные результаты
│   ├── test_data/              # Тестовые данные
│   │   └── accident_scenarios_*.json  # Сценарии аварий
│   ├── .env_example             # Пример переменных окружения
│   ├── keywords.json           # Ключевые слова для извлечения
│   ├── migrate_add_unique_constraint.sql  # Миграция базы данных
│   └── requirements.txt       # Зависимости Python
│
└── docker/                      # Docker конфигурация
    ├── docker-compose.yml       # Docker Compose для всех сервисов
    ├── Dockerfile               # Dockerfile для RAG System
    └── .env.example             # Пример переменных окружения

```

---

## 🔧 Разработка

### Добавление новых документов

1. Поместите документ в соответствующую папку `rag_system/docs/`
2. Запустите переиндексацию:

```bash
cd rag_system
python scripts/rag/ingestion.py
```

### Логирование

Логи RAG System доступны в:
- Консоль (при локальном запуске)
- Docker logs: `docker logs rag-system`

---

## 📝 Лицензия

MIT License

---

## 👨‍💻 Авторы

Разработано для Московской железной дороги

