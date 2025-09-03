from geo_service.repositories.interfaces.iface_geo_repo import GeoRepoInterface
from geo_service.schemas.geo_schemas import (
    GeoCond,
    ResultBuildings,
    ResultForest,
    ResultPower,
    ResultProtection,
)


class GeoService:

    def __init__(self, geo_repo: GeoRepoInterface):
        self.geo_repo = geo_repo

    async def get_power(self, req: GeoCond) -> ResultPower:
        """Fetch GeoCond data and return as GeoCondResult."""
        power: ResultPower = await self.geo_repo.get_power_infrastructure(
            lat=req.lat, lng=req.lng
        )
        if not power:
            raise ValueError("Power infrastructure data not found")
        return power

    async def get_protected_areas(self, req: GeoCond) -> ResultProtection:
        """Fetch protected areas data."""
        protection: ResultProtection = await self.geo_repo.get_protected_areas(
            lat=req.lat, lng=req.lng
        )
        if not protection:
            raise ValueError("Protected areas data not found")
        return protection

    async def get_forest(self, req: GeoCond) -> ResultForest:
        """Fetch forest overlap data."""
        forest: ResultForest = await self.geo_repo.get_forest(
            lat=req.lat, lng=req.lng
        )
        if not forest:
            raise ValueError("Forest overlap data not found")
        return forest

    async def get_buildings_in_area(self, req: GeoCond) -> ResultBuildings:
        """Fetch built-up/buildings data."""
        buildings: ResultBuildings = await self.geo_repo.get_buildings_in_area(
            lat=req.lat, lng=req.lng
        )
        if not buildings:
            raise ValueError("Buildings in area data not found")
        return buildings
