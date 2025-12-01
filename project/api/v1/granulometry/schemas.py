from __future__ import annotations

import datetime as dt
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


class GranulometryBase(BaseModel):
    date: dt.date = Field(..., description="Reference date (YYYY-MM-DD)")
    unit: str = Field(..., description="Production unit identifier")
    farm_id: str = Field(..., description="Associated Farm ID")
    sample: Optional[str] = Field(default=None, description="Optional sample name/label")

    count_6mm: Optional[int] = Field(default=0, ge=0)
    count_3_25mm: Optional[int] = Field(default=0, ge=0)
    count_2mm: Optional[int] = Field(default=0, ge=0)
    count_1_25mm: Optional[int] = Field(default=0, ge=0)
    count_bottom: Optional[int] = Field(default=0, ge=0)

    whole_grain_total: Optional[int] = Field(default=None, ge=0)

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

    @field_validator('count_6mm', 'count_3_25mm', 'count_2mm', 'count_1_25mm', 'count_bottom', 'whole_grain_total', mode='before')
    @classmethod
    def int_ok(cls, v):
        return cls._coerce_int(v)


class GranulometryCreate(GranulometryBase):
    pass


class GranulometryUpdate(BaseModel):
    unit: Optional[str] = None
    sample: Optional[str] = None
    count_6mm: Optional[int] = Field(default=None, ge=0)
    count_3_25mm: Optional[int] = Field(default=None, ge=0)
    count_2mm: Optional[int] = Field(default=None, ge=0)
    count_1_25mm: Optional[int] = Field(default=None, ge=0)
    count_bottom: Optional[int] = Field(default=None, ge=0)
    whole_grain_total: Optional[int] = Field(default=None, ge=0)

    @field_validator('count_6mm', 'count_3_25mm', 'count_2mm', 'count_1_25mm', 'count_bottom', 'whole_grain_total', mode='before')
    @classmethod
    def int_ok(cls, v):
        return GranulometryBase._coerce_int(v)


class GranulometryRead(GranulometryBase):
    id: Optional[str] = Field(default=None)
    total_count: int = Field(default=0, ge=0)
    pct_6mm: float = Field(default=0.0, ge=0, le=100)
    pct_3_25mm: float = Field(default=0.0, ge=0, le=100)
    pct_2mm: float = Field(default=0.0, ge=0, le=100)
    pct_1_25mm: float = Field(default=0.0, ge=0, le=100)
    pct_bottom: float = Field(default=0.0, ge=0, le=100)
    granulometry_mm: float = Field(default=0.0)


class GranulometryList(BaseModel):
    items: List[GranulometryRead]
