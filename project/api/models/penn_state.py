from __future__ import annotations

import datetime as dt
from typing import Optional

from beanie import Document
from pydantic import Field, ConfigDict, field_serializer


class PennState(Document):
    """Penn State Particle Separator results linked to a farm.

    Stores the proportions (%) retained at each sieve and bottom (fines).
    """

    date: dt.date = Field(..., description="Reference date for the sampling")
    unit: str = Field(..., description="Production unit identifier (e.g., CAUA)")
    farm_id: str = Field(..., description="Associated Farm (property) ID")
    diet: Optional[str] = Field(default=None, description="Diet name/category")

    pct_19mm: Optional[float] = Field(default=None, ge=0, le=100, description="Proportion retained at 19 mm sieve (%)")
    pct_8mm: Optional[float] = Field(default=None, ge=0, le=100, description="Proportion retained at 8 mm sieve (%)")
    pct_3_8mm: Optional[float] = Field(default=None, ge=0, le=100, description="Proportion retained at 3.8 mm sieve (%)")
    pct_fines: Optional[float] = Field(default=None, ge=0, le=100, description="Proportion passing to bottom/fines (%)")

    class Settings:
        name = "penn_state"
        indexes = [
            __import__("pymongo").IndexModel(
                [("farm_id", __import__("pymongo").ASCENDING), ("date", __import__("pymongo").ASCENDING), ("diet", __import__("pymongo").ASCENDING)],
                unique=True,
                name="uniq_farm_date_diet",
            )
        ]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "_id": "683d1238fded441a09bdd700",
                "date": "2024-09-23",
                "unit": "CAUA",
                "farm_id": "683d1238fded441a09bdd6f0",
                "diet": "ADAPTACAO",
                "pct_19mm": 2.6,
                "pct_8mm": 31.5,
                "pct_3_8mm": 20.7,
                "pct_fines": 45.3,
            }
        }
    )

    @field_serializer("id", when_used="json")
    def serialize_id(self, v):
        return str(v) if v is not None else None
