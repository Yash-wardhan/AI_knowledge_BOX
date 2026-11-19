
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chunk import Chunk
from backend.models.items import Item

from .embedding_service import create_embedding


async def search_similar_chunks(
    db: AsyncSession,
    question: str,
    top_k: int = 5,
):
    if not question.strip():
        raise ValueError("Question cannot be empty")

    # 1. Generate embedding for the user's question
    query_embedding = await create_embedding(
        question,
        task="search_query",
    )

    # 2. Calculate cosine distance and retrieve relevant chunks
    distance = Chunk.embedding.cosine_distance(query_embedding)

    statement = (
        select(
            Chunk.id.label("chunk_id"),
            Chunk.item_id,
            Chunk.content,
            Item.title,
            Item.source_url,
            distance.label("distance"),
        )
        .join(Item, Chunk.item_id == Item.id)
        .where(Chunk.embedding.is_not(None))
        .order_by(distance)
        .limit(top_k)
    )

    result = await db.execute(statement)
    rows = result.mappings().all()

    # 3. Format search results
    return [
        {
            "chunk_id": row["chunk_id"],
            "item_id": row["item_id"],
            "title": row["title"],
            "source_url": row["source_url"],
            "content": row["content"],
            "distance": float(row["distance"]),
            "similarity": round(1 - float(row["distance"]), 4),
        }
        for row in rows
    ]
