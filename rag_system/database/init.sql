-- rag_system/database/init.sql
-- Создание таблицы чатов
CREATE TABLE IF NOT EXISTS chats (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Создание таблицы сообщений
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    chat_id VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    text TEXT NOT NULL,
    mode VARCHAR(50) DEFAULT 'chat',
    sources TEXT,
    employees TEXT,
    timestamp TIMESTAMP DEFAULT NOW(),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8)
);

-- Создание таблицы базы знаний
CREATE TABLE IF NOT EXISTS knowledge_base (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL UNIQUE,
    answer TEXT NOT NULL,
    category VARCHAR(255) DEFAULT 'railway_emergency',
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Создание индексов для оптимизации
CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);

-- Вставка тестовых данных базы знаний
INSERT INTO knowledge_base (question, answer, category) VALUES
('Что делать при аварии на железной дороге?', 'При аварии на железной дороге необходимо: 1) Немедленно сообщить машинисту и диспетчеру 2) Обеспечить безопасность пассажиров 3) Включить аварийную сигнализацию 4) Следовать инструкциям экстренной эвакуации', 'railway_emergency'),
('Как остановить поезд в аварийной ситуации?', 'Для экстренной остановки поезда: 1) Использовать стоп-кран только при непосредственной угрозе жизни 2) Сообщить машинисту по связи 3) Применить ручной тормоз если доступен', 'railway_emergency'),
('Протокол эвакуации при крушении поезда', 'Эвакуация при крушении: 1) Оценить обстановку 2) Открыть аварийные выходы 3) Помочь пострадавшим 4) Эвакуироваться на безопасное расстояние 5) Оказать первую помощь', 'railway_emergency')
ON CONFLICT (question) DO NOTHING;
