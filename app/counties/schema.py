from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CountyResponse(BaseModel):
    id: UUID
    name: str
    latitude: float
    longitude: float

    model_config = ConfigDict(from_attributes=True)


class ConstituencyResponse(BaseModel):
    id: UUID
    code: int
    name: str
    county_id: UUID
    latitude: float
    longitude: float

    model_config = ConfigDict(from_attributes=True)


class WardResponse(BaseModel):
    id: UUID
    code: int
    name: str
    constituency_id: UUID

    model_config = ConfigDict(from_attributes=True)


class LocationMatchResponse(BaseModel):
    """Nearest administrative match for coordinates; approximate by design."""

    county: CountyResponse
    constituency: ConstituencyResponse
    wards: list[WardResponse]
    distance_km: float
    approximate: bool = True
