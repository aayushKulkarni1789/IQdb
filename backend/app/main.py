import asyncio
import contextlib
import logging
import time

from fastapi import FastAPI
from sqlmodel import Session

from app.api.v1.main import api_router
from app.core.cleanup import safe_run_cleanup_pass
from app.core.config import settings
from app.core.db import engine

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    force=True,
)

logger = logging.getLogger(__name__)

# First pass fires shortly after boot so a restarted backend immediately
# catches up on pre-existing finished rows (design D2).
FIRST_PASS_DELAY_SECONDS = 10.0


async def _sweep_loop() -> None:
    """Cleanup sweep loop with an in-memory derived schedule (design D2).

    ``next_pass = last_pass + interval`` is never persisted — idempotent
    deletes make missed or repeated sweeps cost-free. A failing pass logs a
    WARNING and the loop stays alive, retrying on the next tick.
    """
    interval_seconds = settings.SWEEP_INTERVAL_MINUTES * 60
    await asyncio.sleep(FIRST_PASS_DELAY_SECONDS)
    last_pass = time.monotonic()
    while True:
        safe_run_cleanup_pass(lambda: Session(engine))
        # Schedule derived in memory from the last pass time.
        next_pass = last_pass + interval_seconds
        delay = max(next_pass - time.monotonic(), 0.0)
        await asyncio.sleep(delay)
        last_pass = time.monotonic()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_sweep_loop())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)
app.include_router(api_router, prefix=settings.API_V1_STR)
