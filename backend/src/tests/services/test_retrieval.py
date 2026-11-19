
import pytest

from backend.database.connection import AsyncSessionLocal
from services.retrieval_service import search_similar_chunks


@pytest.mark.asyncio
async def test_semantic_search():
    async with AsyncSessionLocal() as db:
        results = await search_similar_chunks(
            db=db,
            question="What is FastAPI?",
            top_k=5,
        )

    assert isinstance(results, list)

    for result in results:
        assert "chunk_id" in result
        assert "content" in result
        assert "similarity" in result

    print(results)
