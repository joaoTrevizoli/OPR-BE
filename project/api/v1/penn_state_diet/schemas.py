from __future__ import annotations

import datetime as dt
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


class PennStateDietBase(BaseModel):
    date: dt.date = Field(..., description="Reference date (YYYY-MM-DD)")
    unit: str = Field(..., description="Production unit identifier")
    farm_id: str = Field(..., description="Associated Farm ID")
    diet: Optional[str] = Field(default=None, description="Diet name/category")
    sample: Optional[str] = Field(default=None, description="Optional sample name/label")

    # Inputs: counts for each sieve and bottom
    count_19mm: Optional[int] = Field(default=0, ge=0)
    count_8mm: Optional[int] = Field(default=0, ge=0)
    count_1_18mm: Optional[int] = Field(default=0, ge=0)
    count_bottom: Optional[int] = Field(default=0, ge=0)

    # Input: FDN bromate percentage
    fdn_bromate_pct: Optional[float] = Field(default=None, ge=0, le=100)

    @staticmethod
    def _coerce_int(v):
        if v is None or v == "":
            return None
        if isinstance(v, (int, float)):
            try:
                return int(v)
            except Exception:
                return None
        s = str(v).strip().replace(' ', '').replace('.', '').replace(',', '')
        try:
            return int(s)
        except Exception:
            try:
                return int(float(str(v).replace(',', '.')))
            except Exception:
                return None

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

    @field_validator('count_19mm', 'count_8mm', 'count_1_18mm', 'count_bottom', mode='before')
    @classmethod
    def int_ok(cls, v):
        return cls._coerce_int(v)

    @field_validator('fdn_bromate_pct', mode='before')
    @classmethod
    def percent_ok(cls, v):
        return cls._coerce_percent(v)


class PennStateDietCreate(PennStateDietBase):
    pass


class PennStateDietUpdate(BaseModel):
    unit: Optional[str] = None
    diet: Optional[str] = None
    sample: Optional[str] = None
    count_19mm: Optional[int] = Field(default=None, ge=0)
    count_8mm: Optional[int] = Field(default=None, ge=0)
    count_1_18mm: Optional[int] = Field(default=None, ge=0)
    count_bottom: Optional[int] = Field(default=None, ge=0)
    fdn_bromate_pct: Optional[float] = Field(default=None, ge=0, le=100)

    @field_validator('count_19mm', 'count_8mm', 'count_1_18mm', 'count_bottom', mode='before')
    @classmethod
    def int_ok(cls, v):
        return PennStateDietBase._coerce_int(v)

    @field_validator('fdn_bromate_pct', mode='before')
    @classmethod
    def percent_ok(cls, v):
        return PennStateDietBase._coerce_percent(v)


class PennStateDietRead(PennStateDietBase):
    id: Optional[str] = Field(default=None)
    total_count: int = Field(default=0, ge=0)
    pct_19mm: float = Field(default=0.0, ge=0, le=100)
    pct_8mm: float = Field(default=0.0, ge=0, le=100)
    pct_1_18mm: float = Field(default=0.0, ge=0, le=100)
    pct_bottom: float = Field(default=0.0, ge=0, le=100)
    effectiveness_factor_pct: float = Field(default=0.0, ge=0, le=100, description="Effectiveness Factor (%) = 19mm + 8mm + 1.18mm/2")
    fdnef_pct: float = Field(default=0.0, ge=0, le=100, description="FDNef (%) = FDN bromate * effectiveness/100")


class PennStateDietList(BaseModel):
    items: List[PennStateDietRead]
