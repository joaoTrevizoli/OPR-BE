from __future__ import annotations

import datetime as dt
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


class PennStateBase(BaseModel):
    date: dt.date = Field(..., description="Reference date (YYYY-MM-DD)")
    unit: str = Field(..., description="Production unit identifier")
    farm_id: str = Field(..., description="Associated Farm ID")
    diet: Optional[str] = Field(default=None, description="Diet name/category")

    pct_19mm: Optional[float] = Field(default=None, ge=0, le=100)
    pct_8mm: Optional[float] = Field(default=None, ge=0, le=100)
    pct_3_8mm: Optional[float] = Field(default=None, ge=0, le=100)
    pct_fines: Optional[float] = Field(default=None, ge=0, le=100)

    @staticmethod
    def _coerce_percent(v):
        if v is None or v == "":
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip().lower().replace('%', '').replace(',', '.')
        try:
            return float(s)
        except Exception:
            return None

    @field_validator('pct_19mm', 'pct_8mm', 'pct_3_8mm', 'pct_fines', mode='before')
    @classmethod
    def percent_str_ok(cls, v):
        return cls._coerce_percent(v)


class PennStateCreate(PennStateBase):
    pass


class PennStateUpdate(BaseModel):
    diet: Optional[str] = None
    pct_19mm: Optional[float] = Field(default=None, ge=0, le=100)
    pct_8mm: Optional[float] = Field(default=None, ge=0, le=100)
    pct_3_8mm: Optional[float] = Field(default=None, ge=0, le=100)
    pct_fines: Optional[float] = Field(default=None, ge=0, le=100)

    @field_validator('pct_19mm', 'pct_8mm', 'pct_3_8mm', 'pct_fines', mode='before')
    @classmethod
    def percent_str_ok(cls, v):
        return PennStateBase._coerce_percent(v)


class PennStateRead(PennStateBase):
    id: Optional[str] = Field(default=None)
    desirable_pct: float = Field(default=0, ge=0, le=100, description="% de Desejável = 3.8mm + 8mm/2 + 19mm/3")


class PennStateList(BaseModel):
    items: List[PennStateRead]
