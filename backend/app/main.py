import logging

from fastapi import FastAPI

from app.api.v1.main import api_router
from app.core.config import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    force=True,
)

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)
app.include_router(api_router, prefix=settings.API_V1_STR)
