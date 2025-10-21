from __future__ import annotations

import datetime as dt
from typing import Optional

from beanie import Document
from pydantic import Field, ConfigDict, field_serializer


class DietCost(Document):
    """Represents diet costs associated with a farm (property).

    Values are monetary or day counts. Monetary fields are floats in R$.
    """

    date: dt.date = Field(..., description="Reference date for the costs")
    unit: str = Field(..., description="Production unit identifier (e.g., CAUA)")
    farm_id: str = Field(..., description="Associated Farm (property) ID")
    diet: Optional[str] = Field(default=None, description="Diet name/category")

    cost_mn_per_ton: Optional[float] = Field(default=None, ge=0, description="CUSTO MN R$/ton")
    cost_ms_per_ton: Optional[float] = Field(default=None, ge=0, description="CUSTO MS R$/ton")
    time_in_diet_days: Optional[int] = Field(default=None, ge=0, description="Tempo na dieta (dias)")
    cost_mn_per_phase: Optional[float] = Field(default=None, ge=0, description="Custo MN R$/fase")
    cost_ms_per_phase: Optional[float] = Field(default=None, ge=0, description="Custo MS R$/fase")

    class Settings:
        name = "diet_cost"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "_id": "683d1238fded441a09bdd6ff",
                "date": "2024-01-19",
                "unit": "CAUA",
                "farm_id": "683d1238fded441a09bdd6f0",
                "diet": "ADAPTACAO",
                "cost_mn_per_ton": 620.0,
                "cost_ms_per_ton": 1089.0,
                "time_in_diet_days": 16,
                "cost_mn_per_phase": 9920.0,
                "cost_ms_per_phase": 17424.0,
            }
        }
    )

    @field_serializer("id", when_used="json")
    def serialize_id(self, v):
        return str(v) if v is not None else None
