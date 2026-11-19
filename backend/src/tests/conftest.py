import pytest_asyncio

from backend.database.connection import engine


@pytest_asyncio.fixture(autouse=True)
async def dispose_db_engine():
    yield
    await engine.dispose()