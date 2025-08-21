#!/bin/bash

# Скрипт для удаленного развертывания на сервер
# Использование: ./deploy_remote.sh

set -e

# Конфигурация сервера
SERVER_IP="217.150.197.135"
SERVER_USER="user"
SERVER_PATH="/opt/corporate-bot"

echo "🚀 Удаленное развертывание корпоративного бота"
echo "============================================="
echo "Сервер: $SERVER_USER@$SERVER_IP"
echo "Путь: $SERVER_PATH"
echo ""

# Проверяем подключение к серверу
echo "🔍 Проверяем подключение к серверу..."
if ! ssh -o ConnectTimeout=10 $SERVER_USER@$SERVER_IP "echo 'Подключение успешно'" 2>/dev/null; then
    echo "❌ Не удалось подключиться к серверу"
    echo "Проверьте:"
    echo "• IP адрес: $SERVER_IP"
    echo "• Пользователя: $SERVER_USER"
    echo "• Пароль: b%z4goF"
    echo "• Сетевое подключение"
    exit 1
fi

echo "✅ Подключение к серверу успешно!"

# Создаем временную директорию на сервере
echo "📁 Создаем временную директорию на сервере..."
ssh $SERVER_USER@$SERVER_IP "mkdir -p /tmp/corporate-bot-deploy"

# Копируем файлы проекта (исключая большие файлы)
echo "📋 Копируем файлы проекта..."
rsync -av --progress \
    --exclude='.env' \
    --exclude='models/*.gguf' \
    --exclude='models/*.bin' \
    --exclude='*.db' \
    --exclude='venv/' \
    --exclude='__pycache__/' \
    --exclude='logs/' \
    --exclude='.git/' \
    . $SERVER_USER@$SERVER_IP:/tmp/corporate-bot-deploy/

# Перемещаем файлы в рабочую директорию
echo "📂 Перемещаем файлы в рабочую директорию..."
ssh $SERVER_USER@$SERVER_IP "sudo mkdir -p $SERVER_PATH && sudo mv /tmp/corporate-bot-deploy/* $SERVER_PATH/ && sudo chown -R $SERVER_USER:$SERVER_USER $SERVER_PATH"

# Запускаем развертывание на сервере
echo "🔧 Запускаем развертывание на сервере..."
ssh $SERVER_USER@$SERVER_IP "cd $SERVER_PATH && chmod +x deploy_gpu.sh && ./deploy_gpu.sh"

echo "✅ Удаленное развертывание завершено!"
echo ""
echo "📋 Следующие шаги на сервере:"
echo "1. Подключитесь: ssh $SERVER_USER@$SERVER_IP"
echo "2. Перейдите в директорию: cd $SERVER_PATH"
echo "3. Настройте конфигурацию: nano .env"
echo "4. Скачайте модель: ./download_model.sh gigachat_20b_q4_k_m"
echo "5. Протестируйте: python test_gigachat.py"
echo "6. Запустите сервисы:"
echo "   sudo systemctl start model-service"
echo "   sudo systemctl start telegram-bot" 