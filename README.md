# Корпоративный Telegram Бот с LLM

Telegram бот для корпоративной поддержки с использованием Language Model (LLM) для ответов на вопросы и обработки документации. Реализует современные методы RAG (Retrieval Augmented Generation) на основе опыта X5 Tech.

## Особенности

- 🤖 Регистрация пользователей с верификацией (MySQL/MSSQL/SQLite или файл выгрузки)
- 🧠 Интеграция с LLM (Saiga-2, llama-cpp) для ответов на вопросы
- 📚 **Продвинутый RAG (Retrieval Augmented Generation)**:
  - **Cross-Encoder переранжирование** для повышения точности поиска
  - **Query Expansion** - автоматическое расширение запросов через LLM
  - **Гибридный поиск**: FAISS (dense) + BM25 + Cross-Encoder реранкинг
  - **Умное разбиение документов** с метаданными (тип, отдел, даты)
  - **Персистентность индекса** - сохранение на диск для быстрого запуска
  - **A/B тестирование** версий поиска с автоматическим распределением
  - Отображение «Источников» в ответе и порог уверенности
- 📊 **Расширенная аналитика и мониторинг**:
  - Метрики времени ответа, уверенности, популярных вопросов
  - Система фидбека с кнопками 👍👎 для оценки ответов
  - Сбор неотвеченных вопросов для улучшения базы знаний
  - Сравнение эффективности разных версий поиска
- 🔄 Асинхронная обработка запросов, периодическая синхронизация сотрудников
- 🧭 Улучшенный UX: /status, /cancel, «повтор» после неуспешной регистрации
- 🎯 **Админ-панель**: загрузка документов, аналитика, A/B тестирование

## Архитектура

Проект разделен на два основных компонента:

### 1. **Model Service** (model_service.py):
   - FastAPI сервер для LLM (llama-cpp)
   - **Многоязычная модель эмбеддингов** Sentence-Transformers
   - **Cross-Encoder** для точного переранжирования результатов
   - **Гибридный поиск**: FAISS + BM25 + Cross-Encoder
   - **Персистентность индекса** с проверкой актуальности
   - Эндпоинты:
     - GET `/health` - статус сервиса и метрики
     - POST `/generate` - генерация ответов
     - POST `/embed` - создание эмбеддингов
     - POST `/index` - индексация массива текстов
     - POST `/search` - классический гибридный поиск
     - POST `/search_v2` - улучшенный поиск с Cross-Encoder
     - POST `/usage` - статистика использования токенов

### 2. **Telegram Bot** (bot.py):
   - Регистрация и верификация пользователей
   - **Query Expansion** для улучшения поиска
   - **A/B тестирование** версий поиска
   - Интеграция с Model Service (v1/v2 поиск + генерация)
   - **Умное разбиение документов** при загрузке
   - **Система фидбека** с кнопками оценки
   - **Расширенная аналитика** использования

## Требования

### Для Model Service:
- Python 3.8+
- NVIDIA GPU (опционально) — для ускорения указать `LLAMA_GPU_LAYERS`
- 8–24GB RAM (в зависимости от модели)
- **Новые зависимости**: scikit-learn, lightgbm, transformers, torch

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
GGUF_MODEL_PATH=/home/bot/models/saiga2_7b_q4_k_m.gguf
LLAMA_CTX=2048
LLAMA_THREADS=4
LLAMA_BATCH=256
LLAMA_GPU_LAYERS=32

# RAG Configuration
EMBEDDING_MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2
CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-12-v2
USE_SEARCH_V2=false
SEARCH_V2_PERCENTAGE=30
CONFIDENCE_THRESHOLD=0.12
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

3. Индексация для гибридного поиска (опционально через API):
```bash
curl -X POST http://localhost:8000/index \
  -H 'Content-Type: application/json' \
  -d '{"documents":["текст_документа_1","текст_документа_2"]}'
```

4. Поиск (проверка):
```bash
# Классический поиск
curl -X POST http://localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"ваш вопрос","top_k":3}'

# Улучшенный поиск с Cross-Encoder
curl -X POST http://localhost:8000/search_v2 \
  -H 'Content-Type: application/json' \
  -d '{"query":"ваш вопрос","top_k":3}'
```

### Telegram Bot:

1. Для разработки:
```bash
./dev.sh
```

