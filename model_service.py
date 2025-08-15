from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
import uvicorn
from datetime import datetime
from sentence_transformers import SentenceTransformer, util, CrossEncoder
import numpy as np
import os
import pickle
import hashlib
from config import GGUF_MODEL_PATH, LOGS_DIR

# llama-cpp-python для GGUF
from llama_cpp import Llama

# Дополнительно: FAISS и BM25
import faiss  # type: ignore
from rank_bm25 import BM25Okapi

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
EMBEDDING_MODEL_NAME = os.getenv('EMBEDDING_MODEL_NAME', 'paraphrase-multilingual-MiniLM-L12-v2')
CROSS_ENCODER_MODEL = os.getenv('CROSS_ENCODER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-12-v2')
# Лимит токенов в месяц для коммерческой лицензии (только выходные токены)
MONTHLY_TOKEN_LIMIT = int(os.getenv('MONTHLY_TOKEN_LIMIT', '10000000'))
ALERT_THRESHOLD = float(os.getenv('TOKEN_ALERT_THRESHOLD', '0.8'))  # 80%

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
    completion_tokens: Optional[int] = None
    month_key: Optional[str] = None
    monthly_usage: Optional[int] = None
    monthly_limit: Optional[int] = None
    usage_ratio: Optional[float] = None

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    embedding_time: float

class IndexRequest(BaseModel):
    documents: List[str]

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

class SearchHit(BaseModel):
    text: str
    score: float

class SearchResponse(BaseModel):
    hits: List[SearchHit]

class UsageResponse(BaseModel):
    month_key: str
    monthly_usage: int
    monthly_limit: int
    usage_ratio: float

# Глобальные переменные для моделей
llm: Optional[Llama] = None
embedding_model: Optional[SentenceTransformer] = None
cross_encoder: Optional[CrossEncoder] = None

# Индексы для поиска
faiss_index = None
dense_embeddings = None
bm25_index: Optional[BM25Okapi] = None
bm25_corpus_tokens: List[List[str]] = []
corpus_texts: List[str] = []

# Учёт токенов
token_month_key = datetime.now().strftime('%Y-%m')
monthly_completion_tokens = 0

def _reset_usage_if_needed():
    global token_month_key, monthly_completion_tokens
    now_key = datetime.now().strftime('%Y-%m')
    if now_key != token_month_key:
        token_month_key = now_key
        monthly_completion_tokens = 0

def get_index_hash() -> str:
    """Генерирует хеш для проверки актуальности индекса"""
    content = f"{EMBEDDING_MODEL_NAME}_{len(corpus_texts)}_{hash(tuple(corpus_texts)) if corpus_texts else 0}"
    return hashlib.md5(content.encode()).hexdigest()

async def save_index_to_disk():
    """Сохраняет FAISS индекс и метаданные на диск"""
    try:
        if faiss_index is None or not corpus_texts:
            return False
            
        os.makedirs('models', exist_ok=True)
        
        index_data = {
            'faiss_index_bytes': faiss.serialize_index(faiss_index),
            'dense_embeddings': dense_embeddings,
            'corpus_texts': corpus_texts,
            'bm25_tokens': bm25_corpus_tokens,
            'timestamp': datetime.now(),
            'model_hash': get_index_hash(),
            'embedding_model': EMBEDDING_MODEL_NAME
        }
        
        with open('models/search_index.pkl', 'wb') as f:
            pickle.dump(index_data, f)
        
        logger.info(f"Индекс сохранён: {len(corpus_texts)} документов")
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения индекса: {e}")
        return False

async def load_index_from_disk() -> bool:
    """Загружает сохранённый индекс с диска"""
    try:
        if not os.path.exists('models/search_index.pkl'):
            return False
            
        with open('models/search_index.pkl', 'rb') as f:
            data = pickle.load(f)
        
        # Проверяем актуальность модели
        if data.get('embedding_model') != EMBEDDING_MODEL_NAME:
            logger.info("Модель эмбеддингов изменилась, переиндексация необходима")
            return False
            
        global faiss_index, dense_embeddings, corpus_texts, bm25_corpus_tokens, bm25_index
        
        faiss_index = faiss.deserialize_index(data['faiss_index_bytes'])
        dense_embeddings = data['dense_embeddings']
        corpus_texts = data['corpus_texts']
        bm25_corpus_tokens = data['bm25_tokens']
        bm25_index = BM25Okapi(bm25_corpus_tokens)
        
        logger.info(f"Индекс загружен: {len(corpus_texts)} документов")
        return True
    except Exception as e:
        logger.error(f"Ошибка загрузки индекса: {e}")
        return False

