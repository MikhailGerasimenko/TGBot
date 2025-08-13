import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Telegram Bot
API_TOKEN = os.getenv('API_TOKEN', '7987520742:AAHOXmsESsiP46HTQLPxu5PTzdDErj0XuwE')
ADMIN_CHAT_ID = int((os.getenv('ADMIN_CHAT_ID') or '925237471'))

# Model Service
MODEL_SERVICE_URL = os.getenv('MODEL_SERVICE_URL', 'http://localhost:8000')
# Путь к GGUF модели для сервиса модели (используется model_service.py)
GGUF_MODEL_PATH = os.getenv('GGUF_MODEL_PATH', 'model-q2_k.gguf')

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