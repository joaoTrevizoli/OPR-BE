from __future__ import annotations

import datetime as dt
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator
from pydantic.fields import AliasChoices


class FactoryBase(BaseModel):
    date: dt.date = Field(..., description="Reference date (YYYY-MM-DD)")
    unit: str = Field(..., description="Production unit identifier")
    farm_id: str = Field(..., description="Associated Farm ID")

    # Manufacturing inputs
    manufacturing_adaptation: Optional[int] = Field(default=0, ge=0)
    manufacturing_growth: Optional[int] = Field(default=0, ge=0)
    manufacturing_termination: Optional[int] = Field(default=0, ge=0)
    planned_manufacturing_total: Optional[int] = Field(default=None, ge=0)

    # Supply inputs
    supply_adaptation: Optional[int] = Field(default=0, ge=0)
    supply_growth: Optional[int] = Field(default=0, ge=0)
    supply_termination: Optional[int] = Field(default=0, ge=0)
    planned_supply_total: Optional[int] = Field(default=None, ge=0)

    # Flags
    day_reading: Optional[bool] = Field(default=False, validation_alias=AliasChoices("day_reading", "diurna", "day"))
    night_reading: Optional[bool] = Field(default=False, validation_alias=AliasChoices("night_reading", "noturna", "night"))

    @staticmethod
    def _coerce_int(v):
        if v is None or v == "":
            return None
        if isinstance(v, (int, float)):
            try:
                return int(v)
            except Exception:
                return None
        s = str(v).strip().replace(" ", "").replace(".", "").replace(",", "")
        try:
            return int(s)
        except Exception:
            try:
                return int(float(str(v).replace(',', '.')))
            except Exception:
                return None

    @staticmethod
    def _coerce_bool(v):
        if isinstance(v, bool):
            return v
        if v is None or v == "":
            return None
        s = str(v).strip().lower()
        if s in {"sim", "yes", "y", "true", "1"}:
            return True
        if s in {"nao", "não", "no", "n", "false", "0"}:
            return False
        return None

    @field_validator(
        'manufacturing_adaptation', 'manufacturing_growth', 'manufacturing_termination',
        'planned_manufacturing_total', 'supply_adaptation', 'supply_growth', 'supply_termination',
        'planned_supply_total', mode='before'
    )
    @classmethod
    def int_ok(cls, v):
        return cls._coerce_int(v)

    @field_validator('day_reading', 'night_reading', mode='before')
    @classmethod
    def bool_ok(cls, v):
        b = cls._coerce_bool(v)
        return v if b is None else b


class FactoryCreate(FactoryBase):
    pass


class FactoryUpdate(BaseModel):
    manufacturing_adaptation: Optional[int] = Field(default=None, ge=0)
    manufacturing_growth: Optional[int] = Field(default=None, ge=0)
    manufacturing_termination: Optional[int] = Field(default=None, ge=0)
    planned_manufacturing_total: Optional[int] = Field(default=None, ge=0)
    supply_adaptation: Optional[int] = Field(default=None, ge=0)
    supply_growth: Optional[int] = Field(default=None, ge=0)
    supply_termination: Optional[int] = Field(default=None, ge=0)
    planned_supply_total: Optional[int] = Field(default=None, ge=0)
    day_reading: Optional[bool] = Field(default=None, validation_alias=AliasChoices("day_reading", "diurna", "day"))
    night_reading: Optional[bool] = Field(default=None, validation_alias=AliasChoices("night_reading", "noturna", "night"))

    @field_validator(
        'manufacturing_adaptation', 'manufacturing_growth', 'manufacturing_termination',
        'planned_manufacturing_total', 'supply_adaptation', 'supply_growth', 'supply_termination',
        'planned_supply_total', mode='before'
    )
    @classmethod
    def int_ok(cls, v):
        return FactoryBase._coerce_int(v)

    @field_validator('day_reading', 'night_reading', mode='before')
    @classmethod
    def bool_ok(cls, v):
        b = FactoryBase._coerce_bool(v)
        return v if b is None else b


class FactoryRead(FactoryBase):
    id: Optional[str] = Field(default=None)

    manufacturing_day_total: int = Field(default=0)
    loading_deviation_pct: float = Field(default=0.0)

    supply_day_total: int = Field(default=0)
    adaptation_ratio_pct: float = Field(default=0.0)
    growth_ratio_pct: float = Field(default=0.0)
    termination_ratio_pct: float = Field(default=0.0)
    day_ratio_pct: float = Field(default=0.0)
    supply_deviation_pct: float = Field(default=0.0)


class FactoryList(BaseModel):
    items: List[FactoryRead]
