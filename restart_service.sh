#!/bin/bash

echo "🔄 Принудительный перезапуск model_service..."

# Останавливаем все процессы
echo "🛑 Останавливаем процессы..."
pkill -f model_service
pkill -f "python.*model_service"
sleep 3

# Проверяем что остановились
if pgrep -f model_service > /dev/null; then
    echo "❌ Процессы не остановились, принудительно убиваем..."
    pkill -9 -f model_service
    sleep 2
fi

# Проверяем что порт свободен
if lsof -i :8000 > /dev/null 2>&1; then
    echo "❌ Порт 8000 все еще занят"
    lsof -i :8000
    exit 1
fi

echo "✅ Процессы остановлены"

# Запускаем заново
echo "🚀 Запускаем model_service..."
cd /opt/corporate-bot
python3 model_service.py &
SERVICE_PID=$!

echo "⏳ Ждем загрузки..."
sleep 30

# Проверяем что запустился
if ! kill -0 $SERVICE_PID 2>/dev/null; then
    echo "❌ Сервис не запустился"
    exit 1
fi

echo "✅ Сервис запущен (PID: $SERVICE_PID)"

# Проверяем health
echo "🏥 Проверяем health..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Health check прошел"
else
    echo "❌ Health check не прошел"
    exit 1
fi

echo "🎉 Перезапуск завершен успешно!" 