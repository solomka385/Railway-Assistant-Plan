# 🚂 Railway Assistant Plan

Интеллектуальная система анализа железнодорожных аварий и чрезвычайных ситуаций с использованием RAG-технологии (Retrieval-Augmented Generation).

---

## 📋 Оглавление

- [О проекте](#о-проекте)
- [Архитектура](#архитектура)
- [Технологический стек](#технологический-стек)
- [Установка и запуск](#установка-и-запуск)
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
  - `plan` - полный анализ с структурированным ответом

- 📍 **Геолокация** - определение ближайших станций и ответственных лиц
- 📊 **Витрины данных** - интеграция с PostgreSQL для получения актуальной информации
- 🔄 **Потоковая генерация** - ответы генерируются в реальном времени
- 📚 **База знаний** - документы о технике, сотрудниках и подразделениях

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                     Telegram Web App (tg/)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Frontend   │  │   Backend    │  │   Database   │      │
│  │  (HTML/JS)   │  │  (Express)   │  │ (PostgreSQL) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP API
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAG System (rag_system/)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   FastAPI    │  │  LangChain   │  │  ChromaDB    │      │
│  │   Server     │  │   + LLM      │  │ (Vector DB)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
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
| LLM | Vikhr Nemo 12B (HuggingFace) |
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

# Redis (опционально)
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
MODEL_PATH=/path/to/vikhr_nemo_12b
EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# API Keys (опционально)
COHERE_API_KEY=your_key
HUGGINGFACE_API_KEY=your_key
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
python ingestion.py
```

### 5. Запуск

#### Локальный запуск

```bash
# Терминал 1: RAG System
cd rag_system
python api.py

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
│   ├── controllers/             # Контроллеры
│   ├── db/                      # База данных
│   ├── middleware/              # Middleware
│   ├── public/                  # Frontend
│   │   ├── index.html           # Главная страница
│   │   ├── login.html           # Страница входа
│   │   └── js/                  # JavaScript модули
│   ├── routes/                  # Маршруты API
│   └── services/                # Сервисы
│
├── rag_system/                  # RAG System
│   ├── api.py                   # FastAPI приложение
│   ├── config.py                # Конфигурация
│   ├── ingestion.py             # Загрузка документов
│   ├── retrieval.py             # Поиск документов
│   ├── session.py               # Управление сессиями
│   ├── response_processing.py   # Обработка ответов
│   ├── marts_db.py              # Витрины данных
│   ├── prompts.py               # Промпты для LLM
│   ├── docs/                    # Исходные документы
│   │   ├── list_technic/        # Документы о технике
│   │   ├── list_employee/       # Документы о сотрудниках
│   │   ├── list_subdivisions/   # Документы о подразделениях
│   │   └── work_plan/           # План работ
│   ├── chroma_db_*/             # Векторные базы данных
│   └── requirements.txt         # Зависимости Python
│
├── docker/                      # Docker конфигурация
│   ├── docker-compose.yml       # Docker Compose
│   ├── Dockerfile               # Dockerfile для RAG System
│   └── .env.example             # Пример переменных окружения
│
├── документация/               # Документация проекта
│   ├── README.md                # Описание файлов tg
│   ├── README_rag.md            # Описание файлов rag_system
│   ├── API_DESCRIPTION.md      # Описание API
│   ├── database_schema.md      # Схема БД
│   └── VM_DEPLOYMENT.md         # Инструкция по развертыванию
│
└── README.md                    # Этот файл
```

---

## 🔧 Разработка

### Добавление новых документов

1. Поместите документ в соответствующую папку `rag_system/docs/`
2. Запустите переиндексацию:

```bash
cd rag_system
python ingestion.py
```

### Тестирование

```bash
# Тесты RAG System
cd rag_system
python -m pytest tests/

# Тесты Telegram Web App
cd tg
npm test
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

---

## 🤝 Поддержка

Для вопросов и предложений создайте issue в репозитории.
