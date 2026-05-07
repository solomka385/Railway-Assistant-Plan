-- ============================================
-- Схема базы данных RAG системы
-- Все таблицы создаются в схеме rag_app
-- ============================================

-- Создание схемы (если не существует)
CREATE SCHEMA IF NOT EXISTS rag_app;

-- ============================================
-- Таблица: stations
-- Справочник станций
-- ============================================
CREATE TABLE rag_app.stations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) UNIQUE NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);

-- Комментарии к таблице и полям
COMMENT ON TABLE rag_app.stations IS 'Справочник станций';
COMMENT ON COLUMN rag_app.stations.id IS 'Первичный ключ';
COMMENT ON COLUMN rag_app.stations.name IS 'Название станции';
COMMENT ON COLUMN rag_app.stations.latitude IS 'Широта (WGS84)';
COMMENT ON COLUMN rag_app.stations.longitude IS 'Долгота (WGS84)';

-- ============================================
-- Таблица: subdivisions
-- Справочник подразделений
-- ============================================
CREATE TABLE rag_app.subdivisions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    full_name VARCHAR(500)
);

-- Комментарии к таблице и полям
COMMENT ON TABLE rag_app.subdivisions IS 'Справочник подразделений';
COMMENT ON COLUMN rag_app.subdivisions.id IS 'Первичный ключ';
COMMENT ON COLUMN rag_app.subdivisions.code IS 'Код подразделения (например, "ДАВС")';
COMMENT ON COLUMN rag_app.subdivisions.full_name IS 'Полное название подразделения';

-- ============================================
-- Таблица: station_subdivisions
-- Связь многие-ко-многим между станциями и подразделениями
-- ============================================
CREATE TABLE rag_app.station_subdivisions (
    station_id INTEGER NOT NULL,
    subdivision_id INTEGER NOT NULL,
    PRIMARY KEY (station_id, subdivision_id),
    CONSTRAINT fk_station_subdivisions_station 
        FOREIGN KEY (station_id) 
        REFERENCES rag_app.stations(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_station_subdivisions_subdivision 
        FOREIGN KEY (subdivision_id) 
        REFERENCES rag_app.subdivisions(id) 
        ON DELETE CASCADE
);

-- Комментарии к таблице и полям
COMMENT ON TABLE rag_app.station_subdivisions IS 'Связь многие-ко-многим между станциями и подразделениями';
COMMENT ON COLUMN rag_app.station_subdivisions.station_id IS 'Внешний ключ к stations(id)';
COMMENT ON COLUMN rag_app.station_subdivisions.subdivision_id IS 'Внешний ключ к subdivisions(id)';

-- ============================================
-- Таблица: equipment_items
-- Справочник всей специализированной техники с привязкой к подразделению
-- ============================================
CREATE TABLE rag_app.equipment_items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) UNIQUE NOT NULL,
    subdivision_id INTEGER,
    CONSTRAINT fk_equipment_items_subdivision 
        FOREIGN KEY (subdivision_id) 
        REFERENCES rag_app.subdivisions(id) 
        ON DELETE SET NULL
);

-- Комментарии к таблице и полям
COMMENT ON TABLE rag_app.equipment_items IS 'Справочник всей специализированной техники';
COMMENT ON COLUMN rag_app.equipment_items.id IS 'Первичный ключ';
COMMENT ON COLUMN rag_app.equipment_items.name IS 'Название техники';
COMMENT ON COLUMN rag_app.equipment_items.subdivision_id IS 'Внешний ключ к subdivisions(id) (может быть NULL, если техника универсальна)';

-- ============================================
-- Таблица: base_equipment
-- Базовая техника, которая есть у каждой станции
-- ============================================
CREATE TABLE rag_app.base_equipment (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) UNIQUE NOT NULL
);

-- Комментарии к таблице и полям
COMMENT ON TABLE rag_app.base_equipment IS 'Базовая техника, которая есть у каждой станции (не привязана к подразделению)';
COMMENT ON COLUMN rag_app.base_equipment.id IS 'Первичный ключ';
COMMENT ON COLUMN rag_app.base_equipment.name IS 'Название (например, "Рация портативная")';

-- ============================================
-- Таблица: positions
-- Справочник должностей с привязкой к подразделению
-- ============================================
CREATE TABLE rag_app.positions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    subdivision_id INTEGER NOT NULL,
    CONSTRAINT uq_positions_name_subdivision UNIQUE (name, subdivision_id),
    CONSTRAINT fk_positions_subdivision 
        FOREIGN KEY (subdivision_id) 
        REFERENCES rag_app.subdivisions(id) 
        ON DELETE CASCADE
);

-- Комментарии к таблице и полям
COMMENT ON TABLE rag_app.positions IS 'Справочник должностей с привязкой к подразделению';
COMMENT ON COLUMN rag_app.positions.id IS 'Первичный ключ';
COMMENT ON COLUMN rag_app.positions.name IS 'Название должности';
COMMENT ON COLUMN rag_app.positions.subdivision_id IS 'Внешний ключ к subdivisions(id)';

-- ============================================
-- Таблица: equipment_mart
-- Витрина техники (денормализованная таблица)
-- ============================================
CREATE TABLE rag_app.equipment_mart (
    station_name VARCHAR(200) NOT NULL,
    station_lat DOUBLE PRECISION,
    station_lon DOUBLE PRECISION,
    subdivision_code VARCHAR(20) NOT NULL,
    equipment_name VARCHAR(500) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    updated_at DATE DEFAULT CURRENT_DATE
);

