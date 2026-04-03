-- Миграция: удаление колонок для голосовых сообщений из таблицы messages
-- Выполнить на мастер-хосте PostgreSQL

-- Удаляем колонку audio_url, если она существует
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'audio_url'
    ) THEN
        ALTER TABLE messages DROP COLUMN audio_url;
        RAISE NOTICE 'Колонка audio_url удалена из таблицы messages';
    ELSE
        RAISE NOTICE 'Колонка audio_url не существует в таблице messages';
    END IF;
END $$;

-- Удаляем колонку transcription, если она существует
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'transcription'
    ) THEN
        ALTER TABLE messages DROP COLUMN transcription;
        RAISE NOTICE 'Колонка transcription удалена из таблицы messages';
    ELSE
        RAISE NOTICE 'Колонка transcription не существует в таблице messages';
    END IF;
END $$;

-- Удаляем колонку audio_duration, если она существует
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'audio_duration'
    ) THEN
        ALTER TABLE messages DROP COLUMN audio_duration;
        RAISE NOTICE 'Колонка audio_duration удалена из таблицы messages';
    ELSE
        RAISE NOTICE 'Колонка audio_duration не существует в таблице messages';
    END IF;
END $$;

-- Проверяем результат
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'messages'
ORDER BY ordinal_position;
