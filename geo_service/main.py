import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from geo_service.routes import geo_router
import asyncio


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
