from abc import ABC, abstractmethod

import geo_service.schemas.geo_schemas as schemas


class GeoRepoInterface(ABC):

    @abstractmethod
    async def get_power(
        self, lat: float, lng: float, radius: int
    ) -> schemas.ResultPower:
        pass

    @abstractmethod
    async def get_protected_areas(
        self, lat: float, lng: float, radius: int
    ) -> schemas.ResultProtection:
        pass

    @abstractmethod
    async def get_buildings_in_area(
        self, lat: float, lng: float, radius: int
    ) -> schemas.ResultBuildings:
        pass

    @abstractmethod
    async def get_forest(
        self, lat: float, lng: float, radius: int
    ) -> schemas.ResultForest:
        pass
