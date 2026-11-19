
import tiktoken
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chunk import Chunk
from backend.models.items import Item
from services.chunking_service import split_text_into_chunks
from services.embedding_service import create_embeddings
from services.url_fetch_service import fetch_url_content

encoding = tiktoken.encoding_for_model("text-embedding-3-small")


async def process_item_ingestion(
    db: AsyncSession,
    item_id: int
):
    # 1. Find item
    result = await db.execute(
        select(Item).where(Item.id == item_id)
    )

    item = result.scalar_one_or_none()

    if not item:
        raise ValueError(f"Item {item_id} not found")

    # 2. Mark item as processing
    item.status = "processing"
    await db.commit()

    try:
        # 3. Split content into chunks
        if item.source_type == "url":
            if not item.source_url:
                raise ValueError("Source URL is missing")

            item.raw_content = await fetch_url_content(item.source_url)
            await db.flush()

        # 4. Split content into chunks
        chunks = split_text_into_chunks(item.raw_content)

        if not chunks:
            raise ValueError("No content available for ingestion")

        # 4. Generate local embeddings in batch
        embeddings = await create_embeddings(chunks)

        if len(chunks) != len(embeddings):
            raise ValueError("Chunk and embedding count mismatch")

        # 5. Remove old chunks when reprocessing
        await db.execute(
            delete(Chunk).where(Chunk.item_id == item_id)
        )

        # 6. Save chunks and embeddings
        for index, (content, embedding) in enumerate(
            zip(chunks, embeddings)
        ):
            chunk = Chunk(
                item_id=item_id,
                chunk_index=index,
                content=content,
                embedding=embedding,
                token_count=len(encoding.encode(content))
            )

            db.add(chunk)

        # 7. Mark as completed
        item.status = "completed"

        await db.commit()

        return {
            "item_id": item_id,
            "status": "completed",
            "total_chunks": len(chunks)
        }

    except Exception:
        await db.rollback()

        # Mark item as failed
        result = await db.execute(
            select(Item).where(Item.id == item_id)
        )
        item = result.scalar_one_or_none()

        if item:
            item.status = "failed"
            await db.commit()

        raise
