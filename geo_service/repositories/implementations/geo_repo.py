import logging
from geo_service.repositories.interfaces.iface_geo_repo import GeoRepoInterface
from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import Overpass, overpassQueryBuilder
from plpygis import Geometry

from geo_service.schemas.geo_schemas import (
    ResultBuildings,
    ResultForest,
    ResultPower,
    ResultProtection,
)


class GeoRepo(GeoRepoInterface):
    def __init__(self) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        self.overpass = Overpass()

    async def get_power_infrastructure(self, lat: float, lng: float) -> ResultPower:
        return ResultPower (
            nearest_substation_distance_m = 1,
            nearest_powerline_distance_m = 1,
        )
        
            
    async def get_protected_areas(
        self, lat: float, lng: float
    ) -> ResultProtection:
        return ResultProtection(
            in_protected_area=False,
            designation="None"
        )

    async def get_buildings_in_area(
        self, lat: float, lng: float
    ) -> ResultBuildings:
        return ResultBuildings(
            in_building_area=False,
        )

    async def get_forest(self, lat: float, lng: float) -> ResultForest:
        return ResultForest(
            in_forest=False,
            type="None",
        )