2. Для production:
```bash
sudo cp telegram-bot.service /etc/systemd/system/
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

## Команды бота

### Пользовательские команды:
- `/start` — регистрация (ФИО + табельный)
- `'повтор'` — повторить попытку регистрации (кнопка появляется при ошибке)
- `/cancel` — отменить текущую операцию
- `/status` — профиль пользователя (после регистрации)
- `/ask` — задать вопрос ассистенту (после регистрации)
- `/help` — помощь (после регистрации)

### Админ-команды:
- `/train` — загрузить .docx документ; бот индексирует с умным разбиением
- `/analytics` — подробная статистика использования за 7 дней
- `/stats` — краткая статистика (алиас для analytics)
- `/compare_search` — сравнение эффективности v1 и v2 поиска (A/B тест)

## Новые возможности RAG

### 1. **Cross-Encoder переранжирование**
- Использует нейросеть для точной оценки релевантности
- Повышает точность поиска на 10-15%
- Автоматический fallback на классический поиск при ошибках

### 2. **Query Expansion**
- Автоматическое расширение запросов через LLM
- Генерация альтернативных формулировок
- Улучшает покрытие поиска для сложных вопросов

### 3. **A/B тестирование**
- Контролируемое распределение пользователей между версиями
- Автоматический анализ эффективности
- Постепенное внедрение новых методов

### 4. **Умное разбиение документов**
- Автоматическое определение типа документа (регламент, FAQ, справка)
- Извлечение метаданных (отдел, даты, тип)
- Адаптивное разбиение по структуре документа

### 5. **Система фидбека**
- Кнопки 👍👎 после каждого ответа
- Сбор статистики удовлетворённости
- Анализ качества ответов в реальном времени

### 6. **Персистентность индекса**
- Сохранение FAISS индекса на диск
- Быстрая загрузка при перезапуске
- Проверка актуальности модели эмбеддингов

## Поведение при вопросах

1. **Query Expansion**: для длинных запросов генерируются альтернативные формулировки
2. **A/B тестирование**: пользователь автоматически направляется на v1 или v2 поиск
3. **Гибридный поиск**: FAISS + BM25 + Cross-Encoder переранжирование
4. **Проверка уверенности**: если score < threshold, запрос логируется как неотвеченный
5. **Фидбек**: после ответа появляются кнопки для оценки
6. **Аналитика**: все метрики сохраняются для мониторинга

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
MONTHLY_TOKEN_LIMIT=10000000
TOKEN_ALERT_THRESHOLD=0.8

# RAG Configuration
EMBEDDING_MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2
CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-12-v2
USE_SEARCH_V2=false
SEARCH_V2_PERCENTAGE=30
CONFIDENCE_THRESHOLD=0.12

# Database
DATABASE_PATH=employees.db
# MySQL (опционально)
MYSQL_HOST=
MYSQL_PORT=3306
MYSQL_DB=
MYSQL_USER=
MYSQL_PASSWORD=
# MS SQL Server (опционально)
MSSQL_DSN=
MSSQL_HOST=
MSSQL_PORT=1433
MSSQL_DB=
MSSQL_USER=
MSSQL_PASSWORD=

# Redis
REDIS_URL=redis://localhost:6379/0

# 1C Integration
ONEC_EXPORT_PATH=

# Logging
LOG_LEVEL=INFO
```

## Мониторинг и аналитика

### 1. Логи бота:
```bash
tail -f logs/bot.log
```

### 2. Логи модели:
```bash
tail -f logs/model_service.log
```

### 3. Системные логи:
```bash
sudo journalctl -u telegram-bot -f
sudo journalctl -u model-service -f
```

### 4. Аналитика через бота:
- `/analytics` - подробная статистика за 7 дней
- `/compare_search` - сравнение версий поиска
- Автоматические уведомления при падении качества

### 5. Метрики в `/health`:
```bash
curl http://localhost:8000/health
```

## A/B тестирование

### Настройка:
```env
USE_SEARCH_V2=false           # Глобальное включение v2
SEARCH_V2_PERCENTAGE=30       # 30% пользователей на v2
```

### Мониторинг:
1. Используйте `/compare_search` для анализа
2. Следите за метриками удовлетворённости
3. Постепенно увеличивайте `SEARCH_V2_PERCENTAGE`
4. При хороших результатах ставьте `USE_SEARCH_V2=true`

## Разработка

1. Настройка окружения:
```bash
pip install -r requirements.txt
```

2. Запуск тестов (при наличии):
```bash
python -m pytest tests/
```

3. Проверка кода:
```bash
python -m py_compile main.py bot.py database.py
flake8 .
```

4. Тестирование RAG:
```bash
# Проверка индексации
curl -X POST http://localhost:8000/index -H 'Content-Type: application/json' -d '{"documents":["тестовый документ"]}'

# Проверка поиска
curl -X POST http://localhost:8000/search_v2 -H 'Content-Type: application/json' -d '{"query":"тестовый вопрос","top_k":3}'
```

## Безопасность

- Используйте .env/секрет‑хранилище для токенов и доступов
- Для БД создавайте read‑only пользователя и ограничивайте права до нужных представлений
- Фильтруйте ПДн в ответах и применяйте ACL к документам
- Мониторьте использование токенов через `/usage` эндпоинт

## Производительность

### Оптимизация для production:
1. **GPU ускорение**: настройте `LLAMA_GPU_LAYERS` и `N_GPU_LAYERS`
2. **Кеширование**: используйте Redis для состояний пользователей
3. **Мониторинг**: следите за временем ответа и качеством через аналитику
4. **Масштабирование**: запускайте несколько экземпляров model_service за балансировщиком

### Рекомендуемые настройки:
```env
LLAMA_GPU_LAYERS=32          # Для GPU
LLAMA_THREADS=8              # Для CPU
LLAMA_BATCH=512              # Увеличить для GPU
SEARCH_V2_PERCENTAGE=50      # После тестирования
```

## Лицензия

MIT

