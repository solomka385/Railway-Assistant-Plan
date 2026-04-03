# db.py
import psycopg2
from psycopg2 import pool as psycopg2_pool
import logging
import os
import json
from config import PG_CONFIG

logger = logging.getLogger(__name__)

pg_pool = None


def find_master_host():
    """Находит мастер-хост (writeable) из списка хостов."""
    pg_hosts = os.getenv("PG_HOST", "").split(',')
    pg_port = os.getenv("PG_PORT", "")
    pg_db = os.getenv("PG_DB", "")
    pg_user = os.getenv("PG_USER", "")
    pg_password = os.getenv("PG_PASSWORD", "")
    sslmode = os.getenv("PG_SSLMODE", "")
    sslrootcert = os.getenv("PG_SSLROOTCERT", "")

    # Если сертификат не указан, пытаемся использовать стандартный путь
    if not sslrootcert:
        if os.name == 'nt':
            sslrootcert = os.path.join(os.environ['USERPROFILE'], '.postgresql', 'root.crt').replace('\\', '/')
        else:
            sslrootcert = os.path.join(os.path.expanduser('~'), '.postgresql', 'root.crt')

    # Проверяем наличие сертификата, если его нет – скачиваем (для Linux)
    if not os.path.exists(sslrootcert) and os.name != 'nt':
        logger.warning(f"SSL сертификат не найден: {sslrootcert}, пробуем скачать...")
        os.makedirs(os.path.dirname(sslrootcert), exist_ok=True)
        import urllib.request
        urllib.request.urlretrieve("https://storage.yandexcloud.net/cloud-certs/CA.pem", sslrootcert)
        os.chmod(sslrootcert, 0o655)

    # Формируем базовый DSN
    base_dsn = f"port={pg_port} dbname={pg_db} user={pg_user} password={pg_password} sslmode={sslmode}"
    if sslrootcert and os.path.exists(sslrootcert):
        base_dsn += f" sslrootcert={sslrootcert}"

    # Проверяем каждый хост
    for host in pg_hosts:
        host = host.strip()
        logger.info(f"[POSTGRES] Проверка хоста: {host}")
        try:
            dsn = f"host={host} {base_dsn}"
            conn = psycopg2.connect(dsn)
            cur = conn.cursor()
            cur.execute("SHOW transaction_read_only")
            read_only = cur.fetchone()[0]
            cur.close()
            conn.close()
            
            if read_only == 'off':
                logger.info(f"[POSTGRES] Найден мастер-хост: {host}")
                return host
            else:
                logger.info(f"[POSTGRES] Хост {host} в режиме read-only (реплика)")
        except Exception as e:
            logger.warning(f"[POSTGRES] Ошибка подключения к {host}: {e}")
    
    raise Exception("Не удалось найти мастер-хост PostgreSQL")


def close_pg_pool():
    """Закрывает пул соединений PostgreSQL."""
    global pg_pool
    if pg_pool:
        try:
            pg_pool.closeall()
            logger.info("[POSTGRES] Пул соединений закрыт")
        except Exception as e:
            logger.error(f"[POSTGRES] Ошибка закрытия пула: {e}")
        finally:
            pg_pool = None


def init_pg_pool():
    """Инициализирует пул соединений с PostgreSQL."""
    global pg_pool
    try:
        # Закрываем старый пул, если существует
        if pg_pool:
            close_pg_pool()
        
        # Находим мастер-хост
        master_host = find_master_host()
        
        pg_port = os.getenv("PG_PORT", "")
        pg_db = os.getenv("PG_DB", "")
        pg_user = os.getenv("PG_USER", "")
        pg_password = os.getenv("PG_PASSWORD", "")
        sslmode = os.getenv("PG_SSLMODE", "")
        sslrootcert = os.getenv("PG_SSLROOTCERT", "")

        # Если сертификат не указан, пытаемся использовать стандартный путь
        if not sslrootcert:
            if os.name == 'nt':
                sslrootcert = os.path.join(os.environ['USERPROFILE'], '.postgresql', 'root.crt').replace('\\', '/')
            else:
                sslrootcert = os.path.join(os.path.expanduser('~'), '.postgresql', 'root.crt')

        # Проверяем наличие сертификата, если его нет – скачиваем (для Linux)
        if not os.path.exists(sslrootcert) and os.name != 'nt':
            logger.warning(f"SSL сертификат не найден: {sslrootcert}, пробуем скачать...")
            os.makedirs(os.path.dirname(sslrootcert), exist_ok=True)
            import urllib.request
            urllib.request.urlretrieve("https://storage.yandexcloud.net/cloud-certs/CA.pem", sslrootcert)
            os.chmod(sslrootcert, 0o655)

        # Формируем DSN с мастер-хостом
        dsn = f"host={master_host} port={pg_port} dbname={pg_db} user={pg_user} password={pg_password} sslmode={sslmode} options='-c search_path=rag_app'"
        if sslrootcert and os.path.exists(sslrootcert):
            dsn += f" sslrootcert={sslrootcert}"

        pg_pool = psycopg2_pool.ThreadedConnectionPool(
            minconn=PG_CONFIG['minconn'],
            maxconn=PG_CONFIG['maxconn'],
            dsn=dsn
        )

        # Проверка
        conn = pg_pool.getconn()
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.execute("SHOW transaction_read_only")
        read_only = cur.fetchone()[0]
        cur.close()
        pg_pool.putconn(conn)
        
        if read_only == 'off':
            logger.info("[POSTGRES] Пул соединений инициализирован (мастер-хост)")
        else:
            logger.warning("[POSTGRES] Пул соединений инициализирован, но хост в режиме read-only!")
        
        return True

    except Exception as e:
        logger.error(f"[POSTGRES] Ошибка инициализации: {e}", exc_info=True)
        return False


