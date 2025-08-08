# Корпоративный Telegram Бот с LLM

Telegram бот для корпоративной поддержки с использованием Language Model (LLM) для ответов на вопросы и обработки документации.

## Особенности

- 🤖 Регистрация пользователей с верификацией
- 🧠 Интеграция с LLM (Saiga-2) для ответов на вопросы
- 📚 RAG (Retrieval Augmented Generation) для работы с документами
- 🔄 Асинхронная обработка запросов
- 🎯 Микросервисная архитектура (отдельный сервис для LLM)
- 📊 Мониторинг и логирование

## Архитектура

Проект разделен на два основных компонента:

1. **Model Service** (model_service.py):
   - FastAPI сервер для LLM
   - Загрузка GGUF модели через `llama-cpp-python`
   - Работа с GPU/CPU (через n_gpu_layers)
   - Создание эмбеддингов (Sentence-Transformers)

2. **Telegram Bot** (bot.py):
   - Обработка команд пользователей
   - Регистрация и верификация
   - Работа с базой данных
   - Взаимодействие с Model Service через HTTP

## Требования

### Для Model Service:
- Python 3.8+
- NVIDIA GPU (опционально) — для ускорения указать `LLAMA_GPU_LAYERS`
- 8–24GB RAM (в зависимости от модели)

### Для Telegram Bot:
- Python 3.8+
- 4GB RAM

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл .env:
```bash
cp env.example .env
# Отредактируйте .env, добавив свои значения
```

## Запуск

### Model Service (на сервере):

1. Укажите путь к GGUF в `.env`:
```env
GGUF_MODEL_PATH=/home/bot/models/model-q2_k.gguf
LLAMA_CTX=2048
LLAMA_THREADS=4
LLAMA_BATCH=256
LLAMA_GPU_LAYERS=32
```

2. Запуск:
```bash
python model_service.py
# или через systemd (рекомендуется)
sudo cp model-service.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable model-service
sudo systemctl start model-service
```

3. Проверка статуса:
```bash
sudo systemctl status model-service
sudo journalctl -u model-service -f
```

### Telegram Bot:

1. Быстрый старт (без модели, проверка регистрации):
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp env.example .env
# при желании можно переопределить API_TOKEN и ADMIN_CHAT_ID в .env (по умолчанию уже заданы)
python main.py
```

Альтернатива (одноразовый запуск без правки .env):
```bash
API_TOKEN=... ADMIN_CHAT_ID=... MODEL_SERVICE_URL=http://localhost:8000 venv/bin/python main.py
```

2. Для разработки:
```bash
./dev.sh
```

3. Для production:
```bash
sudo cp telegram-bot.service /etc/systemd/system/
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

## Разработка

1. Настройка окружения:
```bash
pip install -r requirements.txt
```

2. Запуск тестов:
```bash
python -m pytest tests/
```

3. Проверка кода:
```bash
# Проверка синтаксиса
python -m py_compile main.py bot.py database.py

# Запуск линтера
flake8 .
```

## Деплой

1. На сервере:
```bash
./update.sh
```

2. Локально:
```bash
./deploy.sh "описание изменений"
```

## Структура проекта

```
telegram-bot/
├── main.py           # Точка входа
├── bot.py            # Логика бота
├── database.py       # Работа с БД
├── model_service.py  # LLM сервис (llama-cpp, GGUF)
├── llm_client.py     # Клиент для LLM
├── config.py         # Конфигурация
├── requirements.txt  # Зависимости
├── setup.sh          # Установка
├── update.sh         # Обновление
├── deploy.sh         # Деплой
├── dev.sh            # Разработка
└── docs/             # Документация
```

## Конфигурация

Основные настройки в файле `.env`:

```env
# Telegram
API_TOKEN=your_bot_token
ADMIN_CHAT_ID=your_admin_id

# Model Service
MODEL_SERVICE_URL=http://your-server:8000
GGUF_MODEL_PATH=/path/to/model.gguf
LLAMA_CTX=2048
LLAMA_THREADS=4
LLAMA_BATCH=256
LLAMA_GPU_LAYERS=32
MAX_NEW_TOKENS=512

# Database
DATABASE_PATH=employees.db

# Logging
LOG_LEVEL=INFO
```

## Мониторинг

1. Логи бота:
```bash
tail -f logs/bot.log
```

2. Логи модели:
```bash
tail -f logs/model_service.log
```

3. Системные логи:
```bash
sudo journalctl -u telegram-bot -f
sudo journalctl -u model-service -f
```

## Безопасность

1. Все секреты хранятся в `.env` (в коде отсутствуют реальные токены)
2. Верификация пользователей
3. Доступ к API модели — по внутренней сети/Firewall
4. Регулярное резервное копирование данных

## Поддержка

При возникновении проблем:
1. Проверьте логи
2. Проверьте статус сервисов
3. Создайте Issue в репозитории

## Лицензия

MIT

