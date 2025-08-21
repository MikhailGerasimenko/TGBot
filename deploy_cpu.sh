#!/bin/bash

# Скрипт развертывания корпоративного бота на CPU сервере
# Оптимизирован для работы без GPU

set -e

echo "🚀 Развертывание корпоративного бота на CPU сервере"
echo "=================================================="

# Проверяем систему
echo "🔍 Проверяем систему..."
echo "ОС: $(lsb_release -d | cut -f2)"
echo "CPU: $(nproc) ядер"
echo "RAM: $(free -h | awk 'NR==2{print $2}')"

# Обновляем систему
echo "📦 Обновляем систему..."
sudo apt update && sudo apt upgrade -y

# Устанавливаем необходимые пакеты
echo "🔧 Устанавливаем зависимости..."
sudo apt install -y python3 python3-pip python3-venv git curl wget htop

# Создаем директорию проекта
PROJECT_DIR="/opt/corporate-bot"
echo "📁 Создаем директорию проекта: $PROJECT_DIR"
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR

# Копируем файлы проекта (если еще не скопированы)
if [ ! -f "$PROJECT_DIR/bot.py" ]; then
    echo "📋 Копируем файлы проекта..."
    cp -r . $PROJECT_DIR/
fi
cd $PROJECT_DIR

# Создаем виртуальное окружение
echo "🐍 Создаем виртуальное окружение..."
python3 -m venv venv
source venv/bin/activate

# Обновляем pip
pip install --upgrade pip

# Устанавливаем PyTorch CPU версию
echo "🔥 Устанавливаем PyTorch CPU версию..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Устанавливаем зависимости
echo "📚 Устанавливаем зависимости..."
pip install -r requirements.txt

# Устанавливаем llama-cpp-python без GPU
echo "🧠 Устанавливаем llama-cpp-python (CPU версия)..."
pip install llama-cpp-python

# Создаем необходимые директории
echo "📂 Создаем директории..."
mkdir -p models documents logs backups

# Копируем конфигурацию
if [ ! -f .env ]; then
    echo "⚙️  Создаем конфигурацию..."
    cp env.example .env
    echo "📝 Отредактируйте .env файл с вашими настройками:"
    echo "   nano $PROJECT_DIR/.env"
fi

# Создаем CPU оптимизированную конфигурацию
echo "⚙️  Создаем CPU оптимизированную конфигурацию..."
cat > cpu_config.env << 'EOF'
# Оптимальные настройки для CPU сервера
# Скопируйте эти настройки в .env файл

# Telegram Bot Configuration
API_TOKEN=your_telegram_bot_token_here
ADMIN_CHAT_ID=your_admin_telegram_id

# Model Service Configuration (оптимизировано для CPU)
MODEL_SERVICE_URL=http://localhost:8000
GGUF_MODEL_PATH=models/model-saiga2_7b_q4_k_m.gguf

# CPU оптимизированные настройки
LLAMA_CTX=4096                    # Стандартный контекст для CPU
LLAMA_THREADS=8                   # Оптимальное количество потоков
LLAMA_BATCH=512                   # Стандартный батч для CPU
LLAMA_GPU_LAYERS=0                # Без GPU слоев
MAX_NEW_TOKENS=1024               # Стандартное количество токенов
MONTHLY_TOKEN_LIMIT=10000000
TOKEN_ALERT_THRESHOLD=0.8

# RAG Configuration (оптимизировано для CPU)
EMBEDDING_MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2
CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-12-v2
USE_SEARCH_V2=true                # Включаем улучшенный поиск
SEARCH_V2_PERCENTAGE=100          # Все пользователи на v2
CONFIDENCE_THRESHOLD=0.15         # Стандартный порог

# Database Configuration
DATABASE_PATH=employees.db

# MySQL (Optional)
MYSQL_HOST=
MYSQL_PORT=3306
MYSQL_DB=
MYSQL_USER=
MYSQL_PASSWORD=

# MS SQL Server (Optional)
MSSQL_DSN=
MSSQL_HOST=
MSSQL_PORT=1433
MSSQL_DB=
MSSQL_USER=
MSSQL_PASSWORD=

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# 1C Integration
ONEC_EXPORT_PATH=

# Logging
LOG_LEVEL=INFO

# CPU оптимизация
OMP_NUM_THREADS=8                 # Количество OpenMP потоков
MKL_NUM_THREADS=8                 # Количество MKL потоков
EOF

# Создаем systemd сервисы
echo "🔧 Создаем systemd сервисы..."

# Model Service
sudo tee /etc/systemd/system/model-service.service > /dev/null <<EOF
[Unit]
Description=Corporate Bot Model Service (CPU)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
Environment=OMP_NUM_THREADS=8
Environment=MKL_NUM_THREADS=8
ExecStart=$PROJECT_DIR/venv/bin/python model_service.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Telegram Bot Service
sudo tee /etc/systemd/system/telegram-bot.service > /dev/null <<EOF
[Unit]
Description=Corporate Telegram Bot (CPU)
After=network.target model-service.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Перезагружаем systemd
echo "🔄 Перезагружаем systemd..."
sudo systemctl daemon-reload

echo "✅ Развертывание на CPU завершено!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Отредактируйте конфигурацию:"
echo "   nano $PROJECT_DIR/.env"
echo ""
echo "2. Скачайте модель (рекомендуется Saiga2 для CPU):"
echo "   cd $PROJECT_DIR"
echo "   ./download_model.sh saiga2_7b_q4_k_m"
echo ""
echo "3. Протестируйте модель:"
echo "   python test_lama.py"
echo ""
echo "4. Запустите сервисы:"
echo "   sudo systemctl start model-service"
echo "   sudo systemctl start telegram-bot"
echo ""
echo "5. Проверьте статус:"
echo "   sudo systemctl status model-service"
echo "   sudo systemctl status telegram-bot"
echo ""
echo "6. Включите автозапуск:"
echo "   sudo systemctl enable model-service"
echo "   sudo systemctl enable telegram-bot"
echo ""
echo "💡 Рекомендации для CPU:"
echo "• Используйте Saiga2-7B вместо GigaChat-20B"
echo "• Модель будет работать медленнее, но стабильно"
echo "• Мониторинг: htop, iotop" 