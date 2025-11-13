from __future__ import annotations

import datetime as dt
from typing import Optional

from beanie import Document
from pydantic import Field, ConfigDict, field_serializer, field_validator


class Environment(Document):
    """Environment measurements per farm and date.

    Columns based on the provided spreadsheet (translated to English):
    - rainfall_mm ("pluviometry")
    - temperature_noon_c ("temperature at 12:00")
    - relative_humidity_pct
    - itu_real (computed)

    ITU Real formula (from sheet):
        ITU Real = 0.8 * T + T * ((RH - 14.3) / 100) + 46.3
        where T is temperature_noon_c (°C) and RH is relative_humidity_pct (0–100)

    Uniqueness: (farm_id, date)
    """

    date: dt.date = Field(..., description="Reference date (YYYY-MM-DD)")
    unit: str = Field(..., description="Production unit identifier (e.g., CAUA)")
    farm_id: str = Field(..., description="Associated Farm ID (spreadsheet column 'UNIDADE')")

    rainfall_mm: Optional[float] = Field(default=None, ge=0, description="Rainfall (mm)")
    temperature_noon_c: Optional[float] = Field(default=None, description="Temperature at 12:00 (°C)")
    relative_humidity_pct: Optional[float] = Field(default=None, ge=0, le=100, description="Relative humidity (%)")

    # Cached computed field
    itu_real: float = Field(default=0.0, description="ITU Real computed using the spreadsheet formula")

    class Settings:
        name = "environment"
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
                "_id": "683d1238fded441a09bddabc",
                "date": "2024-11-05",
                "unit": "CAUA",
                "farm_id": "683d1238fded441a09bdd6f0",
                "rainfall_mm": 0,
                "temperature_noon_c": 32,
                "relative_humidity_pct": 61,
                # 0.8*32 + 32*((61-14.3)/100) + 46.3 = 25.6 + 32*(46.7/100) + 46.3 = 25.6 + 14.944 + 46.3 = 86.844
                "itu_real": 86.84,
            }
        }
    )

    @staticmethod
    def _calc_itu(temp_c: Optional[float], rh_pct: Optional[float]) -> float:
        if temp_c is None or rh_pct is None:
            return 0.0
        try:
            t = float(temp_c)
            rh = float(rh_pct)
            return float(0.8 * t + t * ((rh - 14.3) / 100.0) + 46.3)
        except Exception:
            return 0.0

    @field_validator("itu_real", mode="before")
    @classmethod
    def _ensure_itu(cls, v, info):
        data = info.data
        return cls._calc_itu(data.get("temperature_noon_c"), data.get("relative_humidity_pct"))

    @field_serializer("id", when_used="json")
    def serialize_id(self, v):
        return str(v) if v is not None else None
