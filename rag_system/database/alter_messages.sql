-- rag_system/database/alter_messages.sql
-- Добавление недостающих столбцов в таблицу messages

ALTER TABLE messages 
ADD COLUMN IF NOT EXISTS mode VARCHAR(50) DEFAULT 'chat',
ADD COLUMN IF NOT EXISTS sources TEXT,
ADD COLUMN IF NOT EXISTS employees TEXT;
