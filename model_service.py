from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
import uvicorn
from datetime import datetime
from sentence_transformers import SentenceTransformer
import numpy as np
import os
from config import GGUF_MODEL_PATH, LOGS_DIR

# llama-cpp-python для GGUF
from llama_cpp import Llama

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'model_service.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
MODEL_PATH = GGUF_MODEL_PATH
N_CTX = int(os.getenv('LLAMA_CTX', '2048'))
N_THREADS = int(os.getenv('LLAMA_THREADS', '4'))
N_BATCH = int(os.getenv('LLAMA_BATCH', '256'))
N_GPU_LAYERS = int(os.getenv('LLAMA_GPU_LAYERS', '32'))
MAX_NEW_TOKENS = int(os.getenv('MAX_NEW_TOKENS', '512'))
EMBEDDING_MODEL_NAME = os.getenv('EMBEDDING_MODEL_NAME', 'sentence-transformers/all-MiniLM-L6-v2')

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
llm: Optional[Llama] = None
embedding_model: Optional[SentenceTransformer] = None

@app.on_event("startup")
async def load_models():
    """Загрузка моделей при старте сервиса"""
    global llm, embedding_model
    try:
        logger.info("Загрузка GGUF модели через llama-cpp...")
        llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=N_CTX,
            n_threads=N_THREADS,
            n_batch=N_BATCH,
            n_gpu_layers=N_GPU_LAYERS,
            verbose=False
        )

        logger.info("Загрузка модели эмбеддингов...")
        embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info("Модели успешно загружены")
    except Exception as e:
        logger.error(f"Ошибка при загрузке моделей: {e}")
        raise

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "ok",
        "models_loaded": all([llm is not None, embedding_model is not None]),
        "model_path": MODEL_PATH,
        "ctx": N_CTX,
        "gpu_layers": N_GPU_LAYERS
    }

@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Генерация ответа с помощью LLM"""
    try:
        start_time = datetime.now()

        # Формат промпта Saiga 2
        if request.context:
            prompt = f"<s>[INST] <<SYS>>\nТы — корпоративный ассистент. Отвечай на вопросы, используя предоставленный контекст.\nЕсли информации в контексте недостаточно, так и скажи. Отвечай кратко и по делу.\n<</SYS>>\n\nКонтекст:\n{request.context}\n\nВопрос: {request.query} [/INST]"
        else:
            prompt = f"<s>[INST] <<SYS>>\nТы — корпоративный ассистент. Отвечай на вопросы, используя предоставленный контекст.\nЕсли информации в контексте недостаточно, так и скажи. Отвечай кратко и по делу.\n<</SYS>>\n\nВопрос: {request.query} [/INST]"

        result = llm(
            prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            echo=False
        )

        # Декодирование ответа llama-cpp
        text = ""
        if result and "choices" in result and len(result["choices"]) > 0:
            text = result["choices"][0]["text"].strip()

        generation_time = (datetime.now() - start_time).total_seconds()
        return GenerateResponse(response=text, generation_time=generation_time)
    except Exception as e:
        logger.error(f"Ошибка при генерации ответа: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed", response_model=EmbeddingResponse)
async def embed(request: EmbeddingRequest):
    """Создание эмбеддингов для текстов"""
    try:
        start_time = datetime.now()
        embeddings = embedding_model.encode(request.texts)
        embedding_time = (datetime.now() - start_time).total_seconds()
        return EmbeddingResponse(embeddings=embeddings.tolist(), embedding_time=embedding_time)
    except Exception as e:
        logger.error(f"Ошибка при создании эмбеддингов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "model_service:app",
        host="0.0.0.0",
        port=8000,
        workers=1
    ) 