import aiohttp
import logging
from typing import List, Optional
from config import MODEL_SERVICE_URL

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, base_url: str = MODEL_SERVICE_URL):
        self.base_url = base_url.rstrip('/')
        self._timeout = aiohttp.ClientTimeout(total=30)
        
    async def health_check(self) -> dict:
        """Проверка здоровья сервиса"""
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.get(f"{self.base_url}/health") as response:
                return await response.json()
    
    async def generate(
        self,
        query: str,
        context: str = "",
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.95
    ) -> Optional[str]:
        """Генерация ответа"""
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.post(
                    f"{self.base_url}/generate",
                    json={
                        "query": query,
                        "context": context,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "top_p": top_p
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["response"]
                    else:
                        error = await response.text()
                        logger.error(f"Ошибка генерации: {error}")
                        return None
        except Exception as e:
            logger.error(f"Ошибка при обращении к сервису: {e}")
            return None
    
    async def create_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Создание эмбеддингов"""
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.post(
                    f"{self.base_url}/embed",
                    json={"texts": texts}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["embeddings"]
                    else:
                        error = await response.text()
                        logger.error(f"Ошибка создания эмбеддингов: {error}")
                        return None
        except Exception as e:
            logger.error(f"Ошибка при обращении к сервису: {e}")
            return None 