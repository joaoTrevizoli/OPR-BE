from __future__ import annotations

import datetime as dt
from typing import Optional

from beanie import Document
from pydantic import Field, ConfigDict, field_serializer, field_validator
from pydantic.fields import AliasChoices


class StorageInspection(Document):
    """Storage/Silo inspection per farm and date.

    Columns translated from the spreadsheet (kept general to fit different storages):
    - ingredient (INSUMO)
    - storage_location (ARMAZENAMENTO TRINCHEIRA, etc.)
    - holes (FUROS)            -> bool
    - displaced_pieces (PEDACOS DESLONADOS) -> int
    - in_use (EM USO)          -> bool
    - closing_date (DATA DO FECHAMENTO) -> date
    - tarp_face_correct (FACE DA LONA CERTA) -> bool
    - identified (IDENTIFICADOS) -> bool
    - time_without_use_days (TEMPO SEM USO) -> computed

    Requested rule for TEMPO SEM USO:
        base = closing_date - date (sheet formula G - A)
        if base > 0 -> 0
        if base < 0 -> abs(base)
    Which is equivalent to: max(0, (date - closing_date).days)

    Uniqueness: (farm_id, date, ingredient)
    """

    # Identifiers
    date: dt.date = Field(..., description="Reference date (YYYY-MM-DD)")
    unit: str = Field(..., description="Production unit identifier (e.g., CAUA)")
    farm_id: str = Field(..., description="Associated Farm ID")

    # Descriptive columns
    ingredient: Optional[str] = Field(
        default=None,
        description="Ingredient/input name (column 'INSUMO')",
        validation_alias=AliasChoices("ingredient", "insumo"),
    )
    storage_location: Optional[str] = Field(
        default=None,
        description="Storage location/type (e.g., trench)",
        validation_alias=AliasChoices("storage_location", "armazenamento", "armazenamento_trincheira"),
    )

    holes: Optional[bool] = Field(
        default=None,
        description="Whether holes were observed",
        validation_alias=AliasChoices("holes", "furos"),
    )
    displaced_pieces: Optional[int] = Field(
        default=None, ge=0,
        description="Displaced pieces count",
        validation_alias=AliasChoices("displaced_pieces", "pedacos_deslonados", "pedaços_deslonados"),
    )
    in_use: Optional[bool] = Field(
        default=None,
        description="Whether the storage is currently in use",
        validation_alias=AliasChoices("in_use", "em_uso"),
    )
    closing_date: Optional[dt.date] = Field(
        default=None,
        description="Closing date (column 'DATA DO FECHAMENTO')",
        validation_alias=AliasChoices("closing_date", "data_do_fechamento"),
    )
    tarp_face_correct: Optional[bool] = Field(
        default=None,
        description="Is tarp face correct (white outside, black inside)?",
        validation_alias=AliasChoices("tarp_face_correct", "face_da_lona_certa"),
    )
    identified: Optional[bool] = Field(
        default=None,
        description="Whether the storage is identified",
        validation_alias=AliasChoices("identified", "identificados", "identificado"),
    )

    # Cached computed field
    time_without_use_days: int = Field(
        default=0, ge=0, description="Days without use = max(0, (date - closing_date).days)"
    )

    class Settings:
        name = "storage_inspection"
        indexes = [
            __import__("pymongo").IndexModel(
                [
                    ("farm_id", __import__("pymongo").ASCENDING),
                    ("date", __import__("pymongo").ASCENDING),
                    ("ingredient", __import__("pymongo").ASCENDING),
                ],
                unique=True,
                name="uniq_farm_date_ingredient",
            )
        ]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "_id": "683d1238fded441a09bde111",
                "date": "2025-08-10",
                "unit": "CAUA",
                "farm_id": "683d1238fded441a09bdd6f0",
                "ingredient": "Cottonseed meal",
                "storage_location": "Trench",
                "holes": False,
                "displaced_pieces": 5,
                "in_use": False,
                "closing_date": "2025-01-01",
                "tarp_face_correct": True,
                "identified": False,
                # G - A is negative -> days without use is positive difference
                "time_without_use_days": 221,
            }
        }
    )

    # --------- coercion helpers ---------
    @staticmethod
    def _coerce_bool(v) -> Optional[bool]:
        if v is None or v == "":
            return None
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s in {"sim", "s", "yes", "y", "true", "1"}:
            return True
        if s in {"nao", "não", "n", "no", "false", "0"}:
            return False
        return None

    @staticmethod
    def _coerce_int(v) -> Optional[int]:
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

    # --------- field validators ---------
    @field_validator("holes", "in_use", "tarp_face_correct", "identified", mode="before")
    @classmethod
    def _bool_ok(cls, v):
        b = cls._coerce_bool(v)
        return v if b is None else b

    @field_validator("displaced_pieces", mode="before")
    @classmethod
    def _int_ok(cls, v):
        return cls._coerce_int(v)

    @field_validator("time_without_use_days", mode="before")
    @classmethod
    def _ensure_time_without_use(cls, v, info):
        d = info.data
        date_val = d.get("date")
        closing = d.get("closing_date")
        try:
            if not date_val or not closing:
                return 0
            if isinstance(date_val, str):
                date_val = dt.date.fromisoformat(date_val)
            if isinstance(closing, str):
                closing = dt.date.fromisoformat(closing)
            # days without use = max(0, (date - closing).days)
            delta = (date_val - closing).days
            return int(delta) if delta > 0 else 0
        except Exception:
            return 0

    @field_serializer("id", when_used="json")
    def serialize_id(self, v):
        return str(v) if v is not None else None
