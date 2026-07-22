from fastapi import APIRouter

from app.api.v1.routes import uploads, utils
from app.search.routes import router as search_router

api_router = APIRouter()
api_router.include_router(utils.router)
api_router.include_router(uploads.router)
api_router.include_router(search_router)
