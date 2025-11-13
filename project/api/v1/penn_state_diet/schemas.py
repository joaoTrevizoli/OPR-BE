from __future__ import annotations

import datetime as dt
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


class PennStateDietBase(BaseModel):
    date: dt.date = Field(..., description="Reference date (YYYY-MM-DD)")
    unit: str = Field(..., description="Production unit identifier")
    farm_id: str = Field(..., description="Associated Farm ID")
    diet: Optional[str] = Field(default=None, description="Diet name/category")

    pct_19mm: Optional[float] = Field(default=None, ge=0, le=100)
    pct_8mm: Optional[float] = Field(default=None, ge=0, le=100)
    pct_1_18mm: Optional[float] = Field(default=None, ge=0, le=100)
    fdn_bromate_pct: Optional[float] = Field(default=None, ge=0, le=100)

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

    @field_validator('pct_19mm', 'pct_8mm', 'pct_1_18mm', 'fdn_bromate_pct', mode='before')
    @classmethod
    def percent_str_ok(cls, v):
        return cls._coerce_percent(v)


class PennStateDietCreate(PennStateDietBase):
    pass


class PennStateDietUpdate(BaseModel):
    diet: Optional[str] = None
    pct_19mm: Optional[float] = Field(default=None, ge=0, le=100)
    pct_8mm: Optional[float] = Field(default=None, ge=0, le=100)
    pct_1_18mm: Optional[float] = Field(default=None, ge=0, le=100)
    fdn_bromate_pct: Optional[float] = Field(default=None, ge=0, le=100)

    @field_validator('pct_19mm', 'pct_8mm', 'pct_1_18mm', 'fdn_bromate_pct', mode='before')
    @classmethod
    def percent_str_ok(cls, v):
        return PennStateDietBase._coerce_percent(v)


class PennStateDietRead(PennStateDietBase):
    id: Optional[str] = Field(default=None)
    effectiveness_factor_pct: float = Field(default=0, ge=0, le=100, description="Effectiveness Factor (%) = 19mm + 8mm + 1.18mm/2")
    fdnef_pct: float = Field(default=0, ge=0, le=100, description="FDNef (%) = FDN bromate * effectiveness/100")


class PennStateDietList(BaseModel):
    items: List[PennStateDietRead]