@app.on_event("startup")
async def load_models():
    global llm, embedding_model, cross_encoder
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
        
        logger.info("Загрузка Cross-Encoder модели...")
        cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)
        
        # Пытаемся загрузить сохранённый индекс
        if not await load_index_from_disk():
            logger.info("Сохранённый индекс не найден или устарел")
        
        logger.info("Модели успешно загружены")
    except Exception as e:
        logger.error(f"Ошибка при загрузке моделей: {e}")
        raise

@app.get("/health")
async def health_check():
    _reset_usage_if_needed()
    return {
        "status": "ok",
        "models_loaded": all([llm is not None, embedding_model is not None, cross_encoder is not None]),
        "model_path": MODEL_PATH,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "cross_encoder_model": CROSS_ENCODER_MODEL,
        "ctx": N_CTX,
        "gpu_layers": N_GPU_LAYERS,
        "corpus_size": len(corpus_texts),
        "usage": {
            "month": token_month_key,
            "completion_tokens": monthly_completion_tokens,
            "limit": MONTHLY_TOKEN_LIMIT,
            "ratio": (monthly_completion_tokens / MONTHLY_TOKEN_LIMIT) if MONTHLY_TOKEN_LIMIT else 0.0
        }
    }

@app.post("/usage", response_model=UsageResponse)
async def usage():
    _reset_usage_if_needed()
    return UsageResponse(
        month_key=token_month_key,
        monthly_usage=monthly_completion_tokens,
        monthly_limit=MONTHLY_TOKEN_LIMIT,
        usage_ratio=(monthly_completion_tokens / MONTHLY_TOKEN_LIMIT) if MONTHLY_TOKEN_LIMIT else 0.0
    )

@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    try:
        _reset_usage_if_needed()
        start_time = datetime.now()
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

        text = ""
        completion_tokens = None
        if result and "choices" in result and len(result["choices"]) > 0:
            text = result["choices"][0]["text"].strip()
        # Пытаемся получить usage из ответа
        try:
            usage = result.get("usage") if isinstance(result, dict) else None
            if usage and isinstance(usage, dict) and "completion_tokens" in usage:
                completion_tokens = int(usage["completion_tokens"])  # type: ignore
        except Exception:
            completion_tokens = None
        # Если нет usage — посчитаем токены у ответа
        if completion_tokens is None:
            try:
                completion_tokens = len(llm.tokenize(text.encode('utf-8')))  # type: ignore
            except Exception:
                completion_tokens = len(text.split())

        # Учет токенов
        global monthly_completion_tokens
        monthly_completion_tokens += int(completion_tokens or 0)
        ratio = (monthly_completion_tokens / MONTHLY_TOKEN_LIMIT) if MONTHLY_TOKEN_LIMIT else 0.0
        if ratio >= ALERT_THRESHOLD:
            logger.warning(
                f"Достигнут {int(ratio*100)}% месячного лимита выходных токенов: "
                f"{monthly_completion_tokens}/{MONTHLY_TOKEN_LIMIT}"
            )

        generation_time = (datetime.now() - start_time).total_seconds()
        return GenerateResponse(
            response=text,
            generation_time=generation_time,
            completion_tokens=completion_tokens,
            month_key=token_month_key,
            monthly_usage=monthly_completion_tokens,
            monthly_limit=MONTHLY_TOKEN_LIMIT,
            usage_ratio=ratio
        )
    except Exception as e:
        logger.error(f"Ошибка при генерации ответа: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed", response_model=EmbeddingResponse)
async def embed(request: EmbeddingRequest):
    try:
        start_time = datetime.now()
        embeddings = embedding_model.encode(request.texts)
        embedding_time = (datetime.now() - start_time).total_seconds()
        return EmbeddingResponse(embeddings=embeddings.tolist(), embedding_time=embedding_time)
    except Exception as e:
        logger.error(f"Ошибка при создании эмбеддингов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/index")
