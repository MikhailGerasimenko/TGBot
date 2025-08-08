from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import numpy as np
from sentence_transformers import SentenceTransformer
import logging
import uvicorn
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/model_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
MODEL_NAME = "IlyaGusev/saiga2_7b_gguf"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MAX_LENGTH = 2048
MAX_NEW_TOKENS = 512
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Создаем FastAPI приложение
app = FastAPI(title="LLM Service")

# Модели данных
class GenerateRequest(BaseModel):
    query: str
    context: Optional[str] = ""
    max_tokens: Optional[int] = MAX_NEW_TOKENS
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.95

class EmbeddingRequest(BaseModel):
    texts: List[str]

class GenerateResponse(BaseModel):
    response: str
    generation_time: float

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    embedding_time: float

# Глобальные переменные для моделей
llm = None
tokenizer = None
embedding_model = None

@app.on_event("startup")
async def load_models():
    """Загрузка моделей при старте сервиса"""
    global llm, tokenizer, embedding_model
    
    try:
        logger.info("Загрузка моделей...")
        
        # Загрузка основной модели
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME,
            trust_remote_code=True
        )
        llm = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            device_map="auto" if DEVICE == "cuda" else None,
            trust_remote_code=True
        )
        
        # Загрузка модели для эмбеддингов
        embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        if DEVICE == "cuda":
            embedding_model.to(DEVICE)
            
        logger.info("Модели успешно загружены")
    except Exception as e:
        logger.error(f"Ошибка при загрузке моделей: {e}")
        raise

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "ok",
        "models_loaded": all([llm, tokenizer, embedding_model]),
        "device": DEVICE,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    }

@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Генерация ответа с помощью LLM"""
    try:
        start_time = datetime.now()
        
        # Формируем промпт
        system_prompt = """Ты — корпоративный ассистент. Отвечай на вопросы, используя предоставленный контекст.
        Если информации в контексте недостаточно, так и скажи. Отвечай кратко и по делу."""
        
        if request.context:
            prompt = f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\nКонтекст:\n{request.context}\n\nВопрос: {request.query} [/INST]"
        else:
            prompt = f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\nВопрос: {request.query} [/INST]"
        
        # Токенизируем
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=MAX_LENGTH)
        if DEVICE == "cuda":
            inputs = inputs.to(DEVICE)
        
        # Генерируем ответ
        with torch.no_grad():
            outputs = llm.generate(
                **inputs,
                max_new_tokens=request.max_tokens,
                do_sample=True,
                temperature=request.temperature,
                top_p=request.top_p,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # Декодируем ответ
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Очищаем ответ от промпта
        response = response.split("[/INST]")[-1].strip()
        
        generation_time = (datetime.now() - start_time).total_seconds()
        
        return GenerateResponse(
            response=response,
            generation_time=generation_time
        )
    except Exception as e:
        logger.error(f"Ошибка при генерации ответа: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed", response_model=EmbeddingResponse)
async def embed(request: EmbeddingRequest):
    """Создание эмбеддингов для текстов"""
    try:
        start_time = datetime.now()
        
        # Создаем эмбеддинги
        embeddings = embedding_model.encode(request.texts)
        
        # Конвертируем в список (для JSON)
        embeddings_list = embeddings.tolist()
        
        embedding_time = (datetime.now() - start_time).total_seconds()
        
        return EmbeddingResponse(
            embeddings=embeddings_list,
            embedding_time=embedding_time
        )
    except Exception as e:
        logger.error(f"Ошибка при создании эмбеддингов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "model_service:app",
        host="0.0.0.0",
        port=8000,
        workers=1  # Для работы с GPU лучше использовать один воркер
    ) 