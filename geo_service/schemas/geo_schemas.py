"""
geo_schemas.py
Pydantic models for geo-related service schemas, including conditions and
result types
for power infrastructure, protected areas, forests, and buildings.
Classes:
    GeoCond: Input conditions for geographic queries (latitude, longitude,
    radius).
    ResultPower: Output schema for nearest power infrastructure distances.
    ResultProtection: Output schema for protected area presence and
    designation.
    ResultForest: Output schema for forest type (mixed, broadleaf etc.)
    and presence.
    ResultBuildings: Output schema for populated area presence.
"""

from typing import Optional

from pydantic import BaseModel


class GeoCond(BaseModel):
    lat: float
    lng: float
    radius: Optional[int] = 5000


class ResultHealth(BaseModel):
    status: str
    message: Optional[str] = None


class ResultPower(BaseModel):
    nearest_substation_distance_m: float
    nearest_powerline_distance_m: float


class ResultProtection(BaseModel):
    in_protected_area: bool
    designation: Optional[str]


class ResultForest(BaseModel):
    type: Optional[str]
    in_forest: bool


class ResultBuildings(BaseModel):
    in_populated_area: bool = None
