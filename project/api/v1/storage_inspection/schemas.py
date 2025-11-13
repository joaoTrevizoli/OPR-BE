from __future__ import annotations

import datetime as dt
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator
from pydantic.fields import AliasChoices


class StorageInspectionBase(BaseModel):
    date: dt.date = Field(..., description="Reference date (YYYY-MM-DD)")
    unit: str = Field(..., description="Production unit identifier")
    farm_id: str = Field(..., description="Associated Farm ID")

    ingredient: Optional[str] = Field(default=None, validation_alias=AliasChoices("ingredient", "insumo"))
    storage_location: Optional[str] = Field(default=None, validation_alias=AliasChoices("storage_location", "armazenamento", "armazenamento_trincheira"))

    holes: Optional[bool] = Field(default=None, validation_alias=AliasChoices("holes", "furos"))
    displaced_pieces: Optional[int] = Field(default=None, ge=0, validation_alias=AliasChoices("displaced_pieces", "pedacos_deslonados", "pedaços_deslonados"))
    in_use: Optional[bool] = Field(default=None, validation_alias=AliasChoices("in_use", "em_uso"))
    closing_date: Optional[dt.date] = Field(default=None, validation_alias=AliasChoices("closing_date", "data_do_fechamento"))
    tarp_face_correct: Optional[bool] = Field(default=None, validation_alias=AliasChoices("tarp_face_correct", "face_da_lona_certa"))
    identified: Optional[bool] = Field(default=None, validation_alias=AliasChoices("identified", "identificados", "identificado"))

    @staticmethod
    def _coerce_bool(v):
        if isinstance(v, bool):
            return v
        if v is None or v == "":
            return None
        s = str(v).strip().lower()
        if s in {"sim", "s", "yes", "y", "true", "1"}:
            return True
        if s in {"nao", "não", "n", "no", "false", "0"}:
            return False
        return None

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

    @field_validator('holes', 'in_use', 'tarp_face_correct', 'identified', mode='before')
    @classmethod
    def bool_ok(cls, v):
        b = cls._coerce_bool(v)
        return v if b is None else b

    @field_validator('displaced_pieces', mode='before')
    @classmethod
    def int_ok(cls, v):
        return cls._coerce_int(v)


class StorageInspectionCreate(StorageInspectionBase):
    pass


class StorageInspectionUpdate(BaseModel):
    ingredient: Optional[str] = None
    storage_location: Optional[str] = None
    holes: Optional[bool] = Field(default=None, validation_alias=AliasChoices("holes", "furos"))
    displaced_pieces: Optional[int] = Field(default=None, ge=0, validation_alias=AliasChoices("displaced_pieces", "pedacos_deslonados", "pedaços_deslonados"))
    in_use: Optional[bool] = Field(default=None, validation_alias=AliasChoices("in_use", "em_uso"))
    closing_date: Optional[dt.date] = Field(default=None, validation_alias=AliasChoices("closing_date", "data_do_fechamento"))
    tarp_face_correct: Optional[bool] = Field(default=None, validation_alias=AliasChoices("tarp_face_correct", "face_da_lona_certa"))
    identified: Optional[bool] = Field(default=None, validation_alias=AliasChoices("identified", "identificados", "identificado"))

    @field_validator('holes', 'in_use', 'tarp_face_correct', 'identified', mode='before')
    @classmethod
    def bool_ok(cls, v):
        b = StorageInspectionBase._coerce_bool(v)
        return v if b is None else b

    @field_validator('displaced_pieces', mode='before')
    @classmethod
    def int_ok(cls, v):
        return StorageInspectionBase._coerce_int(v)


class StorageInspectionRead(StorageInspectionBase):
    id: Optional[str] = Field(default=None)
    time_without_use_days: int = Field(default=0, ge=0)


class StorageInspectionList(BaseModel):
    items: List[StorageInspectionRead]
