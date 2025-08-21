# 🐳 Docker развертывание корпоративного бота

Полное руководство по развертыванию корпоративного AI-ассистента в Docker контейнерах.

## 📋 Содержание

- [Обзор](#обзор)
- [Требования](#требования)
- [Быстрый старт](#быстрый-старт)
- [Конфигурация](#конфигурация)
- [Управление](#управление)
- [Мониторинг](#мониторинг)
- [Troubleshooting](#troubleshooting)

## 🎯 Обзор

Docker развертывание включает в себя:

- **Model Service** - LLM сервис с поддержкой GPU
- **Telegram Bot** - основной бот
- **Nginx** - обратный прокси и балансировщик нагрузки
- **Redis** - кэширование и сессии
- **Grafana** - мониторинг (GPU версия)

### Архитектура Docker

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx         │    │   Grafana       │    │   Redis         │
│   (Port 80/443) │    │   (Port 3000)   │    │   (Port 6379)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Model Service │    │   Telegram Bot  │    │   Volumes       │
│   (Port 8000)   │◄──►│   (Internal)    │◄──►│   (Data/Models) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## ⚙️ Требования

### Системные требования

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **NVIDIA Container Toolkit** (для GPU версии)
- **4GB+ RAM** (8GB+ для GPU)
- **50GB+ свободного места**

### Для GPU версии

```bash
# Установка NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# Проверка установки
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi
```

## 🚀 Быстрый старт

### 1. Подготовка

```bash
# Клонирование репозитория
git clone <repository-url>
cd corporate-bot

# Настройка окружения
cp env.example .env
nano .env  # Настройте API_TOKEN и ADMIN_CHAT_ID
```

### 2. Скачивание модели

```bash
# Для CPU версии
./download_model.sh gigachat_20b_q8_0

# Для GPU версии (рекомендуется)
./download_model.sh gigachat_20b_bf16
```

### 3. Запуск

```bash
# CPU версия
cd docker/scripts
chmod +x deploy.sh manage.sh
./deploy.sh cpu

# GPU версия
./deploy.sh gpu
```

### 4. Проверка

```bash
# Статус сервисов
./manage.sh status

# Логи
./manage.sh logs
```

## ⚙️ Конфигурация

### Переменные окружения

Создайте файл `.env` в корневой директории:

```bash
# Telegram Bot
API_TOKEN=your_telegram_bot_token
ADMIN_CHAT_ID=your_admin_telegram_id

# Model Service
GGUF_MODEL_PATH=models/model-gigachat_20b_bf16.gguf
LLAMA_CTX=8192
LLAMA_THREADS=16
LLAMA_BATCH=1024
LLAMA_GPU_LAYERS=80
MAX_NEW_TOKENS=512

# RAG System
EMBEDDING_MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2
CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-12-v2

# Database
DATABASE_PATH=data/employees.db

# GPU Optimization
CUDA_VISIBLE_DEVICES=0
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024
```

### Оптимизация производительности

#### CPU версия
```yaml
# docker-compose.yml
environment:
  - LLAMA_GPU_LAYERS=0
  - LLAMA_CTX=4096
  - LLAMA_THREADS=8
  - LLAMA_BATCH=512
```

#### GPU версия
```yaml
# docker-compose.gpu.yml
environment:
  - LLAMA_GPU_LAYERS=80
  - LLAMA_CTX=8192
  - LLAMA_THREADS=16
  - LLAMA_BATCH=1024
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

## 🎮 Управление

### Основные команды

```bash
# Запуск
./manage.sh start

# Остановка
./manage.sh stop

# Перезапуск
./manage.sh restart

# Статус
./manage.sh status

# Логи
./manage.sh logs
./manage.sh logs model-service
./manage.sh logs telegram-bot

# Обновление
./manage.sh update

# Резервное копирование
./manage.sh backup

# Восстановление
./manage.sh restore backup_file.tar.gz
```

### Прямые команды Docker

```bash
# Просмотр контейнеров
docker ps

# Логи конкретного сервиса
docker logs corporate-bot-model -f

# Вход в контейнер
docker exec -it corporate-bot-model bash

# Перезапуск сервиса
docker restart corporate-bot-model

# Мониторинг ресурсов
docker stats
```

## 📊 Мониторинг

### Health Checks

```bash
# Model Service
curl http://localhost:8000/health

# Nginx
curl http://localhost:80

# Redis
docker exec corporate-bot-redis redis-cli ping
```

### Grafana (GPU версия)

- **URL:** http://localhost:3000
- **Логин:** admin
- **Пароль:** admin

### Метрики

```bash
# GPU использование
nvidia-smi

# Использование памяти
docker stats

# Логи в реальном времени
./manage.sh logs -f
```

## 🔧 Troubleshooting

### Частые проблемы

#### 1. Модель не загружается

```bash
# Проверка GPU
nvidia-smi

# Проверка модели
ls -la models/

# Логи model service
./manage.sh logs model-service

# Перезапуск
./manage.sh restart
```

#### 2. Медленная генерация

```bash
# Проверка настроек GPU
docker exec corporate-bot-model nvidia-smi

# Оптимизация параметров в .env
LLAMA_GPU_LAYERS=80
LLAMA_CTX=8192
LLAMA_THREADS=16
```

#### 3. Ошибки подключения

```bash
# Проверка портов
netstat -tlnp | grep :8000
netstat -tlnp | grep :80

# Проверка контейнеров
docker ps

# Перезапуск сети
docker network prune
./manage.sh restart
```

#### 4. Проблемы с памятью

```bash
# Очистка Docker
docker system prune -a

# Проверка использования диска
df -h

# Очистка логов
docker system prune -f
```

### Отладка

```bash
# Включение debug режима
export LOG_LEVEL=DEBUG
./manage.sh restart

# Проверка конфигурации
docker exec corporate-bot-model python -c "from config import *; print('Config OK')"

# Тест API
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "max_tokens": 10}'
```

### Логи

```bash
# Все логи
./manage.sh logs

# Логи конкретного сервиса
./manage.sh logs model-service

# Логи с временными метками
docker logs corporate-bot-model --timestamps

# Логи последних 100 строк
docker logs corporate-bot-model --tail 100
```

## 📁 Структура файлов

```
docker/
├── Dockerfile.bot              # Образ Telegram бота
├── Dockerfile.model            # Образ LLM сервиса
├── docker-compose.yml          # CPU версия
├── docker-compose.gpu.yml      # GPU версия
├── nginx.conf                  # Конфигурация Nginx
├── scripts/
│   ├── deploy.sh               # Скрипт деплоя
│   └── manage.sh               # Управление сервисами
└── README.md                   # Эта документация
```

## 🔄 Обновления

### Обновление кода

```bash
# Остановка сервисов
./manage.sh stop

# Обновление из git
git pull origin main

# Пересборка и запуск
./manage.sh update
```

### Обновление модели

```bash
# Скачивание новой модели
./download_model.sh gigachat_20b_bf16

# Обновление .env
nano .env  # Измените GGUF_MODEL_PATH

# Перезапуск
./manage.sh restart
```

## 📞 Поддержка

### Полезные команды

```bash
# Полная диагностика
./manage.sh status
nvidia-smi
docker stats
df -h

# Очистка системы
docker system prune -a
docker volume prune
```

### Контакты

- **Разработчик:** [Ваше имя]
- **Email:** [email]
- **Telegram:** [username]

---

**Версия Docker:** 1.0.0  
**Последнее обновление:** 2025-01-19 