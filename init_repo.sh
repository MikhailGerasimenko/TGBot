#!/bin/bash

echo "=== Инициализация Git репозитория ==="

# Проверка наличия git
if ! command -v git &> /dev/null; then
    echo "Git не установлен. Установите git и попробуйте снова."
    exit 1
fi

# Инициализация репозитория
echo "Инициализация репозитория..."
git init

# Создание .gitignore если его нет
if [ ! -f .gitignore ]; then
    echo "Создание .gitignore..."
    cp env.example .env
fi

# Добавление файлов
echo "Добавление файлов..."
git add .

# Первый коммит
echo "Создание первого коммита..."
git commit -m "Initial commit"

# Запрос URL репозитория
echo "Введите URL вашего GitHub репозитория (например, https://github.com/username/repo.git):"
read repo_url

# Добавление удаленного репозитория
if [ ! -z "$repo_url" ]; then
    echo "Добавление удаленного репозитория..."
    git remote add origin $repo_url
    
    echo "Отправка кода на GitHub..."
    git push -u origin main
    
    echo "✅ Репозиторий успешно инициализирован и код отправлен на GitHub!"
else
    echo "URL репозитория не указан. Вы можете добавить его позже командой:"
    echo "git remote add origin <url>"
    echo "git push -u origin main"
fi

echo "
Следующие шаги:
1. Проверьте код на GitHub
2. Настройте защиту ветки main
3. Добавьте соавторов в репозиторий
4. Настройте CI/CD (при необходимости)
" 