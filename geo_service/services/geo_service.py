"""
geo_service.py
Service layer for geo-related queries (power, protection, forest, buildings).
"""

import asyncio
import logging
import os
import time
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, Tuple

from geo_service.config import settings
from geo_service.repositories.interfaces.iface_geo_repo import GeoRepoInterface
from geo_service.schemas.geo_schemas import (
    GeoCond,
    ResultBuildings,
    ResultForest,
    ResultHealth,
    ResultPower,
    ResultProtection,
)

LOGLEVEL = os.getenv("LOGLEVEL", "INFO")


class GeoService:
    """
    Service class for geographic data operations.
    This class provides asynchronous methods to retrieve various types of
    geographic information within a specified area, including power
    infrastructure, protected areas, forest presence, and buildings.
    Each method interacts with a repository interface to fetch the required
    data and raises a ValueError if the data is not found.
    Args:
        geo_repo (GeoRepoInterface): Repository interface for geographic data
        access.
    Methods:
        get_power(req: GeoCond) -> ResultPower:
            Retrieve power infrastructure data for the specified area.
        get_protected_areas(req: GeoCond) -> ResultProtection:
            Retrieve protected areas presence for the specified area.
        get_forest(req: GeoCond) -> ResultForest:
            Retrieve forest presence data for the specified area.
        get_buildings_in_area(req: GeoCond) -> ResultBuildings:
            Retrieve buildings presence within the specified area.
    """

    def __init__(self, geo_repo: GeoRepoInterface):
        self.geo_repo = geo_repo
        logging.basicConfig(
            level=LOGLEVEL,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        self._cache: Dict[Tuple[str, float, float, int], Tuple[float, Any]] = {}
        self._ttl = float(settings.geo_cache_ttl)
        # Precision for rounding lat/lng to improve cache hit rate
        self._precision = int(settings.geo_cache_precision)
        # Per-key locks to avoid thundering herd when multiple identical
        # requests race to populate the cache simultaneously.
        self._locks: Dict[Tuple[str, float, float, int], asyncio.Lock] = defaultdict(
            asyncio.Lock
        )

    def _cache_get(self, key: Tuple[str, float, float, int]):
        if self._ttl <= 0:
            return None  # caching disabled
        item = self._cache.get(key)
        if not item:
            return None
        expiry, value = item
        if expiry < time.time():
            # Expired
            self._cache.pop(key, None)
            return None
        return value

    def _cache_set(self, key: Tuple[str, float, float, int], value: Any):
        if self._ttl <= 0:
            return  # caching disabled
        self._cache[key] = (time.time() + self._ttl, value)

    async def _get_or_compute(
        self,
        label: str,
        lat: float,
        lng: float,
        radius: int,
        producer: Callable[[], Awaitable[Any]],
    ):
        # Round lat/lng to configured precision to stabilize keys
        r_lat = round(lat, self._precision)
        r_lng = round(lng, self._precision)
        cache_key = (label, r_lat, r_lng, radius)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        lock = self._locks[cache_key]
        async with lock:
            # Re-check after awaiting
            cached = self._cache_get(cache_key)
            if cached is not None:
                return cached
            value = await producer()
            self._cache_set(cache_key, value)
            return value

    async def get_health(self) -> ResultHealth:
        health: ResultHealth = await self.geo_repo.get_health()
        if not health:
            self.logger.error("Health check failed")
            raise ValueError("Health check failed")
        return health

    async def get_power(self, req: GeoCond) -> ResultPower:
        async def _producer():
            power: ResultPower = await self.geo_repo.get_power(
                lat=req.lat, lng=req.lng, radius=req.radius
            )
            if not power:
                self.logger.error(f"Power data not found for {req}")
                raise ValueError("Power infrastructure data not found")
            return power

        return await self._get_or_compute(
            "power", req.lat, req.lng, req.radius, _producer
        )

    async def get_protected_areas(self, req: GeoCond) -> ResultProtection:
        async def _producer():
            protection: ResultProtection = await self.geo_repo.get_protected_areas(
                lat=req.lat,
                lng=req.lng,
                radius=req.radius,
            )
            if not protection:
                self.logger.error(f"Protected areas data not found for {req}")
                raise ValueError("Protected areas data not found")
            return protection

        return await self._get_or_compute(
            "protection", req.lat, req.lng, req.radius, _producer
        )

    async def get_forest(self, req: GeoCond) -> ResultForest:
        async def _producer():
            forest: ResultForest = await self.geo_repo.get_forest(
                lat=req.lat, lng=req.lng, radius=req.radius
            )
            if not forest:
                self.logger.error(f"Forest data not found for {req}")
                raise ValueError("Forest data not found")
            return forest

        return await self._get_or_compute(
            "forest", req.lat, req.lng, req.radius, _producer
        )

    async def get_buildings_in_area(self, req: GeoCond) -> ResultBuildings:
        async def _producer():
            buildings: ResultBuildings = await self.geo_repo.get_buildings_in_area(
                lat=req.lat,
                lng=req.lng,
                radius=req.radius,
            )
            if not buildings:
                self.logger.error(f"Buildings in area data not found for {req}")
                raise ValueError("Buildings in area data not found")
            return buildings

        return await self._get_or_compute(
            "buildings", req.lat, req.lng, req.radius, _producer
        )
