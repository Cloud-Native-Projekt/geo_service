from abc import ABC, abstractmethod

import geo_service.schemas.geo_schemas as schemas


class GeoRepoInterface(ABC):
    """
    Interface for geographic repository operations.
    This abstract base class defines asynchronous methods for retrieving
    various geographic data
    within a specified radius around a latitude and longitude. Implementations
    should provide
    access to power data, protected areas, buildings, and forest information.
    Methods:
        get_power(lat, lng, radius): Retrieve power-related data for the
        specified area.
        get_protected_areas(lat, lng, radius): Retrieve protected area data
        for the specified area.
        get_buildings_in_area(lat, lng, radius): Retrieve building data for
        the specified area.
        get_forest(lat, lng, radius): Retrieve forest data for the specified
        area.
    """

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
