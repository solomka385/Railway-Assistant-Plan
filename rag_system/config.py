# config.py
import os

# Корневая директория скрипта
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Путь к модели (можно переопределить через переменную окружения MODEL_PATH)
MODEL_PATH = os.getenv("MODEL_PATH", "")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")


# Директории для хранения векторных БД
PERSIST_DIRECTORY_TECHNIC = os.getenv("PERSIST_DIRECTORY_TECHNIC", os.path.join(SCRIPT_DIR, "chroma_db_technic"))
PERSIST_DIRECTORY_WORK_PLAN = os.getenv("PERSIST_DIRECTORY_WORK_PLAN", os.path.join(SCRIPT_DIR, "chroma_db_work_plan"))
PERSIST_DIRECTORY_ALL_DOCS = os.getenv("PERSIST_DIRECTORY_ALL_DOCS", os.path.join(SCRIPT_DIR, "chroma_db_all_docs"))
PERSIST_DIRECTORY_EMPLOYEES = os.getenv("PERSIST_DIRECTORY_EMPLOYEES", os.path.join(SCRIPT_DIR, "chroma_db_employees"))
PERSIST_DIRECTORY_SUBDIVISIONS = os.getenv("PERSIST_DIRECTORY_SUBDIVISIONS", os.path.join(SCRIPT_DIR, "chroma_db_subdivisions"))

# Папки с исходными документами
DOCS_FOLDER_TECHNIC = os.getenv("DOCS_FOLDER_TECHNIC", os.path.join(SCRIPT_DIR, "docs", "list_technic"))
DOCS_FOLDER_WORK_PLAN = os.getenv("DOCS_FOLDER_WORK_PLAN", os.path.join(SCRIPT_DIR, "docs", "work_plan"))
DOCS_FOLDER_ALL_DOCS = os.getenv("DOCS_FOLDER_ALL_DOCS", os.path.join(SCRIPT_DIR, "docs", "all_docs"))
DOCS_FOLDER_EMPLOYEES = os.getenv("DOCS_FOLDER_EMPLOYEES", os.path.join(SCRIPT_DIR, "docs", "list_employee"))
DOCS_FOLDER_SUBDIVISIONS = os.getenv("DOCS_FOLDER_SUBDIVISIONS", os.path.join(SCRIPT_DIR, "docs", "list_subdivisions"))
EMPLOYEE_EXAMPLES_CSV = os.path.join(DOCS_FOLDER_EMPLOYEES, "employees_examples.csv")
PERSIST_DIRECTORY_EMPLOYEES_EXAMPLES = os.getenv("PERSIST_DIRECTORY_EMPLOYEES_EXAMPLES", os.path.join(SCRIPT_DIR, "chroma_db_employees_examples"))
# Путь к CSV-файлу с примерами аварий
CSV_FILE_PATH = os.getenv("CSV_FILE_PATH", os.path.join(DOCS_FOLDER_SUBDIVISIONS, "test.csv"))

# Пути к справочникам для валидации
EMPLOYEES_REFERENCE_CSV = os.path.join(DOCS_FOLDER_EMPLOYEES, "employees_reference.csv")
TECHNIC_REFERENCE_CSV = os.path.join(DOCS_FOLDER_TECHNIC, "technic_reference.csv")

# Путь к CSV с примерами подразделений
SUBDIVISION_EXAMPLES_CSV = os.path.join(DOCS_FOLDER_SUBDIVISIONS, "subdivisions_examples.csv")
# Директория для векторной БД примеров подразделений
PERSIST_DIRECTORY_SUBDIVISIONS_EXAMPLES = os.getenv(
    "PERSIST_DIRECTORY_SUBDIVISIONS_EXAMPLES",
    os.path.join(SCRIPT_DIR, "chroma_db_subdivisions_examples")
)

