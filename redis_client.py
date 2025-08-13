import redis.asyncio as redis
from config import REDIS_URL

# Singletons for async usage across the app
redis_client = redis.from_url(REDIS_URL, decode_responses=True) 