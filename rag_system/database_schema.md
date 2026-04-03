# Схема базы данных RAG системы

## Обзор

База данных `rag_app` содержит таблицы для хранения информации о железнодорожной инфраструктуре, сотрудниках, технике и связях между станциями. Эти данные используются RAG системой для дополнения ответов реальными контактными данными и информацией о ближайших станциях.

## Порядок выполнения DAGов

1. **railway_marts_rag_app_final** - базовый DAG для создания основных таблиц
2. **railway_graph_rag_app** - создание графа ЖД дорог
3. **station_responsibles_rag_app** - загрузка сотрудников и ответственных

## Таблицы

### 1. stations
Справочник железнодорожных станций с координатами.

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL | Первичный ключ |
| name | VARCHAR(200) | Название станции (уникальное) |
| latitude | DOUBLE PRECISION | Широта |
| longitude | DOUBLE PRECISION | Долгота |

**Использование в RAG:**
- Поиск ближайших станций по координатам пользователя
- Определение местоположения для ответственных сотрудников

### 2. subdivisions
Справочник подразделений.

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL | Первичный ключ |
| code | VARCHAR(20) | Код подразделения (уникальный) |
| full_name | VARCHAR(500) | Полное название |

**Использование в RAG:**
- Фильтрация ответов по подразделениям
- Определение компетенций для разных типов запросов

### 3. station_subdivisions
Связь между станциями и подразделениями.

| Поле | Тип | Описание |
|------|-----|----------|
| station_id | INTEGER | ID станции (FK) |
| subdivision_id | INTEGER | ID подразделения (FK) |

**Использование в RAG:**
- Определение, какие подразделения находятся на конкретной станции

### 4. equipment_items
Справочник техники.

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL | Первичный ключ |
| name | VARCHAR(500) | Название техники (уникальное) |
| subdivision_id | INTEGER | ID подразделения (FK, nullable) |

**Использование в RAG:**
- Поиск доступной техники на станциях
- Формирование списка ресурсов для аварийных ситуаций

### 5. base_equipment
Базовая техника, доступная на всех станциях.

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL | Первичный ключ |
| name | VARCHAR(500) | Название (уникальное) |

**Использование в RAG:**
- Минимальный набор оборудования на любой станции

### 6. positions
Должности сотрудников.

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL | Первичный ключ |
| name | VARCHAR(500) | Название должности |
| subdivision_id | INTEGER | ID подразделения (FK) |

**Использование в RAG:**
- Определение ролей и компетенций сотрудников

### 7. equipment_mart
Витрина техники по станциям (обновляется ежедневно).

| Поле | Тип | Описание |
|------|-----|----------|
| station_name | VARCHAR(200) | Название станции |
| station_lat | DOUBLE PRECISION | Широта станции |
| station_lon | DOUBLE PRECISION | Долгота станции |
| subdivision_code | VARCHAR(20) | Код подразделения |
| equipment_name | VARCHAR(500) | Название техники |
| quantity | INTEGER | Количество |
| updated_at | DATE | Дата обновления |

**Использование в RAG:**
- Быстрый поиск техники по координатам
- Определение доступных ресурсов в радиусе от пользователя

### 8. staff_mart
Витрина сотрудников по станциям (обновляется ежедневно).

| Поле | Тип | Описание |
|------|-----|----------|
| station_name | VARCHAR(200) | Название станции |
| station_lat | DOUBLE PRECISION | Широта станции |
| station_lon | DOUBLE PRECISION | Долгота станции |
| subdivision_code | VARCHAR(20) | Код подразделения |
| position_name | VARCHAR(500) | Название должности |
| quantity | INTEGER | Количество |
| updated_at | DATE | Дата обновления |

**Использование в RAG:**
- Быстрый поиск сотрудников по координатам
- Определение доступного персонала в радиусе от пользователя

### 9. employees
Справочник сотрудников с контактными данными.

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL | Первичный ключ |
| full_name | VARCHAR(200) | ФИО сотрудника |
| phone_number | VARCHAR(20) | Номер телефона |
| position_id | INTEGER | ID должности (FK, nullable) |
| subdivision_id | INTEGER | ID подразделения (FK, nullable) |

**Использование в RAG:**
- Получение контактных данных ответственных
- Формирование списка контактов для ответа

### 10. station_responsibles
Ответственные сотрудники на станциях.

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL | Первичный ключ |
| station_id | INTEGER | ID станции (FK) |
| subdivision_id | INTEGER | ID подразделения (FK) |
| employee_id | INTEGER | ID сотрудника (FK) |
| phone_number | VARCHAR(20) | Номер телефона |
| full_name | VARCHAR(200) | ФИО |
| created_at | TIMESTAMP | Дата создания |
| updated_at | TIMESTAMP | Дата обновления |

**Использование в RAG:**
- Поиск ответственных по станции и подразделению
- Формирование блока контактов в ответе

