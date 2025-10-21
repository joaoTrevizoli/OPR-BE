from __future__ import annotations

import datetime as dt
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


class FeedDryMatterBase(BaseModel):
    date: dt.date = Field(..., description="Reference date (YYYY-MM-DD)")
    unit: str = Field(..., description="Production unit identifier")
    farm_id: str = Field(..., description="Associated Farm ID")

    adaptation: Optional[float] = Field(default=None, ge=0, le=100)
    growth: Optional[float] = Field(default=None, ge=0, le=100)
    termination: Optional[float] = Field(default=None, ge=0, le=100)

    sugarcane_bagasse: Optional[float] = Field(default=None, ge=0, le=100)
    wet_grain: Optional[float] = Field(default=None, ge=0, le=100)
    silage: Optional[float] = Field(default=None, ge=0, le=100)

    @staticmethod
    def _coerce_percent(v):
        if v is None:
            return v
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip().lower().replace('%', '').replace(',', '.')
        try:
            return float(s)
        except Exception:
            return None

    @field_validator('adaptation', 'growth', 'termination', 'sugarcane_bagasse', 'wet_grain', 'silage', mode='before')
    @classmethod
    def percent_str_ok(cls, v):
        return cls._coerce_percent(v)


class FeedDryMatterCreate(FeedDryMatterBase):
    pass


class FeedDryMatterUpdate(BaseModel):
    adaptation: Optional[float] = Field(default=None, ge=0, le=100)
    growth: Optional[float] = Field(default=None, ge=0, le=100)
    termination: Optional[float] = Field(default=None, ge=0, le=100)
    sugarcane_bagasse: Optional[float] = Field(default=None, ge=0, le=100)
    wet_grain: Optional[float] = Field(default=None, ge=0, le=100)
    silage: Optional[float] = Field(default=None, ge=0, le=100)

    @field_validator('adaptation', 'growth', 'termination', 'sugarcane_bagasse', 'wet_grain', 'silage', mode='before')
    @classmethod
    def percent_str_ok(cls, v):
        return FeedDryMatterBase._coerce_percent(v)


class FeedDryMatterRead(FeedDryMatterBase):
    id: Optional[str] = Field(default=None)


class FeedDryMatterList(BaseModel):
    items: List[FeedDryMatterRead]
