from __future__ import annotations

import datetime as dt
from typing import Optional

from beanie import Document
from pydantic import Field, ConfigDict, field_serializer, field_validator
from pydantic.fields import AliasChoices


class Scale(Document):
    """Represents a truck scale (weighbridge) record.

    Based on the provided spreadsheet, we persist raw values and keep
    convenient cached fields for differences.

    Definitions used:
    - net_weight = gross_weight - tare_weight
    - kg_diff = net_weight - loaded_weight
    - pct_diff = (kg_diff / loaded_weight) * 100 (when loaded_weight > 0)

    Uniqueness: (farm_id, date, equipment) is expected to be unique.
    """

    date: dt.date = Field(..., description="Reference date (YYYY-MM-DD)")
    unit: str = Field(..., description="Production unit identifier (e.g., CAUA)")
    farm_id: str = Field(..., description="Associated Farm ID")

    equipment: str = Field(..., description="Truck identifier or number")

    loaded_weight: int = Field(
        ..., ge=0, description="Loaded weight recorded by loader (kg)",
        validation_alias=AliasChoices("loaded_weight", "carregamento"),
    )
    delivered_weight: Optional[int] = Field(
        default=None, ge=0, description="Delivered weight (kg) - optional",
        validation_alias=AliasChoices("delivered_weight", "fornecimento"),
    )
    gross_weight: int = Field(
        ..., ge=0, description="Scale reading when full (kg)",
        validation_alias=AliasChoices("gross_weight", "balanco_cheio"),
    )
    tare_weight: int = Field(
        ..., ge=0, description="Scale reading when empty (kg)",
        validation_alias=AliasChoices("tare_weight", "balanco_vazio"),
    )

    # Cached computed fields
    net_weight: int = Field(
        default=0, ge=0, description="Computed: gross_weight - tare_weight (kg)",
        validation_alias=AliasChoices("net_weight", "peso_balanco"),
    )
    kg_diff: int = Field(default=0, description="Computed: net_weight - loaded_weight (kg)")
    pct_diff: float = Field(default=0.0, description="% difference relative to loaded_weight")

    notes: Optional[str] = Field(default=None, description="Optional notes")

    class Settings:
        name = "scale"
        indexes = [
            __import__("pymongo").IndexModel(
                [("farm_id", __import__("pymongo").ASCENDING), ("date", __import__("pymongo").ASCENDING), ("equipment", __import__("pymongo").ASCENDING)],
                unique=True,
                name="uniq_farm_date_equipment",
            )
        ]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "_id": "683d1238fded441a09bdd9a1",
                "date": "2024-10-11",
                "unit": "CAUA",
                "farm_id": "683d1238fded441a09bdd6f0",
                "equipment": "Truck 23",
                "loaded_weight": 5945,
                "delivered_weight": 5890,
                "gross_weight": 22650,
                "tare_weight": 16810,
                "net_weight": 5840,
                "kg_diff": -105,
                "pct_diff": -1.77,
                "notes": "",
            }
        }
    )

    @staticmethod
    def _calc(net_weight: int, loaded_weight: int) -> tuple[int, float]:
        kg_diff = int(net_weight) - int(loaded_weight)
        pct = (kg_diff / loaded_weight * 100.0) if loaded_weight else 0.0
        return kg_diff, pct

    @field_validator("net_weight", mode="before")
    @classmethod
    def _ensure_net_weight(cls, v, info):
        # If not provided or mismatching, compute from the other fields
        data = info.data
        gross = data.get("gross_weight")
        tare = data.get("tare_weight")
        if gross is not None and tare is not None:
            try:
                return int(gross) - int(tare)
            except Exception:
                return v or 0
        return v or 0

    @field_validator("kg_diff", "pct_diff", mode="before")
    @classmethod
    def _ensure_diffs(cls, v, info):
        data = info.data
        loaded = data.get("loaded_weight")
        net = data.get("net_weight")
        if loaded is not None and net is not None:
            kg, pct = cls._calc(int(net), int(loaded))
            return kg if info.field_name == "kg_diff" else pct
        return v

    @field_serializer("id", when_used="json")
    def serialize_id(self, v):
        return str(v) if v is not None else None
