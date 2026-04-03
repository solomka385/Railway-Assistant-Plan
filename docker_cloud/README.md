# Docker конфигурация для RAG системы

Этот каталог содержит файлы для контейнеризации RAG системы с помощью Docker и Docker Compose.

## Требования

- Docker Desktop (Windows/Mac) или Docker Engine (Linux)
- Docker Compose (входит в Docker Desktop)
- Модель LLM (Vikhr Nemo 12B) должна быть доступна на хосте
- **Для GPU**: NVIDIA GPU с драйверами и NVIDIA Container Toolkit

## Структура файлов

```
docker/
├── Dockerfile          # Образ контейнера для RAG системы
├── docker-compose.yml  # Оркестрация сервисов
├── .dockerignore       # Исключения при сборке образа
├── .env.example        # Пример конфигурации переменных окружения
└── README.md           # Этот файл
```

## Настройка GPU (NVIDIA)

### Windows (WSL2)

1. Установите последние драйверы NVIDIA для вашей видеокарты
2. Установите WSL2: `wsl --install`
3. Установите Docker Desktop с поддержкой WSL2
4. В Docker Desktop перейдите в Settings → General → Enable "Use the WSL 2 based engine"
5. В Settings → Resources → WSL Integration включите интеграцию с вашим дистрибутивом

### Linux

1. Установите драйверы NVIDIA:
   ```bash
   sudo apt install nvidia-driver-535
   ```

2. Установите NVIDIA Container Toolkit:
   ```bash
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker
   ```

3. Проверьте доступность GPU:
   ```bash
   docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
   ```

## Быстрый старт

### 1. Подготовка конфигурации

Скопируйте пример файла конфигурации и отредактируйте его:

```bash
cp .env.example .env
```

Отредактируйте `.env` и укажите правильный путь к модели LLM:

```env
MODEL_HOST_PATH=E:/диплом/vikhr_nemo_12b
```

### 2. Сборка и запуск

Запуск только RAG системы (без локальной PostgreSQL):

```bash
docker-compose up -d
```

Запуск с локальной PostgreSQL:

```bash
docker-compose --profile with-postgres up -d
```

### 3. Проверка статуса

```bash
docker-compose ps
```

### 4. Просмотр логов

```bash
# Все сервисы
docker-compose logs -f

# Только RAG система
docker-compose logs -f rag-system
```

### 5. Остановка

```bash
docker-compose down
```

Для удаления volumes (включая данные Chroma DB):

```bash
docker-compose down -v
```

## Доступ к API

После запуска API будет доступен по адресу:

- **API endpoint**: `http://localhost:8000`
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Монтирование данных

### Модель LLM

Модель монтируется из директории на хосте в контейнер:

```
Хост: E:/диплом/vikhr_nemo_12b
Контейнер: /app/models/vikhr_nemo_12b
```

### Документы

Документы монтируются для возможности обновления без пересборки контейнера:

```
Хост: ../rag_system/docs
Контейнер: /app/docs
```

### Chroma DB

Векторные базы данных хранятся в Docker volumes:

- `chroma_technic` - БД техники
- `chroma_work_plan` - БД планов работ
- `chroma_all_docs` - БД всех документов
- `chroma_employees` - БД сотрудников
- `chroma_subdivisions` - БД подразделений
- `chroma_employees_examples` - Примеры сотрудников
- `chroma_subdivisions_examples` - Примеры подразделений

## Переменные окружения

Основные переменные окружения (см. `.env.example`):

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `PG_HOST` | Хост PostgreSQL | `postgres` |
| `PG_PORT` | Порт PostgreSQL | `5432` |
| `PG_DB` | Имя базы данных | `db1` |
| `PG_USER` | Пользователь БД | `test_cla` |
| `PG_PASSWORD` | Пароль БД | `12345678` |
| `PG_SSLMODE` | Режим SSL | `disable` |
| `PG_SSLROOTCERT` | Путь к SSL сертификату | (пусто) |
| `PG_MINCONN` | Мин. соединений в пуле | `1` |
| `PG_MAXCONN` | Макс. соединений в пуле | `10` |
| `MODEL_HOST_PATH` | Путь к модели на хосте | `E:/диплом/vikhr_nemo_12b` |
| `EMBEDDING_MODEL_NAME` | Модель эмбеддингов | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| `MAX_KEYWORDS_TO_EXTRACT` | Макс. ключевых слов | `7` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |

## Полезные команды

### Пересборка образа

```bash
docker-compose build --no-cache
```

### Вход в контейнер

```bash
docker-compose exec rag-system bash
```

### Перезапуск сервиса

```bash
docker-compose restart rag-system
```

### Просмотр ресурсов

```bash
docker stats rag-system
```

## Устранение проблем

### Проблема: Контейнер не запускается

1. Проверьте логи:
   ```bash
   docker-compose logs rag-system
   ```

2. Убедитесь, что путь к модели указан правильно в `.env`

3. Проверьте, что модель доступна на хосте

### Проблема: Ошибка доступа к PostgreSQL

1. Если используете внешнюю БД, проверьте настройки в `.env`
2. Если используете локальный контейнер PostgreSQL, запустите с профилем:
   ```bash
   docker-compose --profile with-postgres up -d
   ```

### Проблема: Медленная загрузка модели

Модель Vikhr Nemo 12B (~24GB) загружается при старте контейнера. Это может занять несколько минут в зависимости от производительности системы.

### Проблема: Недостаточно памяти

Убедитесь, что Docker имеет достаточно выделенной памяти (рекомендуется минимум 16GB, лучше 32GB+).

## Производительность

Для оптимальной производительности:

1. Используйте SSD для хранения модели
2. Выделите достаточно памяти Docker (минимум 16GB)
3. Используйте GPU (требует дополнительной настройки Docker с NVIDIA runtime)

## Безопасность

- Не коммитьте `.env` файл в репозиторий
- Используйте сильные пароли для PostgreSQL
- В продакшене используйте HTTPS для API
- Ограничьте доступ к API через firewall или VPN
