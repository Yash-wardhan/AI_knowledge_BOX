from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_db
from backend.models.items import Item, ItemCreate, ItemDetailResponse, ItemResponse

router = APIRouter(
    prefix="/items",
    tags=["Items"]
)


@router.post("/", status_code=201)
async def create_item(
    payload: ItemCreate,
    db: AsyncSession = Depends(get_db)
):
    if payload.source_type == "text":
        if not payload.content or not payload.content.strip():
            raise HTTPException(
                status_code=422,
                detail="Content is required for text notes"
            )

        item = Item(
            title=payload.title,
            source_type="text",
            raw_content=payload.content,
            source_url=None,
        )

    elif payload.source_type == "url":
        if not payload.source_url:
            raise HTTPException(
                status_code=422,
                detail="Source URL is required"
            )

        item = Item(
            title=payload.title,
            source_type="url",
            source_url=str(payload.source_url),
            raw_content="",
        )

    else:
        raise HTTPException(
            status_code=422,
            detail="source_type must be 'text' or 'url'"
        )

    db.add(item)
    await db.commit()
    await db.refresh(item)

    return {
        "message": "Item saved successfully",
        "data": {
            "id": item.id,
            "title": item.title,
            "source_type": item.source_type,
            "status": item.status,
            "created_at": item.created_at,
        }
    }


@router.get("/", response_model=list[ItemResponse])
async def get_items(
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Item).order_by(Item.created_at.desc())
    )

    return result.scalars().all()


@router.get("/{item_id}", response_model=ItemDetailResponse)
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Item).where(Item.id == item_id)
    )

    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item not found"
        )

    return item

@router.delete("/{item_id}")
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Item).where(Item.id == item_id)
    )

    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item not found"
        )

    await db.delete(item)
    await db.commit()

    return {
        "message": "Item deleted successfully",
        "item_id": item_id
    }