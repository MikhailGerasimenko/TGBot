#!/bin/bash

# Скрипт скачивания модели для GPU сервера
# Использование: ./download_model.sh [модель]

set -e

# Настройки по умолчанию
DEFAULT_MODEL="saiga2_7b_q4_k_m"
MODELS_DIR="models"

# Доступные модели
declare -A MODEL_URLS=(
    ["gigachat_20b_bf16"]="https://huggingface.co/ai-sage/GigaChat-20B-A3B-instruct-GGUF/resolve/main/GigaChat-20B-A3B-instruct-bf16.gguf"
    ["gigachat_20b_q4_k_m"]="https://huggingface.co/ai-sage/GigaChat-20B-A3B-instruct-GGUF/resolve/main/GigaChat-20B-A3B-instruct-q4_K_M.gguf"
    ["gigachat_20b_q5_k_m"]="https://huggingface.co/ai-sage/GigaChat-20B-A3B-instruct-GGUF/resolve/main/GigaChat-20B-A3B-instruct-q5_K_M.gguf"
    ["gigachat_20b_q8_0"]="https://huggingface.co/ai-sage/GigaChat-20B-A3B-instruct-GGUF/resolve/main/GigaChat-20B-A3B-instruct-q8_0.gguf"
    ["saiga2_7b_q4_k_m"]="https://huggingface.co/IlyaGusev/saiga2_7b_gguf/resolve/main/model-q4_k_m.gguf"
    ["saiga2_7b_q5_k_m"]="https://huggingface.co/IlyaGusev/saiga2_7b_gguf/resolve/main/model-q5_k_m.gguf"
    ["saiga2_7b_q8_0"]="https://huggingface.co/IlyaGusev/saiga2_7b_gguf/resolve/main/model-q8_0.gguf"
    ["llama2_7b_q4_k_m"]="https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf"
    ["mistral_7b_q4_k_m"]="https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
)

# Функция для отображения доступных моделей
show_models() {
    echo "📋 Доступные модели:"
    echo ""
    echo "🚀 РЕКОМЕНДУЕМЫЕ (для GPU):"
    echo "  • gigachat_20b_bf16 - МАКСИМАЛЬНАЯ СКОРОСТЬ, 41.2GB RAM"
    echo "  • gigachat_20b_q4_k_m - ЛУЧШАЯ для русского языка, 12.5GB RAM"
    echo "  • gigachat_20b_q5_k_m - Максимальное качество, 14.6GB RAM"
    echo ""
    echo "⚡ БЫСТРЫЕ (для CPU/мало RAM):"
    echo "  • saiga2_7b_q4_k_m - Хорошая для русского, 4GB RAM"
    echo "  • saiga2_7b_q5_k_m - Лучше качество, 5GB RAM"
    echo "  • mistral_7b_q4_k_m - Хорошая альтернатива, 4GB RAM"
    echo ""
    echo "💡 Рекомендации по GPU памяти:"
    echo "  • 8GB GPU: saiga2_7b_q4_k_m"
    echo "  • 12GB GPU: gigachat_20b_q4_k_m"
    echo "  • 16GB+ GPU: gigachat_20b_q5_k_m"
    echo "  • 40GB+ GPU: gigachat_20b_bf16 (МАКСИМАЛЬНАЯ СКОРОСТЬ)"
}

# Проверяем аргументы
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_models
    exit 0
fi

# Выбираем модель
SELECTED_MODEL=${1:-$DEFAULT_MODEL}

if [ ! "${MODEL_URLS[$SELECTED_MODEL]}" ]; then
    echo "❌ Неизвестная модель: $SELECTED_MODEL"
    echo ""
    show_models
    exit 1
fi

# Проверяем GPU память
echo "🔍 Проверяем GPU память..."
if command -v nvidia-smi &> /dev/null; then
    GPU_MEMORY=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
    echo "✅ GPU память: ${GPU_MEMORY}MB"
    
    # Рекомендации по модели
    if [ "$GPU_MEMORY" -lt 8000 ]; then
        echo "⚠️  Мало GPU памяти. Рекомендуется модель с q4_k_m."
    elif [ "$GPU_MEMORY" -lt 12000 ]; then
        echo "✅ Достаточно памяти для большинства моделей."
    else
        echo "🚀 Много GPU памяти! Можно использовать качественные модели."
    fi
else
    echo "⚠️  GPU не найден, будет использоваться CPU."
fi

# Создаем директорию для моделей
mkdir -p $MODELS_DIR
cd $MODELS_DIR

# Определяем имя файла
MODEL_FILENAME="model-${SELECTED_MODEL}.gguf"

echo "📥 Скачиваем модель: $SELECTED_MODEL"
echo "🔗 URL: ${MODEL_URLS[$SELECTED_MODEL]}"
echo "📁 Файл: $MODEL_FILENAME"
echo ""

# Скачиваем модель
echo "⏳ Начинаем скачивание..."
wget -O "$MODEL_FILENAME" "${MODEL_URLS[$SELECTED_MODEL]}"

# Проверяем размер файла
FILE_SIZE=$(du -h "$MODEL_FILENAME" | cut -f1)
echo "✅ Модель скачана: $MODEL_FILENAME ($FILE_SIZE)"

# Создаем символическую ссылку для совместимости
ln -sf "$MODEL_FILENAME" "model-q2_k.gguf"

echo ""
echo "🔧 Обновляем .env файл..."
cd ..

# Обновляем .env файл
if [ -f .env ]; then
    # Создаем резервную копию
    cp .env .env.backup
    
    # Обновляем путь к модели
    sed -i "s|GGUF_MODEL_PATH=.*|GGUF_MODEL_PATH=$MODELS_DIR/$MODEL_FILENAME|g" .env
    
    echo "✅ .env файл обновлен"
    echo "📝 Путь к модели: $MODELS_DIR/$MODEL_FILENAME"
else
    echo "⚠️  .env файл не найден. Создайте его из env.example"
fi

echo ""
echo "🎉 Модель успешно установлена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Проверьте настройки в .env файле"
echo "2. Запустите model-service:"
echo "   sudo systemctl start model-service"
echo "3. Проверьте статус:"
echo "   sudo systemctl status model-service"
echo "4. Проверьте логи:"
echo "   sudo journalctl -u model-service -f"
echo ""
echo "🧪 Тестирование модели:"
echo "   python test_lama.py" 