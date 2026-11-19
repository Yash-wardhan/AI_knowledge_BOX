from fastapi import APIRouter

from backend.api.routes import ingestion, items, query
from backend.api.routes.conversations import router as conversations_router

api_router = APIRouter()

api_router.include_router(ingestion.router)
api_router.include_router(items.router)
api_router.include_router(query.router)
api_router.include_router(conversations_router)