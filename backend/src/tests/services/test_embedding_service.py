import pytest

from services.embedding_service import create_embedding


@pytest.mark.asyncio
async def test_local_embedding():

    embedding = await create_embedding(
        "FastAPI is a Python framework.",
        task="search_document"
    )

    assert len(embedding) == 768
    assert all(isinstance(value, float) for value in embedding)