from fastapi import Depends

from geo_service.repositories.implementations.geo_repo import GeoRepo
from geo_service.repositories.interfaces.iface_geo_repo import GeoRepoInterface
from geo_service.services.geo_service import GeoService


async def get_geo_repo() -> GeoRepoInterface:
    return GeoRepo()


async def get_geo_service(
    geo_cond_repository: GeoRepoInterface = Depends(get_geo_repo),
):
    return GeoService(geo_cond_repository)
