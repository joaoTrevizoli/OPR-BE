from __future__ import annotations

import datetime as dt
from typing import Optional

from beanie import Document
from pydantic import Field, ConfigDict, field_serializer


class FeedDryMatter(Document):
    """Represents dry matter composition targets for animal feed.

    All percentage fields should be expressed as numbers between 0 and 100.
    """

    date: dt.date = Field(..., description="Reference date for the composition")
    unit: str = Field(..., description="Production unit identifier (e.g., CAUA)")
    farm_id: str = Field(..., description="Associated Farm ID")

    adaptation: Optional[float] = Field(default=None, ge=0, le=100, description="Adaptation percentage")
    growth: Optional[float] = Field(default=None, ge=0, le=100, description="Growth percentage")
    termination: Optional[float] = Field(default=None, ge=0, le=100, description="Termination percentage")

    sugarcane_bagasse: Optional[float] = Field(default=None, ge=0, le=100, description="Sugarcane bagasse percentage")
    wet_grain: Optional[float] = Field(default=None, ge=0, le=100, description="Wet grain percentage")
    silage: Optional[float] = Field(default=None, ge=0, le=100, description="Silage percentage")

    class Settings:
        name = "feed_dry_matter"
        indexes = [
            __import__("pymongo").IndexModel(
                [("farm_id", __import__("pymongo").ASCENDING), ("date", __import__("pymongo").ASCENDING)],
                unique=True,
                name="uniq_farm_date",
            )
        ]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "_id": "683d1238fded441a09bdd6e5",
                "date": "2024-01-19",
                "unit": "CAUA",
                "farm_id": "683d1238fded441a09bdd6f0",
                "adaptation": 61.0,
                "growth": 60.0,
                "termination": 60.0,
                "sugarcane_bagasse": 37.0,
                "wet_grain": 58.0,
                "silage": 0.0,
            }
        }
    )

    @field_serializer("id", when_used="json")
    def serialize_id(self, v):
        return str(v) if v is not None else None
