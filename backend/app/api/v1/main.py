from fastapi import APIRouter

from app.api.v1.routes import uploads, utils

api_router = APIRouter()
api_router.include_router(utils.router)
api_router.include_router(uploads.router)