### 11. railway_lines
ЖД линии и маршруты.

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL | Первичный ключ |
| name | VARCHAR(200) | Название линии (уникальное) |
| description | TEXT | Описание |
| line_type | VARCHAR(50) | Тип линии (радиальная, кольцевая, диагональная) |

**Использование в RAG:**
- Определение маршрутов между станциями
- Поиск ближайших станций по ЖД сети

### 12. station_connections
Связи между станциями (рёбра графа).

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL | Первичный ключ |
| from_station_id | INTEGER | ID станции отправления (FK) |
| to_station_id | INTEGER | ID станции назначения (FK) |
| distance_km | DOUBLE PRECISION | Расстояние в км |
| direction | VARCHAR(50) | Направление |
| line_name | VARCHAR(200) | Название линии |

**Использование в RAG:**
- Графовый поиск ближайших станций
- Определение маршрутов и расстояний

## Представления (Views)

### station_responsibles_view
Полная информация об ответственных на станциях с координатами.

```sql
SELECT 
    sr.id,
    s.name AS station_name,
    s.latitude AS station_lat,
    s.longitude AS station_lon,
    sub.code AS subdivision_code,
    sub.full_name AS subdivision_full_name,
    p.name AS position_name,
    sr.full_name AS employee_full_name,
    sr.phone_number,
    sr.created_at,
    sr.updated_at
FROM rag_app.station_responsibles sr
JOIN rag_app.stations s ON sr.station_id = s.id
JOIN rag_app.subdivisions sub ON sr.subdivision_id = sub.id
JOIN rag_app.employees e ON sr.employee_id = e.id
LEFT JOIN rag_app.positions p ON e.position_id = p.id
```

### station_graph_view
Представление для работы с графом ЖД дорог.

```sql
SELECT 
    sc.id,
    s1.name AS from_station_name,
    s1.latitude AS from_lat,
    s1.longitude AS from_lon,
    s2.name AS to_station_name,
    s2.latitude AS to_lat,
    s2.longitude AS to_lon,
    sc.distance_km,
    sc.direction,
    sc.line_name,
    rl.line_type
FROM rag_app.station_connections sc
JOIN rag_app.stations s1 ON sc.from_station_id = s1.id
JOIN rag_app.stations s2 ON sc.to_station_id = s2.id
LEFT JOIN rag_app.railway_lines rl ON sc.line_name = rl.name
```

## Индексы

Для оптимизации поиска созданы следующие индексы:

- `idx_station_responsibles_station` - поиск по станции
- `idx_station_responsibles_subdivision` - поиск по подразделению
- `idx_employees_subdivision` - поиск сотрудников по подразделению
- `idx_employees_position` - поиск сотрудников по должности
- `idx_employees_full_name` - поиск по ФИО
- `idx_station_connections_from` - поиск связей от станции
- `idx_station_connections_to` - поиск связей к станции
- `idx_station_connections_distance` - поиск по расстоянию
- `idx_station_connections_line` - поиск по линии

## Использование в RAG системе

### Поток данных

1. **LLM анализирует запрос пользователя** и определяет:
   - Какие подразделения нужны
   - Какая техника требуется
   - Какие сотрудники нужны
   - Координаты пользователя (если есть)

2. **Поиск в базе данных:**
   - По координатам находятся ближайшие станции (через граф ЖД дорог)
   - По станциям и подразделениям находятся ответственные
   - По станциям и подразделениям находится техника
   - По станциям и подразделениям находятся сотрудники

3. **Формирование ответа:**
   - LLM генерирует основной ответ
   - В конец ответа добавляются блоки с реальными данными из БД:
     - Где взять технику
     - Контакты ответственных
     - Список сотрудников

### Пример запроса к БД для поиска ответственных

```python
def get_responsibles_by_coordinates(lat, lon, radius_km=10.0):
    """Получает ответственных в радиусе от координат."""
    # Используем граф ЖД дорог для поиска ближайших станций
    # Затем получаем ответственных для этих станций
    pass
```

### Пример запроса к БД для поиска техники

```python
def get_equipment_by_coordinates(lat, lon, radius_km=10.0):
    """Получает технику в радиусе от координат."""
    # Используем equipment_mart для быстрого поиска
    pass
```

## Миграции

Миграции находятся в папке `migrations/`:

1. `add_geolocation_to_messages.sql` - добавление геолокации к сообщениям
2. `add_station_responsibles.sql` - таблицы сотрудников и ответственных
3. `add_railway_graph.sql` - таблицы графа ЖД дорог

## DAGи

DAGи находятся в папке `dags/`:

1. `equipment_staff_mart.py` - базовый DAG для создания основных таблиц и витрин
2. `railway_graph.py` - создание графа ЖД дорог
3. `station_responsibles.py` - загрузка сотрудников и ответственных
4. `test_db.py` - тест подключения к БД
