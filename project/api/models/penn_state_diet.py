from __future__ import annotations

import datetime as dt
from typing import Optional

from beanie import Document
from pydantic import Field, ConfigDict, field_serializer, field_validator


class PennStateDiet(Document):
    """Penn State diet view with effectiveness factor and FDNef.

    Stores sieve percentages and FDN (bromate) percentage, and keeps cached
    computed fields based on provided formulas:

    - effectiveness_factor_pct = pct_19mm + pct_8mm + (pct_1_18mm / 2)
    - fdnef_pct = fdn_bromate_pct * (effectiveness_factor_pct / 100)

    All percentage fields are represented as 0–100 values.
    Uniqueness: (farm_id, date, diet).
    """

    date: dt.date = Field(..., description="Reference date for the sampling")
    unit: str = Field(..., description="Production unit identifier (e.g., CAUA)")
    farm_id: str = Field(..., description="Associated Farm (property) ID")
    diet: Optional[str] = Field(default=None, description="Diet name/category")

    pct_19mm: Optional[float] = Field(default=None, ge=0, le=100, description="Proportion at 19 mm sieve (%)")
    pct_8mm: Optional[float] = Field(default=None, ge=0, le=100, description="Proportion at 8 mm sieve (%)")
    pct_1_18mm: Optional[float] = Field(default=None, ge=0, le=100, description="Proportion at 1.18 mm sieve (%)")
    fdn_bromate_pct: Optional[float] = Field(default=None, ge=0, le=100, description="FDN bromate (%)")

    # Cached computed fields
    effectiveness_factor_pct: float = Field(default=0.0, ge=0, le=100, description="Effectiveness Factor (%)")
    fdnef_pct: float = Field(default=0.0, ge=0, le=100, description="FDNef (%)")

    class Settings:
        name = "penn_state_diet"
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
                "_id": "683d1238fded441a09bdd750",
                "date": "2024-10-22",
                "unit": "CAUA",
                "farm_id": "683d1238fded441a09bdd6f0",
                "diet": "ADAPTATION",
                "pct_19mm": 12.7,
                "pct_8mm": 26.3,
                "pct_1_18mm": 3.5,
                "fdn_bromate_pct": 57.7,
                "effectiveness_factor_pct": 12.7 + 26.3 + (3.5 / 2),
                "fdnef_pct": (57.7 * (12.7 + 26.3 + (3.5 / 2)) / 100.0),
            }
        }
    )

    @staticmethod
    def _calc_effectiveness(p19: Optional[float], p8: Optional[float], p1_18: Optional[float]) -> float:
        if p19 is None and p8 is None and p1_18 is None:
            return 0.0
        return float(p19 or 0.0) + float(p8 or 0.0) + (float(p1_18 or 0.0) / 2.0)

    @staticmethod
    def _calc_fdnef(fdn_bromate: Optional[float], effectiveness: float) -> float:
        if fdn_bromate is None:
            return 0.0
        return float(fdn_bromate) * (effectiveness / 100.0)

    @field_validator("effectiveness_factor_pct", mode="before")
    @classmethod
    def _ensure_effectiveness(cls, v, info):
        data = info.data
        return cls._calc_effectiveness(data.get("pct_19mm"), data.get("pct_8mm"), data.get("pct_1_18mm"))

    @field_validator("fdnef_pct", mode="before")
    @classmethod
    def _ensure_fdnef(cls, v, info):
        data = info.data
        eff = cls._calc_effectiveness(data.get("pct_19mm"), data.get("pct_8mm"), data.get("pct_1_18mm"))
        return cls._calc_fdnef(data.get("fdn_bromate_pct"), eff)

    @field_serializer("id", when_used="json")
    def serialize_id(self, v):
        return str(v) if v is not None else None
