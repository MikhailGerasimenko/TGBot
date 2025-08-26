# Model Service API

Базовый URL: `http://host:8000`

## GET /health
Возвращает статус, загруженные модели, размер корпуса, учёт токенов.

## POST /generate
Тело:
```json
{
  "query": "строка",
  "context": "опционально",
  "max_tokens": 512,
  "temperature": 0.7,
  "top_p": 0.95
}
```
Ответ:
```json
{
  "response": "текст",
  "generation_time": 0.52,
  "completion_tokens": 120,
  "month_key": "2025-08",
  "monthly_usage": 2134,
  "monthly_limit": 10000000,
  "usage_ratio": 0.0002
}
```

## POST /embed (alias /embeddings)
Тело:
```json
{ "texts": ["a", "b", "c"] }
```
Ответ: массив эмбеддингов и время.

## POST /index
Тело:
```json
{ "documents": ["chunk1", "chunk2", "..."] }
```
Индексация корпуса (FAISS + BM25), сериализация индекса на диск.

## POST /search
Тело: `{ "query": "строка", "top_k": 5 }` — гибридный поиск, косинусный реранкинг.

## POST /search_v2
То же, но кандидаты реранжируются Cross‑Encoder’ом (лучше качество, дороже).

## POST /usage
Возвращает текущий учёт выходных токенов. 