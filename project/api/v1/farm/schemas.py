from __future__ import annotations

from typing import Optional, List, Tuple, Dict, Any

from pydantic import BaseModel, Field, field_validator


class LatLong(BaseModel):
    lat: float
    lon: float

    @field_validator("lat")
    @classmethod
    def _lat_range(cls, v):
        if not (-90.0 <= float(v) <= 90.0):
            raise ValueError("Latitude must be between -90 and 90")
        return float(v)

    @field_validator("lon")
    @classmethod
    def _lon_range(cls, v):
        if not (-180.0 <= float(v) <= 180.0):
            raise ValueError("Longitude must be between -180 and 180")
        return float(v)


class FarmBase(BaseModel):
    name: str = Field(..., description="Farm name")
    country: str = Field(..., description="Country")
    state_province: str = Field(..., description="State or province")
    city: Optional[str] = Field(default=None, description="City where the farm is located")
    owner_name: Optional[str] = Field(default=None, description="Owner full name")
    notes: Optional[str] = Field(default=None, description="Notes")
    lat_long: Optional[Dict[str, Any] | Tuple[float, float] | List[float] | str | LatLong] = Field(
        default=None, description="GeoJSON Point or coercible input: 'lat,lon', [lat, lon], {lat, lon}"
    )

    @staticmethod
    def _coerce_geojson(v):
        if v is None or v == "":
            return None
        # If already GeoJSON Point
        if isinstance(v, dict) and v.get("type") == "Point" and isinstance(v.get("coordinates"), (list, tuple)) and len(v["coordinates"]) == 2:
            lon, lat = float(v["coordinates"][0]), float(v["coordinates"][1])
        elif isinstance(v, (list, tuple)) and len(v) == 2:
            lat, lon = float(v[0]), float(v[1])
        elif isinstance(v, str):
            parts = v.replace(" ", "").split(",")
            if len(parts) != 2:
                raise ValueError("lat_long must be 'lat,lon' or [lat, lon] or GeoJSON Point")
            lat, lon = float(parts[0]), float(parts[1])
        elif isinstance(v, dict):
            # dict with lat/lon keys
            lat = float(v.get("lat"))
            lon = float(v.get("lon"))
        elif isinstance(v, LatLong):
            lat, lon = float(v.lat), float(v.lon)
        else:
            raise ValueError("Invalid lat_long format")
        if not (-90.0 <= lat <= 90.0):
            raise ValueError("Latitude must be between -90 and 90")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError("Longitude must be between -180 and 180")
        return {"type": "Point", "coordinates": [lon, lat] }

    @field_validator("lat_long", mode="before")
    @classmethod
    def latlong_ok(cls, v):
        return cls._coerce_geojson(v)


class FarmCreate(FarmBase):
    pass


class FarmUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    state_province: Optional[str] = None
    city: Optional[str] = None
    owner_name: Optional[str] = None
    notes: Optional[str] = None
    lat_long: Optional[Dict[str, Any] | Tuple[float, float] | List[float] | str | LatLong] = None

    @field_validator("lat_long", mode="before")
    @classmethod
    def latlong_ok(cls, v):
        return FarmBase._coerce_geojson(v)


class FarmRead(FarmBase):
    id: Optional[str] = Field(default=None)
    owner_email: str
    shared_with: List[str] = []


class ShareRequest(BaseModel):
    add: Optional[List[str]] = Field(default=None, description="Emails to add to shared_with")
    remove: Optional[List[str]] = Field(default=None, description="Emails to remove from shared_with")
