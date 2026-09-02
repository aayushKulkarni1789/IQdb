from fastapi import APIRouter

from app.api.v2.routes.query import router as query_router

api_v2_router = APIRouter()
api_v2_router.include_router(query_router, prefix="/search", tags=["v2-search"])
