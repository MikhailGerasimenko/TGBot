# 🤖 Корпоративный AI-ассистент

Полнофункциональный корпоративный бот с интеграцией LLM (GigaChat-20B) и системой RAG для обработки корпоративных документов.

## 📋 Содержание

- [Обзор проекта](#обзор-проекта)
- [Архитектура](#архитектура)
- [Технологический стек](#технологический-стек)
- [Установка и настройка](#установка-и-настройка)
- [Конфигурация](#конфигурация)
- [Docker развертывание](#docker-развертывание)
- [API документация](#api-документация)
- [Использование](#использование)
- [Мониторинг и аналитика](#мониторинг-и-аналитика)
- [Troubleshooting](#troubleshooting)
- [Разработка](#разработка)

## 🎯 Обзор проекта

### Основные возможности

- **🤖 AI-ассистент** на базе GigaChat-20B с поддержкой русского языка
- **📚 RAG система** для работы с корпоративными документами (СОП, регламенты)
- **👥 Авторизация** через интеграцию с 1С
- **📊 Аналитика** использования и качества ответов
- **🔄 A/B тестирование** различных подходов к поиску
- **📈 Мониторинг** производительности и использования

### Ключевые особенности

- **Умное разбиение документов** - адаптивные стратегии для разных типов документов
- **Гибридный поиск** - комбинация FAISS (векторный) и BM25 (ключевые слова)
- **Cross-Encoder переранжирование** для повышения точности поиска
- **Интеграция с 1С** для верификации сотрудников
- **Система обратной связи** с кнопками 👍👎
- **Автоматический деплой** на GPU серверы

## 🏗️ Архитектура

### Компоненты системы

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │    │  Model Service  │    │   Database      │
│   (aiogram)     │◄──►│   (FastAPI)     │◄──►│   (SQLite)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Documents     │    │   LLM Model     │    │   1C Sync       │
│   (.docx files) │    │  (GigaChat-20B) │    │   (MySQL/MSSQL) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Поток данных

1. **Загрузка документов** → Умное разбиение → Индексация в FAISS/BM25
2. **Пользовательский запрос** → Поиск релевантных документов → Генерация ответа
3. **Обратная связь** → Аналитика → Улучшение качества

## 🛠️ Технологический стек

### Backend
- **Python 3.9+** - основной язык разработки
- **FastAPI** - REST API сервис для LLM
- **aiogram 3.x** - Telegram Bot API
- **llama-cpp-python** - работа с GGUF моделями
- **sentence-transformers** - эмбеддинги и поиск
- **FAISS** - векторный поиск
- **rank-bm25** - sparse поиск

### Базы данных
- **SQLite** - основная база данных
- **MySQL/MSSQL** - интеграция с 1С
- **Redis** - кэширование (опционально)

### AI/ML
- **GigaChat-20B** - основная языковая модель
- **paraphrase-multilingual-MiniLM-L12-v2** - эмбеддинги
- **cross-encoder/ms-marco-MiniLM-L-12-v2** - переранжирование

### DevOps
- **Docker** - контейнеризация
- **Systemd** - управление сервисами
- **Linux** - серверная ОС
- **Git** - версионный контроль

## 🚀 Установка и настройка

### Системные требования

- **CPU:** 4+ ядра
- **RAM:** 16GB+ (для GPU версии)
- **GPU:** NVIDIA RTX 3080+ (рекомендуется)
- **Storage:** 100GB+ свободного места
- **OS:** Ubuntu 20.04+ / CentOS 8+

### Быстрая установка

```bash
# Клонирование репозитория
git clone <repository-url>
cd corporate-bot

# Установка зависимостей
pip install -r requirements.txt

# Настройка окружения
cp env.example .env
nano .env  # Настройте параметры

# Инициализация БД
python init_db.py

# Скачивание модели
./download_model.sh gigachat_20b_q8_0

# Запуск сервисов
python model_service.py &
python bot.py
```

### Docker установка

```bash
# Сборка образов
docker-compose build

# Запуск
docker-compose up -d

# Проверка статуса
docker-compose ps
```

## ⚙️ Конфигурация

### Основные параметры (.env)

```bash
# Telegram Bot
API_TOKEN=your_telegram_bot_token
ADMIN_CHAT_ID=your_admin_telegram_id

# LLM Model
GGUF_MODEL_PATH=models/model-gigachat_20b_q8_0.gguf
LLAMA_CTX=8192
LLAMA_THREADS=16
LLAMA_BATCH=1024
LLAMA_GPU_LAYERS=40
MAX_NEW_TOKENS=512

# RAG System
EMBEDDING_MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2
CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-12-v2
USE_SEARCH_V2=true
SEARCH_V2_PERCENTAGE=50

# Database
DATABASE_PATH=data/employees.db
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=corporate_db
MYSQL_USER=user
MYSQL_PASSWORD=password

# GPU Optimization
CUDA_VISIBLE_DEVICES=0
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024
```

### Оптимизация производительности

#### Для GPU серверов
```bash
# Высокая производительность
LLAMA_GPU_LAYERS=40
LLAMA_CTX=8192
LLAMA_THREADS=16
LLAMA_BATCH=1024

# Максимальная скорость (BF16 модель)
GGUF_MODEL_PATH=models/model-gigachat_20b_bf16.gguf
LLAMA_GPU_LAYERS=80
```

#### Для CPU серверов
```bash
# Экономия ресурсов
LLAMA_GPU_LAYERS=0
LLAMA_CTX=4096
LLAMA_THREADS=8
LLAMA_BATCH=512
```

## 🐳 Docker развертывание

### Структура Docker

```
docker/
├── Dockerfile.bot          # Образ для Telegram бота
├── Dockerfile.model        # Образ для LLM сервиса
├── docker-compose.yml      # Оркестрация сервисов
├── docker-compose.gpu.yml  # GPU версия
└── nginx.conf             # Конфигурация Nginx
```

### Docker Compose

```yaml
version: '3.8'

services:
  model-service:
    build:
      context: .
      dockerfile: docker/Dockerfile.model
    ports:
      - "8000:8000"
    volumes:
      - ./models:/app/models
      - ./data:/app/data
    environment:
      - GGUF_MODEL_PATH=/app/models/model-gigachat_20b_q8_0.gguf
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  telegram-bot:
    build:
      context: .
      dockerfile: docker/Dockerfile.bot
    depends_on:
      - model-service
    environment:
      - MODEL_SERVICE_URL=http://model-service:8000
    volumes:
      - ./data:/app/data
      - ./documents:/app/documents

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./docker/nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - model-service
```

### GPU поддержка

```bash
# Установка NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# Запуск с GPU
docker-compose -f docker-compose.gpu.yml up -d
```

## 📡 API документация

### Model Service API

#### Генерация текста
```http
POST /generate
Content-Type: application/json

{
  "query": "Что такое СОП?",
  "context": "дополнительный контекст",
  "max_tokens": 512,
  "temperature": 0.7
}
```

#### Создание эмбеддингов
```http
POST /embeddings
Content-Type: application/json

{
  "texts": ["текст 1", "текст 2"]
}
```

#### Индексация документов
```http
POST /index
Content-Type: application/json

{
  "documents": ["документ 1", "документ 2"]
}
```

#### Поиск документов
```http
POST /search
Content-Type: application/json

{
  "query": "поисковый запрос",
  "top_k": 5
}
```

### Telegram Bot API

#### Команды пользователей
- `/start` - начало работы, регистрация
- `/help` - справка по использованию
- `/status` - статус авторизации
- `/cancel` - отмена текущей операции

#### Команды администратора
- `/train` - загрузка документов (.docx)
- `/analytics` - статистика использования
- `/stats` - детальная аналитика
- `/compare_search` - сравнение версий поиска

## 💻 Использование

### Для пользователей

1. **Регистрация**
   ```
   /start → Ввод ФИО → Ввод табельного номера → Подтверждение
   ```

2. **Задавание вопросов**
   ```
   Нажмите "Спросить" → Введите вопрос → Получите ответ
   ```

3. **Обратная связь**
   ```
   После ответа используйте кнопки 👍👎 для оценки качества
   ```

### Для администраторов

1. **Загрузка документов**
   ```
   /train → Отправка .docx файла → Автоматическая индексация
   ```

2. **Мониторинг**
   ```
   /analytics → Просмотр статистики использования
   /stats → Детальная аналитика по запросам
   ```

3. **Управление системой**
   ```bash
   # Перезапуск сервисов
   sudo systemctl restart telegram-bot
   sudo systemctl restart model-service
   
   # Просмотр логов
   sudo journalctl -u telegram-bot -f
   sudo journalctl -u model-service -f
   ```

## 📊 Мониторинг и аналитика

### Метрики производительности

- **Скорость генерации** (токенов/сек)
- **Время ответа** (мс)
- **Использование GPU/CPU**
- **Потребление памяти**

### Аналитика использования

- **Популярные вопросы**
- **Время ответа**
- **Удовлетворенность** (👍👎)
- **Неотвеченные вопросы**

### Логирование

```bash
# Логи бота
tail -f logs/bot.log

# Логи модели
tail -f logs/model_service.log

# Системные логи
sudo journalctl -u telegram-bot -f
sudo journalctl -u model-service -f
```

## 🔧 Troubleshooting

### Частые проблемы

#### 1. Модель не загружается
```bash
# Проверка GPU
nvidia-smi

# Проверка модели
ls -la models/

# Перезапуск сервиса
sudo systemctl restart model-service
```

#### 2. Медленная генерация
```bash
# Оптимизация настроек
LLAMA_GPU_LAYERS=40
LLAMA_CTX=8192
LLAMA_THREADS=16

# Проверка нагрузки
htop
nvidia-smi
```

#### 3. Ошибки поиска
```bash
# Переиндексация документов
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{"documents": []}'
```

#### 4. Проблемы с БД
```bash
# Проверка БД
sqlite3 data/employees.db ".tables"

# Резервное копирование
cp data/employees.db data/employees.db.backup
```

### Отладка

```bash
# Включение debug режима
export LOG_LEVEL=DEBUG

# Проверка конфигурации
python -c "from config import *; print('Config loaded')"

# Тест API
curl http://localhost:8000/health
```

## 👨‍💻 Разработка

### Структура проекта

```
corporate-bot/
├── bot.py                 # Основной файл бота
├── model_service.py       # LLM сервис
├── database.py           # Работа с БД
├── llm_client.py         # Клиент для LLM
├── config.py             # Конфигурация
├── requirements.txt      # Зависимости
├── env.example           # Пример .env
├── docs/                 # Документация
├── docker/               # Docker файлы
├── models/               # Модели LLM
├── data/                 # База данных
├── documents/            # Корпоративные документы
└── logs/                 # Логи
```

### Добавление новых функций

1. **Создание новой команды**
   ```python
   @dp.message(Command('new_command'))
   async def new_command_handler(message: types.Message):
       # Логика команды
       pass
   ```

2. **Расширение API**
   ```python
   @app.post("/new_endpoint")
   async def new_endpoint(req: NewRequest):
       # Логика эндпоинта
       return NewResponse()
   ```

3. **Добавление таблицы БД**
   ```python
   # В database.py
   CREATE_TABLE_SQL = """
   CREATE TABLE IF NOT EXISTS new_table (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       field TEXT NOT NULL
   );
   """
   ```

### Тестирование

```bash
# Запуск тестов
python -m pytest tests/

# Тест модели
python test_lama.py

# Тест RAG системы
python test_rag_comprehensive.py
```

### CI/CD

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to server
        run: |
          # Деплой на сервер
```

## 📞 Поддержка

### Контакты
- **Разработчик:** [Ваше имя]
- **Email:** [email]
- **Telegram:** [username]

### Полезные ссылки
- [Документация aiogram](https://docs.aiogram.dev/)
- [FastAPI документация](https://fastapi.tiangolo.com/)
- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python)
- [FAISS документация](https://faiss.ai/)

---

**Версия:** 1.0.0  
**Последнее обновление:** 2025-01-19  
**Лицензия:** MIT 