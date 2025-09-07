from pydantic import BaseModel
from typing import Optional


class GeoCond(BaseModel):
    lat: float
    lng: float
    radius: Optional[int] = 10000


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
