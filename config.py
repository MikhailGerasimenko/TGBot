import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Telegram Bot
API_TOKEN = os.getenv('API_TOKEN', '7987520742:AAHOXmsESsiP46HTQLPxu5PTzdDErj0XuwE')
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '925237471'))

# Model Service
MODEL_SERVICE_URL = os.getenv('MODEL_SERVICE_URL', 'http://localhost:8000')

# Database
DATABASE_PATH = os.getenv('DATABASE_PATH', 'employees.db')

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Directories
DOCS_DIR = 'docs'
LOGS_DIR = 'logs'
MODELS_DIR = 'models'
BACKUPS_DIR = 'backups'

# Создаем необходимые директории
for directory in [DOCS_DIR, LOGS_DIR, MODELS_DIR, BACKUPS_DIR]:
    os.makedirs(directory, exist_ok=True) 