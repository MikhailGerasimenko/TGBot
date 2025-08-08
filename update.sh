#!/bin/bash

echo "=== Обновление бота ==="

# Проверяем, запущен ли скрипт от имени правильного пользователя
if [ "$(whoami)" != "bot" ]; then
    echo "Скрипт должен быть запущен от пользователя 'bot'"
    echo "Используйте: sudo -u bot ./update.sh"
    exit 1
fi

# Активация виртуального окружения
source venv/bin/activate

# Создание бэкапа текущей версии
echo "Создание бэкапа..."
backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$backup_dir"
cp -r bot.py database.py main.py "$backup_dir/"
cp employees.db "$backup_dir/" 2>/dev/null || true

# Получение последних изменений
echo "Получение обновлений из репозитория..."
git stash  # Сохраняем локальные изменения, если есть
git pull

# Обновление зависимостей
echo "Обновление зависимостей..."
pip install -r requirements.txt

# Проверка синтаксиса Python файлов
echo "Проверка синтаксиса..."
python -m py_compile main.py bot.py database.py
if [ $? -ne 0 ]; then
    echo "❌ Ошибка в синтаксисе Python! Отмена обновления..."
    # Восстанавливаем из бэкапа
    cp "$backup_dir"/* .
    exit 1
fi

# Перезапуск сервиса
echo "Перезапуск бота..."
sudo systemctl restart telegram-bot

# Проверка статуса
echo "Проверка статуса..."
sleep 5  # Даем время на запуск
if sudo systemctl is-active --quiet telegram-bot; then
    echo "✅ Бот успешно обновлен и запущен"
    # Очистка старых бэкапов (оставляем последние 5)
    ls -dt backups/*/ | tail -n +6 | xargs rm -rf
else
    echo "❌ Ошибка запуска бота!"
    echo "Восстановление из бэкапа..."
    cp "$backup_dir"/* .
    sudo systemctl restart telegram-bot
    echo "Проверьте логи: sudo journalctl -u telegram-bot -n 50"
fi 