# rag_system/database/db_manager.py
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os

# Конфигурация подключения к PostgreSQL
DB_CONFIG = {
    'user': 'user',
    'host': 'localhost',
    'database': 'mydatabase',
    'password': '12345',
    'port': 5428
}

def create_database():
    """Создает базу данных, если она не существует"""
    try:
        # Подключаемся к PostgreSQL без указания базы данных
        conn = psycopg2.connect(
            user=DB_CONFIG['user'],
            host=DB_CONFIG['host'],
            password=DB_CONFIG['password'],
            port=DB_CONFIG['port']
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Проверяем, существует ли база данных
        cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (DB_CONFIG['database'],))
        exists = cur.fetchone()
        
        if not exists:
            # Создаем базу данных
            cur.execute(f"CREATE DATABASE {DB_CONFIG['database']}")
            print(f"База данных {DB_CONFIG['database']} создана успешно")
        else:
            print(f"База данных {DB_CONFIG['database']} уже существует")
            
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Ошибка создания базы данных: {e}")

def create_tables():
    """Создает таблицы в базе данных"""
    try:
        # Подключаемся к базе данных
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
         
        # Создаем таблицу чатов
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id VARCHAR(255) PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                title VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Создаем таблицу сообщений
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                chat_id VARCHAR(255) NOT NULL,
                type VARCHAR(50) NOT NULL,
                text TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Создаем таблицу базы знаний
        cur.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL UNIQUE,
                answer TEXT NOT NULL,
                category VARCHAR(255) DEFAULT 'railway_emergency',
                usage_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Создаем индексы для оптимизации
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats(user_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)
        """)
        
        # Вставка тестовых данных базы знаний
        cur.execute("""
            INSERT INTO knowledge_base (question, answer, category) VALUES
            ('Что делать при аварии на железной дороге?', 'При аварии на железной дороге необходимо: 1) Немедленно сообщить машинисту и диспетчеру 2) Обеспечить безопасность пассажиров 3) Включить аварийную сигнализацию 4) Следовать инструкциям экстренной эвакуации', 'railway_emergency'),
            ('Как остановить поезд в аварийной ситуации?', 'Для экстренной остановки поезда: 1) Использовать стоп-кран только при непосредственной угрозе жизни 2) Сообщить машинисту по связи 3) Применить ручной тормоз если доступен', 'railway_emergency'),
            ('Протокол эвакуации при крушении поезда', 'Эвакуация при крушении: 1) Оценить обстановку 2) Открыть аварийные выходы 3) Помочь пострадавшим 4) Эвакуироваться на безопасное расстояние 5) Оказать первую помощь', 'railway_emergency')
            ON CONFLICT (question) DO NOTHING
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("Таблицы созданы успешно")
        
    except Exception as e:
        print(f"Ошибка создания таблиц: {e}")

if __name__ == "__main__":
    create_database()
    create_tables()