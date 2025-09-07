import logging
from geo_service.repositories.interfaces.iface_geo_repo import GeoRepoInterface
from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import Overpass, overpassQueryBuilder
import ssl
from plpygis import Geometry
from shapely.geometry import Point
import geopandas as gpd
import pandas as pd

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
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

    def _get_geometry_from_overpass(self, lat:float, lng:float, element_type, selector, additional_info:list = None):
        poi_id = self.nominatim.query(lat, lng, reverse=True, zoom=10).areaId()
        query = overpassQueryBuilder(
            area=poi_id,
            elementType=element_type,
            selector=selector,
            includeGeometry=True,
        )
        result = self.overpass.query(query)      
        info = []
        coords = []
        if len(result.elements()) > 0:
            for element in result.elements():
                geom = Geometry.from_geojson(element.geometry())
                coords.append(geom)
            if additional_info == "protected_area":
                designation = element.tags().get('protection_title')
                if designation:
                    info.append(designation)
                else:
                    info.append("Unknown")
            elif additional_info == "forests":
                leaf_type = element.tags().get('leaf_type')
                if leaf_type:
                    info.append(leaf_type)
                else:
                    info.append("Unknown")
        return coords, info

    def _calculate_nearest_distance(self, lat: float, lng: float, geometry_coords, additional_info = None):
        corresponding_info = None
        min_distance = 0
        poi_gdf = (
            gpd.GeoDataFrame({"geometry": [Point(lng, lat)]})
            .set_crs("EPSG:4326")
            .to_crs("EPSG:3857")
        )      
        # Create a GeoDataFrame from the geometries
        geom_gdf = (
            gpd.GeoDataFrame(geometry=geometry_coords)
            .set_crs("EPSG:4326")
            .to_crs("EPSG:3857")
        )

        distances = gpd.sjoin_nearest(
            poi_gdf,
            geom_gdf,
            how="inner",
            distance_col="distance",
        )
        
        if not distances.empty:
            min_distance_index = distances['distance'].idxmin()
            min_distance_row = distances.loc[min_distance_index]
            min_distance = min_distance_row['distance']
            if additional_info:
                corresponding_info = additional_info[min_distance_index]
        return min_distance, corresponding_info

    async def get_power(self, lat: float, lng: float, radius: int) -> ResultPower:
        nearest_powerline_distance_m = 0
        nearest_substation_distance_m = 0
        # Substation distance calculation
        substation_coords, _ = self._get_geometry_from_overpass(
            lat,
            lng,
            element_type="node",
            selector=['"power"="substation"'],
            additional_info=None
        )
        nearest_substation_distance_m, _ = self._calculate_nearest_distance(lat, lng, substation_coords, None)

        # Powerline distance calculation
        powerline_coords, _ = self._get_geometry_from_overpass(
            lat,
            lng,
            element_type="way",
            selector=['"line"="busbar"', '"power"="line"'],
            additional_info=None
        )
        nearest_powerline_distance_m, _ = self._calculate_nearest_distance(lat, lng, powerline_coords, None)
        if nearest_powerline_distance_m > radius:
            nearest_powerline_distance_m = 0
        if nearest_substation_distance_m > radius:
            nearest_substation_distance_m = 0
        return ResultPower(
            nearest_substation_distance_m=nearest_substation_distance_m,
            nearest_powerline_distance_m=nearest_powerline_distance_m,
        )

    async def get_protected_areas(self, lat: float, lng: float, radius: int) -> ResultProtection:
        area_coords, designations = self._get_geometry_from_overpass(
            lat,
            lng,
            element_type=["way", "relation"],
            selector=['"boundary"="protected_area"'],
            additional_info="protected_area"
        )           
        if len(area_coords) > 0:
            distance, designation = self._calculate_nearest_distance(lat, lng, area_coords, designations)
            if distance < radius:
                return ResultProtection(
                    in_protected_area=True,
                    designation=designation,
                )
        return ResultProtection(
            in_protected_area=False,
            designation=None,
        )

    async def get_buildings_in_area(self, lat: float, lng: float, radius: int) -> ResultBuildings:
        landuse_types = [
            "residential", "construction", "education", "fairground",
            "industrial", "retail", "commercial", "institutional"
        ]
        for landuse in landuse_types:
            landuse_coords, _ = self._get_geometry_from_overpass(
                lat,
                lng,
                element_type=["way", "relation"],
                selector=f'"landuse"="{landuse}"',
                additional_info=None
            )       
            if len(landuse_coords) > 0:
                distance, _ = self._calculate_nearest_distance(lat, lng, landuse_coords, None)
                if distance < radius:
                    return ResultBuildings(in_populated_area=True)
        return ResultBuildings(in_populated_area=False)

    async def get_forest(self, lat: float, lng: float, radius: int) -> ResultForest:
        forest_types = ['"natural"="wood"','"landuse"="forest"',]
        for forest_type in forest_types:
            forest_coords, leaf_types = self._get_geometry_from_overpass(
                lat,
                lng,
                element_type=["node", "relation", "way"],
                selector=f"{forest_type}",
                additional_info="forests",
            )
            if len(forest_coords) > 0:
                distance, leaf_type = self._calculate_nearest_distance(
                    lat, lng, forest_coords, leaf_types
                )
            if distance < radius:
                return ResultForest(
                    in_forest=True,
                    type=leaf_type,
                )
        return ResultForest(in_forest=False, type=None)