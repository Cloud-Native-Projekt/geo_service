import logging
from geo_service.repositories.interfaces.iface_geo_repo import GeoRepoInterface
from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import Overpass, overpassQueryBuilder
import requests
import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context

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
        self.nominatim = Nominatim()

    async def get_power(self, lat: float, lng: float) -> ResultPower:
        return ResultPower(
            nearest_substation_distance_m=1,
            nearest_powerline_distance_m=1,
        )
          
         
        """
      poi_id = self.nominatim.query(lat, lng, reverse=True).areaId()
        query = overpassQueryBuilder(
            area=poi_id,
            elementType=["way", "relation"],
            selector='"boundary"="protected_area"',
            zoom=12,  # zoom level: town / borough
            includeGeometry=True,
        )
        result = self.overpass.query(query)
        if result.countElements() > 0:
            substation = result.elements()[0]
            s_geom = shapely.from_geojson(substation.geometry())
            #s_geom.distance(POINt...)

        query = overpassQueryBuilder(
            area=poi_id,
            elementType=["way", "relation"],
            selector='"boundary"="protected_area"',
            includeGeometry=True,
        )
        if result.countElements() > 0:
            power_line = result.elements()[0]
        """ 

    async def get_protected_areas(
        self, lat: float, lng: float
    ) -> ResultProtection:
        # zoom=14: neighbourhood
        poi = self.nominatim.query(lat, lng, reverse=True, zoom=14).areaId()
        query = overpassQueryBuilder(
            area=poi,
            elementType=["way", "relation"],
            selector='"boundary"="protected_area"',
            includeGeometry=False,
        )
        result = self.overpass.query(query)
        if len(result.elements()) > 0:
            area = result.elements()[0]
            return ResultProtection(
                in_protected_area=True,
                designation=area.tags().get('protection_title'),
            )
        else:
            return ResultProtection(
                in_protected_area=False,
                designation="None"
            )

    async def get_buildings_in_area(
        self, lat: float, lng: float
    ) -> ResultBuildings:
        poi = self.nominatim.query(lat, lng, reverse=True).areaId()
        query = overpassQueryBuilder(
            area=poi,
            elementType=["way", "relation"],
            selector='"boundary"="protected_area"',
            includeGeometry=False,
        )
        result = self.overpass.query(query)
        if result.countElements() > 0:
            return ResultBuildings(
                in_populated_area=True
            )
        else:
            return ResultBuildings(
                in_populated_area=False,
            )
        return ResultBuildings(
            in_building_area=False,
        )

    async def get_forest(self, lat: float, lng: float) -> ResultForest:
        poi = self.nominatim.query(lat, lng, reverse=True, zoom=12).areaId()
        query = overpassQueryBuilder(
            area=poi,
            elementType=["way", "relation", "node"],
            selector=[
                '"natural"="wood"',
                '"landuse"="forest"',
                '"landcover"="trees"'
                ],
            includeGeometry=False,
        )
        result = self.overpass.query(query)
        if len(result.elements()) > 0:
            forest = result.elements()[0]
            return ResultForest(
                in_forest=True,
                type=forest.tags().get('leaf_type'),
            )
        else:
            return ResultForest(
                in_forest=False,
                type="None",
            )
