-- Миграция: добавление колонок mode, sources, employees в таблицу messages
-- Выполнить на мастер-хосте PostgreSQL

-- Добавляем колонку mode, если её нет
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'mode'
    ) THEN
        ALTER TABLE messages ADD COLUMN mode VARCHAR(10) DEFAULT 'plan';
        RAISE NOTICE 'Колонка mode добавлена в таблицу messages';
    ELSE
        RAISE NOTICE 'Колонка mode уже существует в таблице messages';
    END IF;
END $$;

-- Добавляем колонку sources, если её нет
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'sources'
    ) THEN
        ALTER TABLE messages ADD COLUMN sources JSONB DEFAULT '[]'::jsonb;
        RAISE NOTICE 'Колонка sources добавлена в таблицу messages';
    ELSE
        RAISE NOTICE 'Колонка sources уже существует в таблице messages';
    END IF;
END $$;

-- Добавляем колонку employees, если её нет
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'employees'
    ) THEN
        ALTER TABLE messages ADD COLUMN employees JSONB DEFAULT '[]'::jsonb;
        RAISE NOTICE 'Колонка employees добавлена в таблицу messages';
    ELSE
        RAISE NOTICE 'Колонка employees уже существует в таблице messages';
    END IF;
END $$;

-- Проверяем результат
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'messages'
ORDER BY ordinal_position;
