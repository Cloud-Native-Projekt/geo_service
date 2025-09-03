from pydantic import BaseModel


class GeoCond(BaseModel):
    lat: float
    lng: float


class ResultPower(BaseModel):
    nearest_substation_distance_m: float
    nearest_powerline_distance_m: float


class ResultProtection(BaseModel):
    in_protected_area: bool
    designation: str = None


class ResultForest(BaseModel):
    type: str = None
    in_forest: bool


class ResultBuildings(BaseModel):
    in_populated_area: bool = None
    
