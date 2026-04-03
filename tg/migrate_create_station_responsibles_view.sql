-- Создание view для ответственных сотрудников на станциях с координатами
-- Эта view объединяет данные из таблиц station_responsibles, stations, employees, positions и subdivisions

-- Сначала проверяем, существуют ли необходимые таблицы
DO $$
BEGIN
    -- Таблица сотрудников
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'rag_app' AND table_name = 'employees') THEN
        CREATE TABLE rag_app.employees (
            id SERIAL PRIMARY KEY,
            full_name VARCHAR(200) NOT NULL,
            phone_number VARCHAR(20) NOT NULL,
            position_id INTEGER REFERENCES rag_app.positions(id),
            subdivision_id INTEGER REFERENCES rag_app.subdivisions(id),
            UNIQUE (full_name, phone_number)
        );
    END IF;

    -- Таблица ответственных на станциях
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'rag_app' AND table_name = 'station_responsibles') THEN
        CREATE TABLE rag_app.station_responsibles (
            id SERIAL PRIMARY KEY,
            station_id INTEGER REFERENCES rag_app.stations(id) ON DELETE CASCADE,
            subdivision_id INTEGER REFERENCES rag_app.subdivisions(id) ON DELETE CASCADE,
            employee_id INTEGER REFERENCES rag_app.employees(id) ON DELETE CASCADE,
            phone_number VARCHAR(20) NOT NULL,
            full_name VARCHAR(200) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (station_id, subdivision_id, employee_id)
        );
    END IF;
END $$;

-- Удаляем существующий view, если он есть
DROP VIEW IF EXISTS rag_app.station_responsibles_view CASCADE;

-- Создаём view с правильной структурой
CREATE VIEW rag_app.station_responsibles_view AS
SELECT
    sr.id,
    sr.station_id,
    s.name AS station_name,
    s.latitude AS station_lat,
    s.longitude AS station_lon,
    sr.employee_id,
    e.full_name AS employee_full_name,
    e.phone_number,
    sr.subdivision_id,
    sub.code AS subdivision_code,
    sub.full_name AS subdivision_name,
    e.position_id,
    p.name AS position_name,
    sr.created_at,
    sr.updated_at
FROM rag_app.station_responsibles sr
JOIN rag_app.stations s ON sr.station_id = s.id
JOIN rag_app.employees e ON sr.employee_id = e.id
JOIN rag_app.subdivisions sub ON sr.subdivision_id = sub.id
LEFT JOIN rag_app.positions p ON e.position_id = p.id;

-- Добавляем комментарии
COMMENT ON VIEW rag_app.station_responsibles_view IS 'View для получения ответственных сотрудников на станциях с координатами';
