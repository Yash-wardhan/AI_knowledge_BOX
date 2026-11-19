
from openai import AsyncOpenAI

from backend.core.config import settings


async def create_embedding(
    text: str,
    task: str = "search_document",
) -> list[float]:

    if task not in ("search_document", "search_query"):
        raise ValueError("Invalid embedding task")

    if not text.strip():
        raise ValueError("Text cannot be empty")

    async with AsyncOpenAI(
        base_url=settings.EMBEDDING_BASE_URL,
        api_key=settings.EMBEDDING_API_KEY,
    ) as client:

        response = await client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=f"{task}: {text}",
        )

    embedding = response.data[0].embedding

    if len(embedding) != settings.EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Expected {settings.EMBEDDING_DIMENSIONS} dimensions, "
            f"got {len(embedding)}"
        )

    return embedding


async def create_embeddings(
    texts: list[str],
) -> list[list[float]]:

    if not texts:
        return []

    async with AsyncOpenAI(
        base_url=settings.EMBEDDING_BASE_URL,
        api_key=settings.EMBEDDING_API_KEY,
    ) as client:

        response = await client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=[
                f"search_document: {text}"
                for text in texts
            ],
        )

    embeddings = [
        item.embedding for item in response.data
    ]

    for embedding in embeddings:
        if len(embedding) != settings.EMBEDDING_DIMENSIONS:
            raise ValueError("Embedding dimension mismatch")

    return embeddings
