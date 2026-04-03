-- Миграция: создание и обновление таблиц в схеме rag_app
-- Дата: 2026-03-25
-- Описание: Создает все необходимые таблицы и исправляет ограничения

-- Создаем схему rag_app, если она не существует
CREATE SCHEMA IF NOT EXISTS rag_app;

-- Устанавливаем схему rag_app
SET search_path TO rag_app, public;

-- Создаем таблицу user_sessions
CREATE TABLE IF NOT EXISTS user_sessions (
    "sid" varchar NOT NULL PRIMARY KEY,
    "sess" json NOT NULL,
    "expire" timestamp(6) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expire ON user_sessions ("expire");

-- Создаем таблицу users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создаем таблицу chats
CREATE TABLE IF NOT EXISTS chats (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создаем таблицу messages
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    chat_id VARCHAR(50) NOT NULL,
    type VARCHAR(10) NOT NULL,
    text TEXT NOT NULL,
    mode VARCHAR(10) DEFAULT 'plan',
    sources JSONB DEFAULT '[]'::jsonb,
    employees JSONB DEFAULT '[]'::jsonb,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);

-- Создаем таблицу knowledge_base
CREATE TABLE IF NOT EXISTS knowledge_base (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(50),
    usage_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Сначала удаляем все уникальные ограничения на таблицу knowledge_base
DO $$
DECLARE
    constraint_name text;
BEGIN
    -- Находим и удаляем все уникальные ограничения на knowledge_base
    FOR constraint_name IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'rag_app.knowledge_base'::regclass
        AND contype = 'u'
    LOOP
        EXECUTE format('ALTER TABLE rag_app.knowledge_base DROP CONSTRAINT IF EXISTS %I', constraint_name);
        RAISE NOTICE 'Удалено ограничение: %', constraint_name;
    END LOOP;
END $$;

-- Добавляем составное уникальное ограничение (question, category)
ALTER TABLE knowledge_base
ADD CONSTRAINT knowledge_base_question_category_unique
UNIQUE (question, category);

-- Проверка результата
SELECT conname, contype, pg_get_constraintdef(oid) as definition
FROM pg_constraint
WHERE conrelid = 'rag_app.knowledge_base'::regclass;

-- Проверка всех таблиц в схеме rag_app
SELECT table_name, table_schema
FROM information_schema.tables
WHERE table_schema = 'rag_app'
ORDER BY table_name;
