#!/bin/bash

# Скрипт развертывания корпоративного бота на GPU сервере
# Копирует локальные файлы вместо клонирования с GitHub

set -e

echo "🚀 Развертывание корпоративного бота на GPU сервере"
echo "=================================================="

# Проверяем наличие NVIDIA GPU
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ NVIDIA GPU не обнаружена. Установите драйверы NVIDIA."
    exit 1
fi

echo "✅ NVIDIA GPU обнаружена:"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits

# Обновляем систему
echo "📦 Обновляем систему..."
sudo apt update && sudo apt upgrade -y

# Устанавливаем необходимые пакеты
echo "🔧 Устанавливаем зависимости..."
sudo apt install -y python3 python3-pip python3-venv git curl wget htop nvtop

# Создаем директорию проекта
PROJECT_DIR="/opt/corporate-bot"
echo "📁 Создаем директорию проекта: $PROJECT_DIR"
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR

# Копируем файлы проекта (вместо клонирования)
echo "📋 Копируем файлы проекта..."
cp -r . $PROJECT_DIR/
cd $PROJECT_DIR

# Создаем виртуальное окружение
echo "🐍 Создаем виртуальное окружение..."
python3 -m venv venv
source venv/bin/activate

# Обновляем pip
pip install --upgrade pip

# Устанавливаем PyTorch с CUDA
echo "🔥 Устанавливаем PyTorch с CUDA..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Устанавливаем зависимости
echo "📚 Устанавливаем зависимости..."
pip install -r requirements.txt

# Устанавливаем llama-cpp-python с CUBLAS
echo "🧠 Устанавливаем llama-cpp-python с GPU поддержкой..."
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python

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

# Создаем systemd сервисы
echo "🔧 Создаем systemd сервисы..."

# Model Service
sudo tee /etc/systemd/system/model-service.service > /dev/null <<EOF
[Unit]
Description=Corporate Bot Model Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python model_service.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Telegram Bot Service
sudo tee /etc/systemd/system/telegram-bot.service > /dev/null <<EOF
[Unit]
Description=Corporate Telegram Bot
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

echo "✅ Развертывание завершено!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Отредактируйте конфигурацию:"
echo "   nano $PROJECT_DIR/.env"
echo ""
echo "2. Скачайте модель:"
echo "   cd $PROJECT_DIR"
echo "   ./download_model.sh gigachat_20b_q4_k_m"
echo ""
echo "3. Протестируйте модель:"
echo "   python test_gigachat.py"
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