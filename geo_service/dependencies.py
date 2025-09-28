"""
dependencies.py
This file contains dependency definitions for the geo_service application.
"""

from fastapi import Depends

from geo_service.repositories.implementations.geo_repo import GeoRepo
from geo_service.repositories.interfaces.iface_geo_repo import GeoRepoInterface
from geo_service.services.geo_service import GeoService

# Create a single shared instance for the @lru_cache inside the repository
_GEO_REPO_SINGLETON: GeoRepoInterface | None = None


async def get_geo_repo() -> GeoRepoInterface:
    global _GEO_REPO_SINGLETON
    if _GEO_REPO_SINGLETON is None:
        _GEO_REPO_SINGLETON = GeoRepo()
    return _GEO_REPO_SINGLETON


async def get_geo_service(
    geo_cond_repository: GeoRepoInterface = Depends(get_geo_repo),
):
    return GeoService(geo_cond_repository)
