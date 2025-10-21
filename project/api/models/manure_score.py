from __future__ import annotations

import datetime as dt
from typing import Optional

from beanie import Document
from pydantic import Field, ConfigDict, field_serializer


class ManureScore(Document):
    """Represents manure score counting results for a given date/unit/farm.

    Stores counts for each score bucket and keeps a cached `total` for convenience.
    Percentages should be computed at the API layer.
    """

    date: dt.date = Field(..., description="Reference date for the measurements")
    unit: str = Field(..., description="Production unit identifier (e.g., CAUA)")
    farm_id: str = Field(..., description="Associated Farm ID")
    diet: Optional[str] = Field(default=None, description="Diet name/category (e.g., Adaptation, Growth, Termination)")

    score_1: int = Field(default=0, ge=0, description="Count with score 1")
    score_2: int = Field(default=0, ge=0, description="Count with score 2")
    score_3: int = Field(default=0, ge=0, description="Count with score 3")
    score_3_5: int = Field(default=0, ge=0, description="Count with score 3.5")
    score_4: int = Field(default=0, ge=0, description="Count with score 4")

    total: int = Field(default=0, ge=0, description="Total observations (cached)")

    class Settings:
        name = "manure_score"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "_id": "683d1238fded441a09bdd7a1",
                "date": "2024-08-11",
                "unit": "CAUA",
                "farm_id": "683d1238fded441a09bdd6f0",
                "diet": "ADAPTATION",
                "score_1": 1,
                "score_2": 4,
                "score_3": 6,
                "score_3_5": 2,
                "score_4": 0,
                "total": 13,
            }
        }
    )

    @field_serializer("id", when_used="json")
    def serialize_id(self, v):
        return str(v) if v is not None else None
