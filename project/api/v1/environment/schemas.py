from __future__ import annotations

import datetime as dt
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


class EnvironmentBase(BaseModel):
    date: dt.date = Field(..., description="Reference date (YYYY-MM-DD)")
    unit: str = Field(..., description="Production unit identifier")
    farm_id: str = Field(..., description="Associated Farm ID (spreadsheet 'UNIDADE')")

    rainfall_mm: Optional[float] = Field(default=None, ge=0)
    temperature_noon_c: Optional[float] = Field(default=None)
    relative_humidity_pct: Optional[float] = Field(default=None, ge=0, le=100)

    @staticmethod
    def _coerce_float(v):
        if v is None or v == "":
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip().replace('%', '').replace('mm', '').replace('MM', '').replace(' ', '').replace(',', '.')
        try:
            return float(s)
        except Exception:
            return None

    @field_validator('rainfall_mm', 'temperature_noon_c', 'relative_humidity_pct', mode='before')
    @classmethod
    def float_ok(cls, v):
        return cls._coerce_float(v)


class EnvironmentCreate(EnvironmentBase):
    pass


class EnvironmentUpdate(BaseModel):
    rainfall_mm: Optional[float] = Field(default=None, ge=0)
    temperature_noon_c: Optional[float] = Field(default=None)
    relative_humidity_pct: Optional[float] = Field(default=None, ge=0, le=100)

    @field_validator('rainfall_mm', 'temperature_noon_c', 'relative_humidity_pct', mode='before')
    @classmethod
    def float_ok(cls, v):
        return EnvironmentBase._coerce_float(v)


class EnvironmentRead(EnvironmentBase):
    id: Optional[str] = Field(default=None)
    itu_real: float = Field(default=0.0, description="ITU Real = 0.8*T + T*((RH-14.3)/100) + 46.3")


class EnvironmentList(BaseModel):
    items: List[EnvironmentRead]
