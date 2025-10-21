from __future__ import annotations

from typing import Optional, Tuple, List, Dict, Any

from beanie import Document
from pydantic import Field, ConfigDict, field_serializer, field_validator


class Farm(Document):
    """Represents a farm owned by a user and optionally shared with other users.

    Access rules (to be enforced at the API layer):
    - Readers: owner_email or any user in shared_with
    - Mutations (update/delete/share): only owner_email
    """

    name: str = Field(..., description="Farm name")
    country: str = Field(..., description="Country")
    state_province: str = Field(..., description="State or province")
    owner_email: str = Field(..., description="Email of the owner user")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    lat_long: Optional[Dict[str, Any]] = Field(
        default=None, description="GeoJSON Point: {'type':'Point','coordinates':[lon, lat]}"
    )
    shared_with: List[str] = Field(default_factory=list, description="Emails of users the farm is shared with")

    class Settings:
        name = "farms"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "_id": "683d1238fded441a09bdd6f0",
                "name": "Green Valley",
                "country": "Brazil",
                "state_province": "SP",
                "owner_email": "owner@example.com",
                "notes": "Irrigated fields",
                "lat_long": {"type": "Point", "coordinates": [-47.12345, -22.12345]},
                "shared_with": ["tech1@example.com", "manager@example.com"],
            }
        }
    )

    @field_validator("lat_long", mode="before")
    @classmethod
    def _coerce_geojson(cls, v):
        if v is None or v == "":
            return None
        # Accept GeoJSON directly or coerce from "lat,lon", [lat, lon], {"lat": x, "lon": y}
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
            lat = float(v.get("lat"))
            lon = float(v.get("lon"))
        else:
            raise ValueError("Invalid lat_long format")
        if not (-90.0 <= lat <= 90.0):
            raise ValueError("Latitude must be between -90 and 90")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError("Longitude must be between -180 and 180")
        return {"type": "Point", "coordinates": [lon, lat] }

    @field_serializer("id", when_used="json")
    def serialize_id(self, v):
        return str(v) if v is not None else None