def get_pg_connection():
    global pg_pool
    if pg_pool:
        try:
            return pg_pool.getconn()
        except Exception as e:
            logger.error(f"[POSTGRES] Ошибка получения соединения: {e}")
            return None
    return None


def return_pg_connection(conn):
    global pg_pool
    if pg_pool and conn:
        try:
            pg_pool.putconn(conn)
        except Exception as e:
            logger.error(f"[POSTGRES] Ошибка возврата соединения: {e}")


def save_message_to_db(chat_id: str, message_type: str, text: str, mode: str = "plan", sources: list = None, employees: list = None):
    """
    Сохраняет сообщение в таблицу messages для отображения в чате.
    
    Args:
        chat_id: ID чата
        message_type: Тип сообщения ('user' или 'bot')
        text: Текст сообщения
        mode: Режим ('plan' или 'chat')
        sources: Список источников
        employees: Список сотрудников
    
    Returns:
        bool: True если сохранение успешно, иначе False
    """
    global pg_pool
    
    # Проверяем, что пул инициализирован с мастером
    if not pg_pool:
        logger.error("[POSTGRES] Пул соединений не инициализирован")
        return False
    
    conn = get_pg_connection()
    if not conn:
        logger.error("[POSTGRES] Не удалось получить соединение для сохранения сообщения")
        return False
    
    try:
        # Откатываем любую незавершенную транзакцию
        try:
            conn.rollback()
        except:
            pass
        
        # Проверяем, что соединение не в режиме только для чтения
        cur = conn.cursor()
        cur.execute("SHOW transaction_read_only")
        read_only = cur.fetchone()[0]
        
        if read_only == 'on':
            logger.warning("[POSTGRES] Соединение в режиме только для чтения, переподключаемся к мастеру...")
            cur.close()
            return_pg_connection(conn)
            
            # Переинициализируем пул с мастером
            try:
                init_pg_pool()
                conn = get_pg_connection()
                if not conn:
                    logger.error("[POSTGRES] Не удалось переподключиться к мастеру")
                    return False
                cur = conn.cursor()
                # Повторно проверяем режим только для чтения
                cur.execute("SHOW transaction_read_only")
                read_only = cur.fetchone()[0]
                if read_only == 'on':
                    logger.error("[POSTGRES] После переподключения хост всё ещё в режиме read-only!")
                    cur.close()
                    return_pg_connection(conn)
                    return False
            except Exception as e:
                logger.error(f"[POSTGRES] Ошибка переподключения: {e}")
                return False
        
        # Сохраняем сообщение в таблицу messages (используем схему rag_app)
        cur.execute("""
            INSERT INTO rag_app.messages (chat_id, type, text, mode, sources, employees)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            chat_id,
            message_type,
            text,
            mode,
            json.dumps(sources or [], ensure_ascii=False),
            json.dumps(employees or [], ensure_ascii=False)
        ))
        
        conn.commit()
        cur.close()
        logger.info(f"[POSTGRES] Сообщение сохранено: chat_id={chat_id}, type={message_type}")
        return True
        
    except Exception as e:
        logger.error(f"[POSTGRES] Ошибка сохранения сообщения: {e}", exc_info=True)
        try:
            conn.rollback()
        except:
            pass
        return False
    finally:
        return_pg_connection(conn)