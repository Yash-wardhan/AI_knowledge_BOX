
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.conversation_service import (
    create_conversation,
    get_conversation,
    get_conversation_history,
    save_message,
)


@pytest.mark.asyncio
async def test_create_conversation():
    db = AsyncMock()

    db = AsyncMock()
    db.add = MagicMock()

    conversation = await create_conversation(db)

    assert conversation.session_id is not None
    assert isinstance(conversation.session_id, uuid.UUID)

    db.add.assert_called_once_with(conversation)
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(conversation)


@pytest.mark.asyncio
async def test_get_conversation():
    db = AsyncMock()

    session_id = uuid.uuid4()
    expected_conversation = MagicMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = expected_conversation
    db.execute.return_value = result

    conversation = await get_conversation(db, session_id)

    assert conversation == expected_conversation
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_conversation_not_found():
    db = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result

    conversation = await get_conversation(db, uuid.uuid4())

    assert conversation is None


@pytest.mark.asyncio
async def test_get_conversation_history():
    db = AsyncMock()

    conversation_id = uuid.uuid4()

    messages = [
        MagicMock(
            role="assistant",
            content="FastAPI is a Python framework."
        ),
        MagicMock(
            role="user",
            content="What is FastAPI?"
        ),
    ]

    scalars = MagicMock()
    scalars.all.return_value = messages

    result = MagicMock()
    result.scalars.return_value = scalars

    db.execute.return_value = result

    history = await get_conversation_history(
        db=db,
        conversation_id=conversation_id,
        limit=10,
    )

    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
    assert history[0]["content"] == "What is FastAPI?"


@pytest.mark.asyncio
async def test_save_message():
    db = AsyncMock()
    db.add = MagicMock()
    conversation_id = uuid.uuid4()

    message = await save_message(
        db=db,
        conversation_id=conversation_id,
        role="user",
        content="What is FastAPI?",
    )

    assert message.conversation_id == conversation_id
    assert message.role == "user"
    assert message.content == "What is FastAPI?"

    db.add.assert_called_once_with(message)
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(message)
