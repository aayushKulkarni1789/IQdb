from fastapi import APIRouter

from .utils import router as utils_router

api_router = APIRouter()
api_router.include_router(utils_router, prefix="/utils")
