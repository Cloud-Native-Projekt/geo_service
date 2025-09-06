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

    async def get_power(self, lat: float, lng: float) -> ResultPower:
        nearest_powerline_distance_m = 0
        nearest_substation_distance_m = 0

        poi_id = self.nominatim.query(lat, lng, reverse=True, zoom=10).areaId()
        poi_gdf = (
            gpd.GeoDataFrame({"geometry": [Point(lng, lat)]})
            .set_crs("EPSG:4326")
            .to_crs("EPSG:3857")
        )

        query = overpassQueryBuilder(
            area=poi_id,
            elementType=["node"],
            selector='"power"="substation"',
            includeGeometry=True,
        )
        result = self.overpass.query(query)

        substation_coords = []

        if len(result.elements()) > 0:
            for substation in result.elements():
                geom = Geometry.from_geojson(substation.geometry())
                substation_coords.append((geom.x, geom.y))
            substation_df = pd.DataFrame(substation_coords, columns=["longitude", "latitude"])
            substation_df["geometry"] = substation_df.apply(
                lambda row: Point(row["longitude"], row["latitude"]), axis=1
            )
            substation_gdf = (
                gpd.GeoDataFrame(substation_df, geometry="geometry")
                .set_crs("EPSG:4326")
                .to_crs("EPSG:3857")
            )
            sub_distances = gpd.sjoin_nearest(
                poi_gdf,
                substation_gdf,
                how="inner",
                distance_col="distance",
                # max distance 10km
                max_distance=10000,
            )
            if not sub_distances.empty:
                nearest_substation_distance_m = sub_distances["distance"].min()

        query = overpassQueryBuilder(
            area=poi_id,
            elementType=["way"],
            selector=[
                '"line"="busbar"',
                '"power"="line"'
                ],
            includeGeometry=True,
        )
        result = self.overpass.query(query)

        p_lines_coords = []
        if len(result.elements()) > 0:

            for p_line in result.elements():
                geom = Geometry.from_geojson(p_line.geometry())
                p_lines_coords.append(geom)

            p_line_gdf = (
                gpd.GeoDataFrame(geometry=p_lines_coords)
                .set_crs("EPSG:4326")
                .to_crs("EPSG:3857")
            )

            p_line_distances = gpd.sjoin_nearest(
                poi_gdf,
                p_line_gdf,
                how="inner",
                distance_col="distance",
                max_distance=10000,
            )
            if not p_line_distances.empty:
                nearest_powerline_distance_m = \
                    p_line_distances["distance"].min()
        return ResultPower(
            nearest_substation_distance_m=nearest_substation_distance_m,
            nearest_powerline_distance_m=nearest_powerline_distance_m,
        )

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
                designation=None,
            )

    async def get_buildings_in_area(
        self, lat: float, lng: float
    ) -> ResultBuildings:
        poi = self.nominatim.query(lat, lng, reverse=True, zoom=12).areaId()
        landuse_types = ["residential",
                         "construction",
                         "education",
                         "fairground",
                         "industrial",
                         "retail",
                         "commercial",
                         "institutional"
                         ]
        for type in landuse_types:
            query = overpassQueryBuilder(
                area=poi,
                elementType=["way", "relation"],
                selector=f'"landuse"="{type}"',
                includeGeometry=False,
                out='count'
            )
            result = self.overpass.query(query)
            if result.countElements() > 0:
                return ResultBuildings(
                    in_populated_area=True
                )
        return ResultBuildings(
                in_populated_area=False,
            )

    async def get_forest(self, lat: float, lng: float) -> ResultForest:
        poi = self.nominatim.query(lat, lng, reverse=True, zoom=12).areaId()
        forest_types = [
            '"landuse"="forest"',
            '"natural"="wood"',
            '"landcover"="trees"'
            ]
        for forest_type in forest_types:
            query = overpassQueryBuilder(
                area=poi,
                elementType=["way", "relation", "node"],
                selector=[
                    f'{forest_type}'
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
            return ResultForest(
                in_forest=False,
                type=None,
            )
