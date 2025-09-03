from abc import ABC, abstractmethod

import geo_service.schemas.geo_schemas as schemas


class GeoRepoInterface(ABC):

    @abstractmethod
    async def get_power_infrastructure(
        self, lat: float, lng: float
    ) -> schemas.ResultPower:
        pass

    @abstractmethod
    async def get_protected_areas(
        self, lat: float, lng: float
    ) -> schemas.ResultProtection:
        pass

    @abstractmethod
    async def get_buildings_in_area(
        self, lat: float, lng: float
    ) -> schemas.ResultBuildings:
        pass

    @abstractmethod
    async def get_forest(
        self, lat: float, lng: float
    ) -> schemas.ResultForest:
        pass
