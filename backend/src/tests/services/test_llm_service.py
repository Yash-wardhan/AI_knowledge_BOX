import pytest

from services.llm_service import generate_answer


@pytest.mark.asyncio
async def test_generate_answer():
    answer = await generate_answer(
        question="What is FastAPI?",
        context="""
        [S1]
        FastAPI is a modern Python web framework.
        It supports asynchronous programming and
        automatic API documentation.
        """,
    )

    assert isinstance(answer, str)
    assert len(answer) > 0

    print("\nGenerated answer:", answer)