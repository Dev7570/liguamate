"""Embedding generation utility using OpenAI embeddings API"""

from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key)


async def generate_embedding(text: str) -> list[float]:
    """Generate a 1536-dimension embedding vector for the given text."""
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding
