import pytest

from backend.database.connection import AsyncSessionLocal
from services.rag_service import answer_question


@pytest.mark.asyncio
async def test_rag_answer():
    async with AsyncSessionLocal() as db:
        result = await answer_question(
            db=db,
            question="What is FastAPI?",
            top_k=5,
        )

    assert "answer" in result
    assert "citations" in result

    print("\nAnswer:", result["answer"])
    print("\nCitations:", result["citations"])