# Словарь допустимых подразделений
ALLOWED_SUBDIVISIONS = {
    "ABP": "аварийно-восстановительные работы",
    "БВС": "беспилотное воздушное судно",
    "ДАВС": "дирекция аварийно-восстановительных средств",
    "ДГПС": "старший дорожный диспетчер по управлению перевозками",
    "ДИ": "Московская дирекция инфраструктуры",
    "ДИ ЦУСИ": "Центр управления содержанием инфраструктуры",
    "ДРП": "Московская дирекция по ремонту пути",
    "ДЦС": "центр организации работы железнодорожных станций",
    "ДЦУП": "диспетчерский центр управления перевозками",
    "МАБ": "медицинская выездная врачебно-аварийная бригада",
    "МВПС": "моторвагонный подвижной состав",
    "МЧ": "механизированная дистанция погрузочно-разгрузочных работ",
    "МЧС": "Министерство Российской Федерации по делам гражданской обороны, чрезвычайным ситуациям и ликвидации последствий стихийных бедствий",
    "МКБКС": "мобильный комплекс видео-конференц-связи",
    "НТЭ": "Московская дирекция по энергообеспечению",
    "НУЗ": "негосударственное учреждение здравоохранения ОАО 'РЖД'",
    "НЦОП": "Центр охраны окружающей среды",
    "РКЧС": "региональная комиссия по предупреждению и ликвидации чрезвычайных ситуаций",
    "РСЧС": "Единая государственная система предупреждения и ликвидации чрезвычайных ситуаций",
    "РЦБЗ": "Московский региональный центр безопасности",
    "СЦ": "Ситуационный центр по принятию оперативных решений",
    "СЦБ": "устройства сигнализации, централизации и блокировки",
    "УМЖД": "управление Московской железной дороги",
    "ФГП": "Федеральное государственное предприятие 'Ведомственная охрана железнодорожного транспорта Российской Федерации'",
    "ЦБЗ": "Департамент безопасности ОАО 'РЖД'",
    "ЦД": "Центральная дирекция управления движением",
    "ЦДИ": "Центральная дирекция инфраструктуры",
    "ЦРБ": "Департамент безопасности движения ОАО 'РЖД'",
    "ЦСС": "Центральная станция связи",
    "ЦТО": "производственный участок мониторинга и диагностики",
    "ЦТУ": "отдел технического управления сетями связи",
    "ЦУП": "Центр управления перевозками",
    "ЦУТСС": "Центр управления технологической сетью связи",
    "ЦЧС": "Ситуационный центр мониторинга и управления чрезвычайными ситуациями",
    "ЧУЗ": "частное учреждение здравоохранения ОАО 'РЖД'"
}

# Ключевые слова для извлечения из описания аварий
# Можно расширять этот список или загружать из внешнего JSON файла
ACCIDENT_KEYWORDS = [
    "пожар", "взрыв", "сход", "столкновение", "утечка",
    "повреждение", "мост", "тоннель", "путь", "поезд",
    "вагон", "локомотив", "станция", "сигнализация", "связь",
    "ремонт", "эвакуация", "авария", "катастрофа", "обрушение",
    "медицин", "травм", "пострадавш", "жертвы", "гибель",
    "оползень", "ураган", "землетрясени", "лавина", "наводнение",
    "кибератака", "автоматика", "контактная сеть", "депо", "переезд",
    "насыпь", "балласт", "рельс", "контактная сеть", "электрический",
    "подвижной состав", "вагоны", "состав", "движение", "маневр",
    "тормоз", "автоматика", "сигнал", "стрелочный перевод", "мостовой переход",
    "опасные грузы", "химикаты", "газ", "дым", "задымление",
    "обрыв", "провода", "электричество", "ток", "напряжение",
    "снег", "метель", "обледенение", "лед", "падени", "дерев",
    "ветер", "буря", "шторм", "ветвь", "ствол"
]

# Путь к JSON файлу с ключевыми словами (опционально)
KEYWORDS_JSON_PATH = os.getenv("KEYWORDS_JSON_PATH", os.path.join(SCRIPT_DIR, "keywords.json"))

# Максимальное количество ключевых слов для извлечения
MAX_KEYWORDS_TO_EXTRACT = int(os.getenv("MAX_KEYWORDS_TO_EXTRACT", "7"))

# Настройки пула PostgreSQL
PG_CONFIG = {
    'minconn': int(os.getenv("PG_MINCONN", "1")),
    'maxconn': int(os.getenv("PG_MAXCONN", "10"))
}