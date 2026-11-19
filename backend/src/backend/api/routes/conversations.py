
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_db
from services.conversation_service import (
    create_conversation,
    delete_conversation,
    get_conversation,
    get_conversation_history,
    list_conversations,
)

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


@router.get("/")
async def get_conversations(
    db: AsyncSession = Depends(get_db),
):
    return {"conversations": await list_conversations(db)}


@router.delete("/{session_id}", status_code=204)
async def remove_conversation(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    if not await delete_conversation(db=db, session_id=session_id):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )


@router.post("/", status_code=201)
async def start_conversation(
    db: AsyncSession = Depends(get_db),
):
    conversation = await create_conversation(db)

    return {
        "session_id": str(conversation.session_id),
        "message": "Conversation created successfully",
    }


@router.get("/{session_id}/messages")
async def get_messages(
    session_id: UUID,
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    conversation = await get_conversation(
        db=db,
        session_id=session_id,
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    messages = await get_conversation_history(
        db=db,
        conversation_id=conversation.id,
        limit=limit,
    )

    return {
        "session_id": str(session_id),
        "messages": messages,
    }