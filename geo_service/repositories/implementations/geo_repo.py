import asyncio
import logging
import os
import ssl
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
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

        # Fix OSMPythonTools cache directory issues
        try:
            # In Docker container, use app-writable cache directories
            home_cache = os.path.expanduser("~/.cache/OSMPythonTools")
            app_cache = "/app/cache" if os.path.exists("/app") else "cache"

            # Try home cache first, fallback to app cache
            for cache_path in [home_cache, app_cache]:
                try:
                    os.makedirs(cache_path, exist_ok=True)
                    # Test write permissions
                    test_file = os.path.join(cache_path, "test_write")
                    with open(test_file, "w") as f:
                        f.write("test")
                    os.remove(test_file)
                    self.logger.info(f"Using cache directory: {cache_path}")
                    break
                except (PermissionError, OSError) as pe:
                    self.logger.warning(f"Cache path {cache_path} not writable: {pe}")
                    continue

        except Exception as e:
            self.logger.warning(f"Cache directory setup warning: {e}")

        self.overpass = Overpass()
        self._executor = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="geo_worker"
        )

    def __del__(self) -> None:
        """Clean up thread pool on destruction."""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)

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
        if distance_km > 5:
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

    def _make_hashable_params(
        self, element_type: Union[str, List[str]], selector: Union[str, List[str]]
    ) -> Tuple[Union[str, Tuple[str, ...]], Union[str, Tuple[str, ...]]]:
        """Convert lists to tuples for hashability in caching."""
        hashable_element_type = (
            tuple(element_type) if isinstance(element_type, list) else element_type
        )
        hashable_selector = tuple(selector) if isinstance(selector, list) else selector
        return hashable_element_type, hashable_selector

    # LRU cache for faster in-memory access to frequently used results
    @lru_cache(maxsize=128)
    def _get_data_from_overpass_cached(
        self,
        lat: float,
        lng: float,
        radius: int,
        element_type: Union[str, Tuple[str, ...]],
        selector: Union[str, Tuple[str, ...]],
        additional_info: Optional[str] = None,
        include_geometry: bool = True,
        el_limit: bool = False,
    ) -> Tuple[List[Any], str]:
        """Cached version with hashable parameters."""
        # Convert back to lists for processing
        element_type_list = (
            list(element_type) if isinstance(element_type, tuple) else element_type
        )
        selector_list = list(selector) if isinstance(selector, tuple) else selector

        return self._get_data_from_overpass_sync(
            lat,
            lng,
            radius,
            element_type_list,
            selector_list,
            additional_info,
            include_geometry,
            el_limit,
        )

    def _get_data_from_overpass_sync(
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
        Synchronous version of Overpass query for use in thread pools.
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
            el_limit (bool): Whether to limit the number of elements returned
                for performance.

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

        # Retry logic with blocking sleep (safe in thread)
        for attempt in range(2):
            try:
                result = self.overpass.query(query)
                break
            except Exception as e:
                error_str = str(e).lower()
                self.logger.error(f"Overpass query attempt {attempt + 1} failed: {e}")

                # Handle cache directory issues
                if "file exists" in error_str and "cache" in error_str:
                    try:
                        # Try to fix cache directory issue
                        if os.path.exists("cache") and not os.path.isdir("cache"):
                            os.remove("cache")
                        os.makedirs("cache", exist_ok=True)
                    except Exception as cache_e:
                        self.logger.warning(f"Cache fix attempt failed: {cache_e}")

                if attempt == 0 and ("504" in error_str or "file exists" in error_str):
                    self.logger.info(
                        "Retrying Overpass query after 2 seconds due to error."
                    )
                    time.sleep(2)  # Safe blocking sleep in thread
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

    async def _get_data_from_overpass(
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
        Async wrapper that runs the cached Overpass query in a thread pool.
        """
        # Make parameters hashable for caching
        hashable_element_type, hashable_selector = self._make_hashable_params(
            element_type, selector
        )

        return await asyncio.to_thread(
            self._get_data_from_overpass_cached,
            lat,
            lng,
            radius,
            hashable_element_type,
            hashable_selector,
            additional_info,
            include_geometry,
            el_limit,
        )

    def _calculate_nearest_distance_sync(
        self,
        lat: float,
        lng: float,
        geometry_coords: List[Any],
    ) -> float:
        """
        Synchronous version of distance calculation for use in thread pools.
        Calculate the nearest distance from a point to a list of geometries.

        Parameters:
            lat (float): Latitude of the reference point.
            lng (float): Longitude of the reference point.
            geometry_coords (list): List of geometry objects.

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

    async def _calculate_nearest_distance(
        self,
        lat: float,
        lng: float,
        geometry_coords: List[Any],
    ) -> float:
        """
        Async wrapper that runs the sync distance calculation in a thread pool.
        """
        return await asyncio.to_thread(
            self._calculate_nearest_distance_sync,
            lat,
            lng,
            geometry_coords,
        )

    async def get_health(self) -> ResultHealth:
        """
        Check the health status of the GeoRepo service.

        Returns:
            ResultHealth: Result object indicating service health status.
        """
        return ResultHealth(status="healthy", message="Service is operational.")

    async def get_power(self, lat: float, lng: float, radius: int) -> ResultPower:
        """
        Get the nearest power substation (using a fixed 10 km radius) and
        powerline distances from a point.

        Parameters:
            lat (float): Latitude of the center point.
            lng (float): Longitude of the center point.
            radius (int): Search radius in meters (powerlines, substations use
                         fixed 10 km radius).

        Returns:
            ResultPower: Result object with nearest distances.
        """
        # Concurrent queries for substations and power lines
        substation_task = self._get_data_from_overpass(
            lat,
            lng,
            10000,
            element_type="node",
            selector='"power"="substation"',
            additional_info=None,
            include_geometry=True,
            el_limit=False,
        )

        powerline_task = self._get_data_from_overpass(
            lat,
            lng,
            radius,
            element_type="way",
            selector=['"power"="line"', '"line"="busbar"'],
            additional_info=None,
            include_geometry=True,
            el_limit=False,
        )

        substation_result: Any
        powerline_result: Any
        substation_result, powerline_result = await asyncio.gather(
            substation_task, powerline_task, return_exceptions=True
        )

        # Extract coords from results
        substation_coords = (
            substation_result[0]
            if isinstance(substation_result, tuple) and len(substation_result) > 0
            else substation_result
        )
        powerline_coords = (
            powerline_result[0]
            if isinstance(powerline_result, tuple) and len(powerline_result) > 0
            else powerline_result
        )

        # Calculate distances concurrently
        if substation_coords and substation_coords is not False:
            substation_distance_task = self._calculate_nearest_distance(
                lat, lng, substation_coords
            )
        else:

            async def zero_distance():
                return 0.0

            substation_distance_task = zero_distance()

        if powerline_coords and powerline_coords is not False:
            powerline_distance_task = self._calculate_nearest_distance(
                lat, lng, powerline_coords
            )
        else:

            async def zero_distance():
                return 0.0

            powerline_distance_task = zero_distance()

        nearest_substation_distance_m, nearest_powerline_distance_m = (
            await asyncio.gather(substation_distance_task, powerline_distance_task)
        )

        if nearest_substation_distance_m == 0.0:
            self.logger.info("No substations found or distance calculation failed.")
        if nearest_powerline_distance_m == 0.0:
            self.logger.info("No powerlines found or distance calculation failed.")

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
        area_coords, designation = await self._get_data_from_overpass(
            lat,
            lng,
            radius,
            element_type=["way", "relation"],
            selector=['"boundary"="protected_area"'],
            additional_info="protected_area",
            include_geometry=False,
            el_limit=True,
        )
        if area_coords and area_coords[0] is not False:
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
        landuse_coords, _ = await self._get_data_from_overpass(
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
        if landuse_coords and landuse_coords[0] is not False:
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
        forest_coords, leaf_type = await self._get_data_from_overpass(
            lat,
            lng,
            radius,
            element_type=["node", "relation", "way"],
            selector=['"natural"="wood"', '"landuse"="forest"'],
            additional_info="forests",
            include_geometry=False,
            el_limit=True,
        )
        if forest_coords and forest_coords[0] is not False:
            return ResultForest(
                in_forest=True,
                type=leaf_type,
            )
        else:
            self.logger.info("No forests found within radius.")
        return ResultForest(in_forest=False, type=None)