-- Комментарии к таблице и полям
COMMENT ON TABLE rag_app.equipment_mart IS 'Витрина техники (денормализованная таблица)';
COMMENT ON COLUMN rag_app.equipment_mart.station_name IS 'Название станции (денормализовано)';
COMMENT ON COLUMN rag_app.equipment_mart.station_lat IS 'Широта станции';
COMMENT ON COLUMN rag_app.equipment_mart.station_lon IS 'Долгота станции';
COMMENT ON COLUMN rag_app.equipment_mart.subdivision_code IS 'Код подразделения';
COMMENT ON COLUMN rag_app.equipment_mart.equipment_name IS 'Название техники';
COMMENT ON COLUMN rag_app.equipment_mart.quantity IS 'Количество единиц';
COMMENT ON COLUMN rag_app.equipment_mart.updated_at IS 'Дата обновления (CURRENT_DATE)';

-- ============================================
-- Таблица: staff_mart
-- Витрина сотрудников (денормализованная таблица)
-- ============================================
CREATE TABLE rag_app.staff_mart (
    station_name VARCHAR(200) NOT NULL,
    station_lat DOUBLE PRECISION,
    station_lon DOUBLE PRECISION,
    subdivision_code VARCHAR(20) NOT NULL,
    position_name VARCHAR(500) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    updated_at DATE DEFAULT CURRENT_DATE
);

-- Комментарии к таблице и полям
COMMENT ON TABLE rag_app.staff_mart IS 'Витрина сотрудников (денормализованная таблица)';
COMMENT ON COLUMN rag_app.staff_mart.station_name IS 'Название станции';
COMMENT ON COLUMN rag_app.staff_mart.station_lat IS 'Широта';
COMMENT ON COLUMN rag_app.staff_mart.station_lon IS 'Долгота';
COMMENT ON COLUMN rag_app.staff_mart.subdivision_code IS 'Код подразделения';
COMMENT ON COLUMN rag_app.staff_mart.position_name IS 'Название должности';
COMMENT ON COLUMN rag_app.staff_mart.quantity IS 'Количество сотрудников';
COMMENT ON COLUMN rag_app.staff_mart.updated_at IS 'Дата обновления';

-- ============================================
-- Индексы для оптимизации запросов
-- ============================================

-- Индексы для stations
CREATE INDEX idx_stations_name ON rag_app.stations(name);
CREATE INDEX idx_stations_location ON rag_app.stations(latitude, longitude);

-- Индексы для subdivisions
CREATE INDEX idx_subdivisions_code ON rag_app.subdivisions(code);

-- Индексы для station_subdivisions
CREATE INDEX idx_station_subdivisions_station ON rag_app.station_subdivisions(station_id);
CREATE INDEX idx_station_subdivisions_subdivision ON rag_app.station_subdivisions(subdivision_id);

-- Индексы для equipment_items
CREATE INDEX idx_equipment_items_name ON rag_app.equipment_items(name);
CREATE INDEX idx_equipment_items_subdivision ON rag_app.equipment_items(subdivision_id);

-- Индексы для positions
CREATE INDEX idx_positions_name ON rag_app.positions(name);
CREATE INDEX idx_positions_subdivision ON rag_app.positions(subdivision_id);

-- Индексы для equipment_mart
CREATE INDEX idx_equipment_mart_station ON rag_app.equipment_mart(station_name);
CREATE INDEX idx_equipment_mart_subdivision ON rag_app.equipment_mart(subdivision_code);
CREATE INDEX idx_equipment_mart_equipment ON rag_app.equipment_mart(equipment_name);

-- Индексы для staff_mart
CREATE INDEX idx_staff_mart_station ON rag_app.staff_mart(station_name);
CREATE INDEX idx_staff_mart_subdivision ON rag_app.staff_mart(subdivision_code);
CREATE INDEX idx_staff_mart_position ON rag_app.staff_mart(position_name);

-- ============================================
-- Примеры заполнения данными (опционально)
-- ============================================

-- Пример заполнения stations
-- INSERT INTO rag_app.stations (name, latitude, longitude) VALUES
-- ('Станция Москва', 55.7558, 37.6173),
-- ('Станция Санкт-Петербург', 59.9343, 30.3351);

-- Пример заполнения subdivisions
-- INSERT INTO rag_app.subdivisions (code, full_name) VALUES
-- ('ДАВС', 'Дистанция аварийно-восстановительных средств'),
-- ('ДГПС', 'Дистанция гражданских сооружений');

-- Пример заполнения station_subdivisions
-- INSERT INTO rag_app.station_subdivisions (station_id, subdivision_id) VALUES
-- (1, 1),
-- (1, 2);

-- Пример заполнения equipment_items
-- INSERT INTO rag_app.equipment_items (name, subdivision_id) VALUES
-- ('Кран-балка 10т', 1),
-- ('Экскаватор', NULL);

-- Пример заполнения base_equipment
-- INSERT INTO rag_app.base_equipment (name) VALUES
-- ('Рация портативная'),
-- ('Огнетушитель');

-- Пример заполнения positions
-- INSERT INTO rag_app.positions (name, subdivision_id) VALUES
-- ('Начальник дистанции', 1),
-- ('Мастер', 1);

-- Пример заполнения equipment_mart
-- INSERT INTO rag_app.equipment_mart (station_name, station_lat, station_lon, subdivision_code, equipment_name, quantity) VALUES
-- ('Станция Москва', 55.7558, 37.6173, 'ДАВС', 'Кран-балка 10т', 2),
-- ('Станция Москва', 55.7558, 37.6173, 'ДАВС', 'Экскаватор', 1);

-- Пример заполнения staff_mart
-- INSERT INTO rag_app.staff_mart (station_name, station_lat, station_lon, subdivision_code, position_name, quantity) VALUES
-- ('Станция Москва', 55.7558, 37.6173, 'ДАВС', 'Начальник дистанции', 1),
-- ('Станция Москва', 55.7558, 37.6173, 'ДАВС', 'Мастер', 5);
