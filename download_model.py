import os
import logging
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from bot import MODEL_NAME, DEVICE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_model():
    """Загрузка модели из Hugging Face"""
    try:
        logger.info(f"Загрузка модели {MODEL_NAME}...")
        
        # Проверяем наличие GPU
        if torch.cuda.is_available():
            logger.info(f"Найден GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"Доступная память GPU: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
        else:
            logger.warning("GPU не найден, будет использован CPU")
        
        # Загружаем токенизатор
        logger.info("Загрузка токенизатора...")
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME,
            trust_remote_code=True
        )
        tokenizer.save_pretrained("models/tokenizer")
        logger.info("Токенизатор сохранен")
        
        # Загружаем модель
        logger.info("Загрузка модели...")
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            trust_remote_code=True
        )
        model.save_pretrained("models/llm")
        logger.info("Модель сохранена")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при загрузке модели: {e}")
        return False

if __name__ == "__main__":
    # Создаем директорию для моделей
    os.makedirs("models/tokenizer", exist_ok=True)
    os.makedirs("models/llm", exist_ok=True)
    
    if download_model():
        print("\n✅ Модель успешно загружена и сохранена")
        print("   Путь к токенизатору: models/tokenizer")
        print("   Путь к модели: models/llm")
    else:
        print("\n❌ Ошибка при загрузке модели") 