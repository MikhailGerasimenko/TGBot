#!/bin/bash

# Скрипт для безопасного обновления GitHub репозитория
# Исключает конфиденциальные данные (.env, модели, БД)

set -e

echo "🔄 Безопасное обновление GitHub репозитория"
echo "=========================================="

# Проверяем наличие .git
if [ ! -d ".git" ]; then
    echo "❌ Это не Git репозиторий. Инициализируем..."
    git init
    git remote add origin https://github.com/MikhailGerasimenko/TGBot.git
fi

# Проверяем .gitignore
if [ ! -f ".gitignore" ]; then
    echo "❌ .gitignore не найден. Создаем..."
    cat > .gitignore << 'EOF'
# Конфиденциальные данные
.env
*.env
config.env
gpu_config.env

# Базы данных
*.db
*.sqlite
*.sqlite3

# Логи
logs/
*.log

# Модели (большие файлы)
models/*.gguf
models/*.bin
models/*.safetensors

# Индексы поиска
models/search_index.pkl
models/faiss_index/

# Документы
documents/
*.docx
*.pdf
*.txt

# Виртуальное окружение
venv/
env/
.venv/

# Кэш Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so

# IDE
.vscode/
.idea/
*.swp
*.swo

# Системные файлы
.DS_Store
Thumbs.db

# Временные файлы
*.tmp
*.temp
.cache/

# Резервные копии
backups/
*.bak
*.backup
EOF
fi

# Проверяем, что .env не в Git
if git ls-files | grep -q "\.env"; then
    echo "⚠️  ВНИМАНИЕ: .env файл уже в Git! Удаляем..."
    git rm --cached .env
    echo "✅ .env удален из Git (остался локально)"
fi

# Добавляем все файлы (кроме .gitignore)
echo "📋 Добавляем файлы в Git..."
git add .

# Проверяем статус
echo "📊 Статус Git:"
git status

# Создаем коммит
echo "💾 Создаем коммит..."
read -p "Введите сообщение коммита (или нажмите Enter для авто): " commit_message
if [ -z "$commit_message" ]; then
    commit_message="Update: $(date '+%Y-%m-%d %H:%M:%S')"
fi

git commit -m "$commit_message"

# Отправляем на GitHub
echo "🚀 Отправляем на GitHub..."
git push origin main

echo "✅ Обновление завершено!"
echo ""
echo "🔒 Безопасность:"
echo "• .env файл НЕ отправлен на GitHub"
echo "• Модели НЕ отправлены на GitHub"
echo "• База данных НЕ отправлена на GitHub"
echo ""
echo "📝 Для развертывания на сервере:"
echo "1. Скопируйте файлы: scp -r . user@server:/opt/corporate-bot/"
echo "2. Создайте .env на сервере с вашими токенами"
echo "3. Скачайте модель: ./download_model.sh gigachat_20b_q4_k_m" 