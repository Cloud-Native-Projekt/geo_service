import logging
import ssl
from typing import Any, List, Optional, Tuple, Union

import geopandas as gpd
import geopy.distance
from geopy import Point as GeopyPoint
from OSMPythonTools.overpass import Overpass, overpassQueryBuilder
from plpygis import Geometry
from shapely.geometry import Point

from geo_service.repositories.interfaces.iface_geo_repo import GeoRepoInterface
from geo_service.schemas.geo_schemas import (
    ResultBuildings,
    ResultForest,
    ResultPower,
    ResultProtection,
)

# SSL context setup for OSMPythonTools
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context


class GeoRepo(GeoRepoInterface):
    """
    Repository implementation for geographic queries using Overpass API and
    geospatial libraries.
    Provides methods to query power infrastructure, protected areas, buildings,
    and forests around a given latitude and longitude.
    """

    def __init__(self) -> None:
        """
        Initialize the GeoRepo instance, set up logging and
        Overpass API client.
        """
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        self.overpass = Overpass()

    def _create_bounding_box(
        self, lat: float, lng: float, distance: float
    ) -> Tuple[float, float, float, float]:
        """
        Create a bounding box around a given latitude and longitude.

        Parameters:
            lat (float): Latitude of the center point.
            lng (float): Longitude of the center point.
            distance (float): Distance from the center point in meters.

        Returns:
            tuple: (min_lat, min_lon, max_lat, max_lon)
        """
        distance_km = distance / 1000.0  # Convert meters to kilometers
        if distance_km > 0:
            distance_km = 5  # Limit to 5 km for Overpass API performance
        center_point = GeopyPoint(lat, lng)

        north_point = geopy.distance.geodesic(kilometers=distance_km).\
            destination(
            center_point, 0
        )
        south_point = geopy.distance.geodesic(kilometers=distance_km).\
            destination(
            center_point, 180
        )
        east_point = geopy.distance.geodesic(kilometers=distance_km).\
            destination(
            center_point, 90
        )
        west_point = geopy.distance.geodesic(kilometers=distance_km).\
            destination(
            center_point, 270
        )

        min_lat = south_point.latitude
        max_lat = north_point.latitude
        min_lon = west_point.longitude
        max_lon = east_point.longitude

        return min_lat, min_lon, max_lat, max_lon

    def _get_geometry_from_overpass(
        self,
        lat: float,
        lng: float,
        radius: int,
        element_type: Union[str, List[str]],
        selector: Union[str, List[str]],
        additional_info: Optional[str] = None,
    ) -> Tuple[List[Any], List[str]]:
        """
        Query Overpass API for geographic elements and extract their 
        geometries.

        Parameters:
            lat (float): Latitude of the center point.
            lng (float): Longitude of the center point.
            radius (int): Search radius in meters.
            element_type (str or list): OSM element type(s) to query.
            selector (str or list): OSM selector(s) for filtering elements.
            additional_info (str, optional): Type of additional info to 
            extract.

        Returns:
            tuple: (list of geometries, list of additional info strings)
        """
        bbox = self._create_bounding_box(lat, lng, radius)
        query = overpassQueryBuilder(
            bbox=bbox,
            elementType=element_type,
            selector=selector,
            includeGeometry=True,
        )
        result = self.overpass.query(query)
        info: List[str] = []
        coords: List[Any] = []
        for element in result.elements():
            geom = Geometry.from_geojson(element.geometry())
            coords.append(geom)
            if additional_info == "protected_area":
                designation = element.tags().get("protection_title")
                info.append(designation if designation else "Unknown")
            elif additional_info == "forests":
                leaf_type = element.tags().get("leaf_type")
                info.append(leaf_type if leaf_type else "Unknown")
        return coords, info

    def _calculate_nearest_distance(
        self,
        lat: float,
        lng: float,
        geometry_coords: List[Any],
        additional_info: Optional[List[str]] = None,
    ) -> Tuple[float, Optional[str]]:
        """
        Calculate the nearest distance from a point to a list of geometries.

        Parameters:
            lat (float): Latitude of the reference point.
            lng (float): Longitude of the reference point.
            geometry_coords (list): List of geometry objects.
            additional_info (list, optional): List of additional info strings.

        Returns:
            tuple: (minimum distance in meters, corresponding additional info)
        """
        corresponding_info: Optional[str] = None
        min_distance: float = 0.0
        poi_gdf = (
            gpd.GeoDataFrame({"geometry": [Point(lng, lat)]})
            .set_crs("EPSG:4326")
            .to_crs("EPSG:3857")
        )
        geom_gdf = (
            gpd.GeoDataFrame({"geometry": geometry_coords})
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
            min_distance_index = distances["distance"].idxmin()
            min_distance_row = distances.loc[min_distance_index]
            min_distance = min_distance_row["distance"]
            if additional_info:
                corresponding_info = additional_info[min_distance_index]
        return min_distance, corresponding_info

    async def get_power(
        self, lat: float, lng: float, radius: int
    ) -> ResultPower:
        """
        Get the nearest power substation and powerline distances from a point.

        Parameters:
            lat (float): Latitude of the center point.
            lng (float): Longitude of the center point.
            radius (int): Search radius in meters.

        Returns:
            ResultPower: Result object with nearest distances.
        """
        substation_coords, _ = self._get_geometry_from_overpass(
            lat,
            lng,
            radius,
            element_type="node",
            selector=['"power"="substation"'],
            additional_info=None,
        )
        nearest_substation_distance_m, _ = self._calculate_nearest_distance(
            lat, lng, substation_coords, None
        )

        powerline_coords, _ = self._get_geometry_from_overpass(
            lat,
            lng,
            radius,
            element_type="way",
            selector=['"line"="busbar"', '"power"="line"'],
            additional_info=None,
        )
        nearest_powerline_distance_m, _ = self._calculate_nearest_distance(
            lat, lng, powerline_coords, None
        )

        if nearest_powerline_distance_m > radius:
            nearest_powerline_distance_m = 0
        if nearest_substation_distance_m > radius:
            nearest_substation_distance_m = 0

        return ResultPower(
            nearest_substation_distance_m=nearest_substation_distance_m,
            nearest_powerline_distance_m=nearest_powerline_distance_m,
        )

    async def get_protected_areas(
        self, lat: float, lng: float, radius: int
    ) -> ResultProtection:
        """
        Check if a point is within a protected area and get its designation.

        Parameters:
            lat (float): Latitude of the center point.
            lng (float): Longitude of the center point.
            radius (int): Search radius in meters.

        Returns:
            ResultProtection: Result object with protected area info.
        """
        area_coords, designations = self._get_geometry_from_overpass(
            lat,
            lng,
            radius,
            element_type=["way", "relation"],
            selector=['"boundary"="protected_area"'],
            additional_info="protected_area",
        )
        if area_coords:
            distance, designation = self._calculate_nearest_distance(
                lat, lng, area_coords, designations
            )
            if distance < radius:
                return ResultProtection(
                    in_protected_area=True,
                    designation=designation,
                )
        return ResultProtection(
            in_protected_area=False,
            designation=None,
        )

    async def get_buildings_in_area(
        self, lat: float, lng: float, radius: int
    ) -> ResultBuildings:
        """
        Check if a point is within a populated area (buildings/landuse).

        Parameters:
            lat (float): Latitude of the center point.
            lng (float): Longitude of the center point.
            radius (int): Search radius in meters.

        Returns:
            ResultBuildings: Result object indicating populated area status.
        """
        landuse_types = [
            "residential",
            "construction",
            "industrial",
            "retail",
            "commercial",
        ]
        for landuse in landuse_types:
            landuse_coords, _ = self._get_geometry_from_overpass(
                lat,
                lng,
                radius,
                element_type=["way", "relation"],
                selector=f'"landuse"="{landuse}"',
                additional_info=None,
            )
            if landuse_coords:
                distance, _ = self._calculate_nearest_distance(
                    lat, lng, landuse_coords, None
                )
                if distance < radius:
                    return ResultBuildings(in_populated_area=True)
        return ResultBuildings(in_populated_area=False)

    async def get_forest(
        self, lat: float, lng: float, radius: int
    ) -> ResultForest:
        """
        Check if a point is within a forest and get its leaf type.

        Parameters:
            lat (float): Latitude of the center point.
            lng (float): Longitude of the center point.
            radius (int): Search radius in meters.

        Returns:
            ResultForest: Result object with forest leaf type (mixed,
            broadleaf etc.) info.
        """
        forest_types = ['"natural"="wood"', '"landuse"="forest"']
        for forest_type in forest_types:
            forest_coords, leaf_types = self._get_geometry_from_overpass(
                lat,
                lng,
                radius,
                element_type=["node", "relation", "way"],
                selector=forest_type,
                additional_info="forests",
            )
            if forest_coords:
                distance, leaf_type = self._calculate_nearest_distance(
                    lat, lng, forest_coords, leaf_types
                )
                if distance < radius:
                    return ResultForest(
                        in_forest=True,
                        type=leaf_type,
                    )
        return ResultForest(in_forest=False, type=None)
