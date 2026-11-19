
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.conversation import Conversation, Message


async def create_conversation(db: AsyncSession):
    conversation = Conversation(
        session_id=uuid.uuid4()
    )

    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return conversation


async def get_conversation(
    db: AsyncSession,
    session_id: uuid.UUID,
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.session_id == session_id
        )
    )

    return result.scalar_one_or_none()


async def get_conversation_history(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    limit: int = 10,
):
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(limit)
    )

    messages = result.scalars().all()

    return [
        {
            "role": message.role,
            "content": message.content,
            "citations": message.citations or [],
        }
        for message in reversed(messages)
    ]


async def save_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    citations: list[dict] | None = None,
):
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        citations=citations or None,
    )

    db.add(message)
    await db.commit()
    await db.refresh(message)

    return message

async def list_conversations(db: AsyncSession, limit: int = 50):
    """
    Conversations that have at least one message, most recently active first.
    Title = the first user question in the conversation.
    """
    first_question = (
        select(Message.content)
        .where(Message.conversation_id == Conversation.id, Message.role == "user")
        .order_by(Message.created_at, Message.id)
        .limit(1)
        .correlate(Conversation)
        .scalar_subquery()
    )
    last_activity = (
        select(func.max(Message.created_at))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )
    message_count = (
        select(func.count(Message.id))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )

    updated_at = func.coalesce(last_activity, Conversation.created_at).label("updated_at")

    result = await db.execute(
        select(
            Conversation.session_id,
            first_question.label("title"),
            updated_at,
            message_count.label("message_count"),
        )
        .where(message_count > 0)
        .order_by(updated_at.desc())
        .limit(limit)
    )

    return [
        {
            "session_id": str(row.session_id),
            "title": row.title or "New conversation",
            "updated_at": row.updated_at,
            "message_count": row.message_count,
        }
        for row in result.all()
    ]


async def delete_conversation(db: AsyncSession, session_id: uuid.UUID) -> bool:
    # Bulk DELETE: messages are removed by the FK's ON DELETE CASCADE.
    # (session.delete() would lazy-load the relationship, which fails under asyncio.)
    result = await db.execute(
        delete(Conversation).where(Conversation.session_id == session_id)
    )
    await db.commit()
    return result.rowcount > 0
