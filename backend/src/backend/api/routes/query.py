
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_db
from backend.models.query import AskRequest, AskResponse, QueryRequest, QueryResponse
from guardrails.guardrail_service import BLOCKED_RESPONSE, LLMRateLimitedError
from services.conversation_service import (
    create_conversation,
    get_conversation,
    get_conversation_history,
    save_message,
)
from services.rag_service import answer_question
from services.retrieval_service import search_similar_chunks

router = APIRouter(prefix="/query", tags=["Query"])

# Prior messages replayed to the LLM (3 user/assistant turns) — keeps prompts
# small for rate-limited providers.
HISTORY_LIMIT = 6

logger = logging.getLogger(__name__)


@router.post("/", response_model=QueryResponse)
async def semantic_search(
    payload: QueryRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        results = await search_similar_chunks(
            db=db,
            question=payload.question,
            top_k=payload.top_k,
        )

        return {
            "question": payload.question,
            "total_results": len(results),
            "results": results,
        }

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    except Exception:
        logger.exception("Semantic search failed")
        raise HTTPException(
            status_code=503,
            detail="Semantic search is temporarily unavailable",
        )


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    payload: AskRequest,
    db: AsyncSession = Depends(get_db),
):
    # Resolve an existing session. New sessions are created only after a
    # successful answer, so failed first questions don't leave empty rows.
    conversation = None
    history: list[dict] = []
    if payload.session_id:
        conversation = await get_conversation(db=db, session_id=payload.session_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        history = await get_conversation_history(
            db=db,
            conversation_id=conversation.id,
            limit=HISTORY_LIMIT,
        )

    try:
        result = await answer_question(
            db=db,
            question=payload.question,
            top_k=payload.top_k,
            history=history,
        )

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    except LLMRateLimitedError:
        logger.warning("LLM provider rate limited / overloaded after retries")
        raise HTTPException(
            status_code=429,
            detail="The AI model is busy right now. Please try again in a few seconds.",
            headers={"Retry-After": "10"},
        )

    except Exception:
        logger.exception("RAG question answering failed")
        raise HTTPException(
            status_code=503,
            detail="Question answering is temporarily unavailable",
        )

    # Persist the exchange. Blocked turns are not saved: replaying a refusal
    # (or the attack that caused it) would poison later answers.
    if result["answer"] != BLOCKED_RESPONSE:
        if conversation is None:
            conversation = await create_conversation(db)
        await save_message(db, conversation.id, "user", payload.question)
        await save_message(
            db, conversation.id, "assistant", result["answer"], result["citations"]
        )

    return {
        **result,
        "session_id": conversation.session_id if conversation else payload.session_id,
    }
