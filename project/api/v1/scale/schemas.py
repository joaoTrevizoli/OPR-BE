from __future__ import annotations

import datetime as dt
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator
from pydantic.alias_generators import to_camel
from pydantic.fields import AliasChoices


class ScaleBase(BaseModel):
    date: dt.date = Field(..., description="Reference date (YYYY-MM-DD)")
    unit: str = Field(..., description="Production unit identifier")
    farm_id: str = Field(..., description="Associated Farm ID")

    equipment: str = Field(..., description="Truck identifier/number")

    loaded_weight: int = Field(
        ..., ge=0, description="Loaded weight (kg)",
        validation_alias=AliasChoices("loaded_weight", "carregamento"),
    )
    delivered_weight: Optional[int] = Field(
        default=None, ge=0, description="Delivered weight (kg)",
        validation_alias=AliasChoices("delivered_weight", "fornecimento"),
    )
    gross_weight: int = Field(
        ..., ge=0, description="Scale full (kg)",
        validation_alias=AliasChoices("gross_weight", "balanco_cheio"),
    )
    tare_weight: int = Field(
        ..., ge=0, description="Scale empty (kg)",
        validation_alias=AliasChoices("tare_weight", "balanco_vazio"),
    )

    notes: Optional[str] = None

    @staticmethod
    def _coerce_int(v):
        if v is None or v == "":
            return None
        try:
            return int(str(v).replace(" ", "").replace(",", "").replace(".", "")) if isinstance(v, str) and str(v).count(".") + str(v).count(",") > 1 else int(v)
        except Exception:
            try:
                return int(float(str(v).replace(',', '.')))
            except Exception:
                return None

    @field_validator('loaded_weight', 'delivered_weight', 'gross_weight', 'tare_weight', mode='before')
    @classmethod
    def int_ok(cls, v):
        return cls._coerce_int(v)


class ScaleCreate(ScaleBase):
    pass


class ScaleUpdate(BaseModel):
    equipment: Optional[str] = None
    loaded_weight: Optional[int] = Field(default=None, ge=0, validation_alias=AliasChoices("loaded_weight", "carregamento"))
    delivered_weight: Optional[int] = Field(default=None, ge=0, validation_alias=AliasChoices("delivered_weight", "fornecimento"))
    gross_weight: Optional[int] = Field(default=None, ge=0, validation_alias=AliasChoices("gross_weight", "balanco_cheio"))
    tare_weight: Optional[int] = Field(default=None, ge=0, validation_alias=AliasChoices("tare_weight", "balanco_vazio"))
    notes: Optional[str] = None

    @field_validator('loaded_weight', 'delivered_weight', 'gross_weight', 'tare_weight', mode='before')
    @classmethod
    def int_ok(cls, v):
        return ScaleBase._coerce_int(v)


class ScaleRead(ScaleBase):
    id: Optional[str] = Field(default=None)
    net_weight: int = Field(default=0)
    kg_diff: int = Field(default=0)
    pct_diff: float = Field(default=0.0)


class ScaleList(BaseModel):
    items: List[ScaleRead]
