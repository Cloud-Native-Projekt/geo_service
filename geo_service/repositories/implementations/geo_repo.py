import logging
import os
import ssl
import time
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
    ResultHealth,
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

LOGLEVEL = os.getenv("LOGLEVEL", "INFO")


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
            level=LOGLEVEL,
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

        north_point = geopy.distance.geodesic(kilometers=distance_km).destination(
            center_point, 0
        )
        south_point = geopy.distance.geodesic(kilometers=distance_km).destination(
            center_point, 180
        )
        east_point = geopy.distance.geodesic(kilometers=distance_km).destination(
            center_point, 90
        )
        west_point = geopy.distance.geodesic(kilometers=distance_km).destination(
            center_point, 270
        )

        min_lat = south_point.latitude
        max_lat = north_point.latitude
        min_lon = west_point.longitude
        max_lon = east_point.longitude

        return min_lat, min_lon, max_lat, max_lon

    def _get_data_from_overpass(
        self,
        lat: float,
        lng: float,
        radius: int,
        element_type: Union[str, List[str]],
        selector: Union[str, List[str]],
        additional_info: Optional[str] = None,
        include_geometry: bool = True,
        el_limit: bool = False,
    ) -> Tuple[List[Any], str]:
        """
        Query Overpass API for geographic elements and extract their
        geometries and/or additional info.

        Parameters:
            lat (float): Latitude of the center point.
            lng (float): Longitude of the center point.
            radius (int): Search radius in meters.
            element_type (str or list): OSM element type(s) to query.
            selector (str or list): OSM selector(s) for filtering elements.
            additional_info (str, optional): Type of additional info to extract
                (e.g., "protected_area" or "forests").
            include_geometry (bool): Whether to include geometry in the query.
            el_limit (bool): Whether to limit the number of elements returned for performance.

        Returns:
            tuple: (
                list of geometries or list with a single string with
                True if no geometries requested and elements found,
                additional info string
            )
        """
        bbox = self._create_bounding_box(lat, lng, radius)
        if el_limit:
            out_str = "body 1"
        else:
            out_str = ""
        query = overpassQueryBuilder(
            bbox=bbox,
            elementType=element_type,
            selector=selector,
            includeGeometry=include_geometry,
            out=out_str,
        )
        attempt = 0
        for attempt in range(2):
            try:
                result = self.overpass.query(query)
                break
            except Exception as e:
                self.logger.error(f"Overpass query attempt {attempt + 1} failed: {e}")
                if attempt == 0 and "504" in str(e):
                    self.logger.info(
                        "Retrying Overpass query after 2 seconds due to 504 error."
                    )
                    time.sleep(2)
                else:
                    return [False], ""

        info: str = ""
        coords: List[Any] = []

        if result.countElements() > 0:
            if include_geometry:
                for element in result.elements():
                    geom = Geometry.from_geojson(element.geometry())
                    coords.append(geom)
            else:
                coords.append(True)  # True to indicate presence of elements
            if additional_info:
                if additional_info == "protected_area":
                    designation = result.elements()[0].tags().get("protection_title")
                    info = designation if designation else "Unknown"
                elif additional_info == "forests":
                    leaf_type = result.elements()[0].tags().get("leaf_type")
                    info = leaf_type if leaf_type else "Unknown"
        else:
            self.logger.info("No elements found in Overpass query.")
            coords.append(False)
        return coords, info

    def _calculate_nearest_distance(
        self,
        lat: float,
        lng: float,
        geometry_coords: List[Any],
        additional_info: Optional[List[str]] = None,
    ) -> float:
        """
        Calculate the nearest distance from a point to a list of geometries.

        Parameters:
            lat (float): Latitude of the reference point.
            lng (float): Longitude of the reference point.
            geometry_coords (list): List of geometry objects.
            additional_info (list, optional): List of additional info strings.

        Returns:
            float: Minimum distance in meters.
        """
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
        else:
            self.logger.info("No geometries found for distance calculation.")
        return min_distance

    async def get_health(self) -> ResultHealth:
        """
        Check the health status of the GeoRepo service.

        Returns:
            ResultHealth: Result object indicating service health status.
        """
        return ResultHealth(status="healthy", message="Service is operational.")

    async def get_power(self, lat: float, lng: float, radius: int) -> ResultPower:
        """
        Get the nearest power substation (using a fixed 10 km radius) and powerline distances from a point.

        Parameters:
            lat (float): Latitude of the center point.
            lng (float): Longitude of the center point.
            radius (int): Search radius in meters (powerlines, substations use fixed 10 km radius).

        Returns:
            ResultPower: Result object with nearest distances.
        """
        substation_coords, _ = self._get_data_from_overpass(
            lat,
            lng,
            10000,  # Fixed 10 km radius for power infrastructure
            element_type="node",
            selector=['"power"="substation"'],
            additional_info=None,
            include_geometry=True,
            el_limit=False,
        )
        if substation_coords[0]:
            nearest_substation_distance_m = self._calculate_nearest_distance(
                lat, lng, substation_coords, None
            )
        else:
            nearest_substation_distance_m = 0.0

        if nearest_substation_distance_m == 0.0:
            self.logger.info("No substations found.")

        powerline_coords, _ = self._get_data_from_overpass(
            lat,
            lng,
            radius,
            element_type="way",
            selector=['"line"="busbar"', '"power"="line"'],
            additional_info=None,
            include_geometry=True,
            el_limit=False,
        )
        if powerline_coords[0]:
            nearest_powerline_distance_m = self._calculate_nearest_distance(
                lat, lng, powerline_coords, None
            )
        else:
            nearest_powerline_distance_m = 0.0
        if nearest_powerline_distance_m == 0.0:
            self.logger.info("No powerlines found.")

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
        area_coords, designation = self._get_data_from_overpass(
            lat,
            lng,
            radius,
            element_type=["way", "relation"],
            selector=['"boundary"="protected_area"'],
            additional_info="protected_area",
            include_geometry=False,
            el_limit=True,
        )
        if area_coords[0]:
            return ResultProtection(
                in_protected_area=True,
                designation=designation,
            )
        else:
            self.logger.info("No protected areas found within radius.")
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
        landuse_coords, _ = self._get_data_from_overpass(
            lat,
            lng,
            radius,
            element_type=["way", "relation"],
            selector=[
                '"landuse"="residential"',
                '"landuse"="construction"',
                '"landuse"="industrial"',
                '"landuse"="retail"',
                '"landuse"="commercial"',
            ],
            additional_info=None,
            include_geometry=False,
            el_limit=True,
        )
        if landuse_coords[0]:
            return ResultBuildings(in_populated_area=True)
        else:
            self.logger.info("No buildings found within radius.")
        return ResultBuildings(in_populated_area=False)

    async def get_forest(self, lat: float, lng: float, radius: int) -> ResultForest:
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
        forest_coords, leaf_type = self._get_data_from_overpass(
            lat,
            lng,
            radius,
            element_type=["node", "relation", "way"],
            selector=['"natural"="wood"', '"landuse"="forest"'],
            additional_info="forests",
            include_geometry=False,
            el_limit=True,
        )
        if forest_coords[0] != 0:
            return ResultForest(
                in_forest=True,
                type=leaf_type,
            )
        else:
            self.logger.info("No forests found within radius.")
        return ResultForest(in_forest=False, type=None)
