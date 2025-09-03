from fastapi import APIRouter, Depends, HTTPException

from geo_service.dependencies import get_geo_service
from geo_service.schemas.geo_schemas import GeoCond
from geo_service.services.geo_service import GeoService

router = APIRouter()


@router.get("/geo/power", status_code=200)
async def geo_power_endpoint(
    lat: float,
    lng: float,
    geo_service: GeoService = Depends(get_geo_service),
):
    geo_cond = GeoCond(lat=lat, lng=lng)
    return await geo_service.get_power(geo_cond)


@router.get("/geo/protection", status_code=200)
async def geo_protection_endpoint(
    lat: float,
    lng: float,
    geo_service: GeoService = Depends(get_geo_service),
):
    geo_cond = GeoCond(lat=lat, lng=lng)
    return await geo_service.get_protected_areas(geo_cond)


@router.get("/geo/forest", status_code=200)
async def geo_forest_endpoint(
    lat: float,
    lng: float,
    geo_service: GeoService = Depends(get_geo_service),
):
    geo_cond = GeoCond(lat=lat, lng=lng)
    return await geo_service.get_forest(geo_cond)


@router.get("/geo/builtup", status_code=200)
async def geo_builtup_endpoint(
    lat: float,
    lng: float,
    geo_service: GeoService = Depends(get_geo_service),
):
    geo_cond = GeoCond(lat=lat, lng=lng)
    return await geo_service.get_buildings_in_area(geo_cond)
