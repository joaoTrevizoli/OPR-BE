from __future__ import annotations

import datetime as dt
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


class DietCostBase(BaseModel):
    date: dt.date = Field(..., description="Reference date (YYYY-MM-DD)")
    unit: str = Field(..., description="Production unit identifier")
    farm_id: str = Field(..., description="Associated Farm ID")
    diet: Optional[str] = Field(default=None, description="Diet name/category")

    cost_mn_per_ton: Optional[float] = Field(default=None, ge=0)
    cost_ms_per_ton: Optional[float] = Field(default=None, ge=0)
    time_in_diet_days: Optional[int] = Field(default=None, ge=0)

    @staticmethod
    def _coerce_float(v):
        if v is None or v == "":
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip().lower().replace("r$", "").replace(" ", "").replace(",", ".")
        try:
            return float(s)
        except Exception:
            return None

    @field_validator("cost_mn_per_ton", "cost_ms_per_ton", mode="before")
    @classmethod
    def float_ok(cls, v):
        return cls._coerce_float(v)

    @field_validator("time_in_diet_days", mode="before")
    @classmethod
    def int_ok(cls, v):
        if v is None or v == "":
            return None
        try:
            return int(v)
        except Exception:
            return None


class DietCostCreate(DietCostBase):
    pass


class DietCostUpdate(BaseModel):
    diet: Optional[str] = None
    cost_mn_per_ton: Optional[float] = Field(default=None, ge=0)
    cost_ms_per_ton: Optional[float] = Field(default=None, ge=0)
    time_in_diet_days: Optional[int] = Field(default=None, ge=0)

    @field_validator("cost_mn_per_ton", "cost_ms_per_ton", mode="before")
    @classmethod
    def float_ok(cls, v):
        return DietCostBase._coerce_float(v)

    @field_validator("time_in_diet_days", mode="before")
    @classmethod
    def int_ok(cls, v):
        if v is None or v == "":
            return None
        try:
            return int(v)
        except Exception:
            return None


class DietCostRead(DietCostBase):
    id: Optional[str] = Field(default=None)
    cost_mn_per_phase: Optional[float] = Field(default=None, ge=0)
    cost_ms_per_phase: Optional[float] = Field(default=None, ge=0)


class DietCostList(BaseModel):
    items: List[DietCostRead]
