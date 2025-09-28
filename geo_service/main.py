import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from geo_service.routes import geo_router

LOGLEVEL = os.getenv("LOGLEVEL", "INFO")

logging.basicConfig(
    level=LOGLEVEL,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Running startup tasks...")
        logger.info("Startup tasks completed")
        yield
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        logger.info("Running shutdown tasks...")
        logger.info("Shutdown tasks completed")


app = FastAPI(lifespan=lifespan)

app.include_router(geo_router.router)


@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-ms"] = f"{duration:.2f}"
    logger.info(f"{request.method} {request.url.path} took {duration:.2f} ms")
    return response
