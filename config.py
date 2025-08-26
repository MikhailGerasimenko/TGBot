import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Telegram Bot
API_TOKEN = os.getenv('API_TOKEN') or ''
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '0'))

# Model Service
MODEL_SERVICE_URL = os.getenv('MODEL_SERVICE_URL', 'http://localhost:8000')
# Путь к GGUF модели для сервиса модели (используется model_service.py)
GGUF_MODEL_PATH = os.getenv('GGUF_MODEL_PATH', 'models/model-gigachat_20b_q6_0.gguf')

# RAG Configuration
EMBEDDING_MODEL_NAME = os.getenv('EMBEDDING_MODEL_NAME', 'paraphrase-multilingual-MiniLM-L12-v2')
CROSS_ENCODER_MODEL = os.getenv('CROSS_ENCODER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-12-v2')
USE_SEARCH_V2 = os.getenv('USE_SEARCH_V2', 'false').lower() == 'true'
SEARCH_V2_PERCENTAGE = int(os.getenv('SEARCH_V2_PERCENTAGE', '30'))  # % пользователей на новой версии
CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.12'))  # Порог уверенности для ответов

# Database (SQLite for logs); External employees DB
DATABASE_PATH = os.getenv('DATABASE_PATH', 'employees.db')
# MySQL
MYSQL_HOST = os.getenv('MYSQL_HOST', '')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
MYSQL_DB = os.getenv('MYSQL_DB', '')
MYSQL_USER = os.getenv('MYSQL_USER', '')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
# MS SQL Server
MSSQL_DSN = os.getenv('MSSQL_DSN', '')  # предпочтительно DSN (настроенный в odbc.ini)
MSSQL_HOST = os.getenv('MSSQL_HOST', '')
MSSQL_PORT = int(os.getenv('MSSQL_PORT', '1433'))
MSSQL_DB = os.getenv('MSSQL_DB', '')
MSSQL_USER = os.getenv('MSSQL_USER', '')
MSSQL_PASSWORD = os.getenv('MSSQL_PASSWORD', '')

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Redis
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Directories
DOCS_DIR = 'docs'
LOGS_DIR = 'logs'
MODELS_DIR = 'models'
BACKUPS_DIR = 'backups'

# 1C Export (Variant A): path to CSV/JSON export file
ONEC_EXPORT_PATH = os.getenv('ONEC_EXPORT_PATH', '')

# Создаем необходимые директории
for directory in [DOCS_DIR, LOGS_DIR, MODELS_DIR, BACKUPS_DIR]:
    os.makedirs(directory, exist_ok=True) 