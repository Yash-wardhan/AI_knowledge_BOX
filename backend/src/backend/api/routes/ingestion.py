
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import AsyncSessionLocal, get_db
from backend.models.items import Item
from services.ingestion_service import process_item_ingestion

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])

logger = logging.getLogger(__name__)


async def run_ingestion(item_id: int):
    """Run ingestion using an independent database session."""

    async with AsyncSessionLocal() as db:
        try:
            await process_item_ingestion(db, item_id)
        except Exception:
            logger.exception("Ingestion failed for item_id=%s", item_id)


@router.post("/{item_id}", status_code=202)
async def start_ingestion(
    item_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Item).where(Item.id == item_id)
    )

    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item not found",
        )

    if item.status == "processing":
        raise HTTPException(
            status_code=409,
            detail="Item is already being processed",
        )

    background_tasks.add_task(run_ingestion, item_id)

    return {
        "message": "Ingestion started successfully",
        "item_id": item_id,
        "status": "pending",
    }