async def index_docs(req: IndexRequest):
    """Индексация массива документов для гибридного поиска."""
    global faiss_index, dense_embeddings, bm25_index, bm25_corpus_tokens, corpus_texts
    try:
        corpus_texts = [t for t in req.documents if t and t.strip()]
        if not corpus_texts:
            return {"indexed": 0}
        # Dense
        dense_embeddings = embedding_model.encode(corpus_texts, convert_to_numpy=True)
        dim = dense_embeddings.shape[1]
        faiss_index = faiss.IndexFlatIP(dim)
        # нормируем для косинуса
        norms = np.linalg.norm(dense_embeddings, axis=1, keepdims=True) + 1e-12
        dense_norm = dense_embeddings / norms
        faiss_index.add(dense_norm.astype('float32'))
        # BM25
        bm25_corpus_tokens = [t.lower().split() for t in corpus_texts]
        bm25_index = BM25Okapi(bm25_corpus_tokens)
        
        # Сохраняем индекс на диск
        await save_index_to_disk()
        
        return {"indexed": len(corpus_texts)}
    except Exception as e:
        logger.error(f"Ошибка индексации: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    """Гибридный ретривер: BM25 + FAISS, реранкинг косинусом."""
    try:
        if not corpus_texts:
            return SearchResponse(hits=[])
        # Dense кандидаты
        q_emb = embedding_model.encode([req.query], convert_to_numpy=True)
        q_norm = q_emb / (np.linalg.norm(q_emb, axis=1, keepdims=True) + 1e-12)
        D, I = faiss_index.search(q_norm.astype('float32'), min(req.top_k*3, len(corpus_texts)))
        dense_candidates = [(int(idx), float(score)) for idx, score in zip(I[0], D[0]) if idx >= 0]
        # BM25 кандидаты
        bm_scores = bm25_index.get_scores(req.query.lower().split())
        bm_top = np.argsort(bm_scores)[-req.top_k*3:][::-1]
        bm_candidates = [(int(idx), float(bm_scores[idx])) for idx in bm_top]
        # Слияние
        combined = {}
        for idx, sc in dense_candidates:
            combined[idx] = max(combined.get(idx, 0.0), sc)
        for idx, sc in bm_candidates:
            combined[idx] = max(combined.get(idx, 0.0), sc)
        # Реранкинг косинусом на объединённом пуле
        rerank = []
        for idx, _ in combined.items():
            doc_emb = dense_embeddings[idx]
            score = float(util.cos_sim(q_emb, np.expand_dims(doc_emb, 0))[0][0])
            rerank.append((idx, score))
        rerank.sort(key=lambda x: x[1], reverse=True)
        top_idxs = [idx for idx, _ in rerank[:req.top_k]]
        hits = [SearchHit(text=corpus_texts[i], score=float([s for j, s in rerank if j==i][0])) for i in top_idxs]
        return SearchResponse(hits=hits)
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search_v2", response_model=SearchResponse)
async def search_v2(req: SearchRequest):
    """Улучшенный поиск с Cross-Encoder переранжированием."""
    try:
        if not corpus_texts:
            return SearchResponse(hits=[])
            
        # 1. Получаем больше кандидатов для переранжирования
        candidates_count = min(req.top_k * 5, len(corpus_texts))
        
        # Dense поиск
        q_emb = embedding_model.encode([req.query], convert_to_numpy=True)
        q_norm = q_emb / (np.linalg.norm(q_emb, axis=1, keepdims=True) + 1e-12)
        D, I = faiss_index.search(q_norm.astype('float32'), candidates_count)
        dense_candidates = [(int(idx), float(score)) for idx, score in zip(I[0], D[0]) if idx >= 0]
        
        # BM25 поиск
        bm_scores = bm25_index.get_scores(req.query.lower().split())
        bm_top = np.argsort(bm_scores)[-candidates_count:][::-1]
        bm_candidates = [(int(idx), float(bm_scores[idx])) for idx in bm_top]
        
        # Объединяем кандидатов
        combined_scores = {}
        for idx, score in dense_candidates:
            combined_scores[idx] = combined_scores.get(idx, 0) + score * 0.7  # вес dense
        for idx, score in bm_candidates:
            combined_scores[idx] = combined_scores.get(idx, 0) + score * 0.3  # вес BM25
            
        # Берём топ кандидатов для Cross-Encoder
        top_candidates = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:min(20, len(combined_scores))]
        
        # 2. Cross-Encoder переранжирование
        candidate_texts = [corpus_texts[idx] for idx, _ in top_candidates]
        query_doc_pairs = [(req.query, doc) for doc in candidate_texts]
        
        cross_scores = cross_encoder.predict(query_doc_pairs)
        
        # 3. Финальное ранжирование по Cross-Encoder скорам
        final_ranking = []
        for i, (idx, _) in enumerate(top_candidates):
            final_ranking.append((idx, float(cross_scores[i])))
            
        final_ranking.sort(key=lambda x: x[1], reverse=True)
        
        # Возвращаем топ результатов
        top_results = final_ranking[:req.top_k]
        hits = [SearchHit(text=corpus_texts[idx], score=score) for idx, score in top_results]
        
        return SearchResponse(hits=hits)
        
    except Exception as e:
        logger.error(f"Ошибка в search_v2: {e}")
        # Fallback на обычный поиск
        return await search(req)

if __name__ == "__main__":
    uvicorn.run(
        "model_service:app",
        host="0.0.0.0",
        port=8000,
        workers=1
    ) 