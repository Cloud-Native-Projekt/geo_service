"""
geo_service.py
Service layer for geo-related queries (power, protection, forest, buildings).
"""

import logging
import os

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

    async def get_health(self) -> ResultHealth:
        health: ResultHealth = await self.geo_repo.get_health()
        if not health:
            self.logger.error("Health check failed")
            raise ValueError("Health check failed")
        return health

    async def get_power(self, req: GeoCond) -> ResultPower:
        power: ResultPower = await self.geo_repo.get_power(
            lat=req.lat, lng=req.lng, radius=req.radius
        )
        if not power:
            self.logger.error(f"Power data not found for {req}")
            raise ValueError("Power infrastructure data not found")
        return power

    async def get_protected_areas(self, req: GeoCond) -> ResultProtection:
        protection: ResultProtection = await self.geo_repo.get_protected_areas(
            lat=req.lat, lng=req.lng, radius=req.radius
        )
        if not protection:
            self.logger.error(f"Protected areas data not found for {req}")
            raise ValueError("Protected areas data not found")
        return protection

    async def get_forest(self, req: GeoCond) -> ResultForest:
        forest: ResultForest = await self.geo_repo.get_forest(
            lat=req.lat, lng=req.lng, radius=req.radius
        )
        if not forest:
            self.logger.error(f"Forest data not found for {req}")
            raise ValueError("Forest data not found")
        return forest

    async def get_buildings_in_area(self, req: GeoCond) -> ResultBuildings:
        buildings: ResultBuildings = await self.geo_repo.get_buildings_in_area(
            lat=req.lat, lng=req.lng, radius=req.radius
        )
        if not buildings:
            self.logger.error(f"Buildings in area data not found for {req}")
            raise ValueError("Buildings in area data not found")
        return buildings
