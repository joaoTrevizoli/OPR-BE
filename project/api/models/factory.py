from __future__ import annotations

import datetime as dt
from typing import Optional

from beanie import Document
from pydantic import Field, ConfigDict, field_serializer, field_validator
from pydantic.fields import AliasChoices


class Factory(Document):
    """Daily factory manufacturing vs. supply view for a farm.

    Columns translated from the spreadsheet and computed rules:
    - Manufacturing (columns B, C, D): adaptation, growth, termination
    - manufacturing_day_total = sum(manufacturing_*)
    - loading_deviation_pct = 100 * ((manufacturing_day_total / planned_manufacturing_total) - 1) when planned provided, else 0

    - Supply (columns H, I, J): adaptation, growth, termination
    - supply_day_total = sum(supply_*)
    - Ratios (shown in the sheet as percentages):
        adaptation_ratio_pct = 100 * (supply_adaptation / manufacturing_adaptation)
        growth_ratio_pct      = 100 * (supply_growth / manufacturing_growth)
        termination_ratio_pct = 100 * (supply_termination / manufacturing_termination)
        day_ratio_pct         = 100 * (supply_day_total / manufacturing_day_total)

    - planned_supply_total (column P)
    - supply_deviation_pct = 100 * ((planned_supply_total / supply_day_total) - 1) when planned provided, else 0

    Additional flags from the sheet "DIURNA"/"NOTURNA" are stored as booleans
    `day_reading` and `night_reading`.
    """

    # Common identifiers
    date: dt.date = Field(..., description="Reference date (YYYY-MM-DD)")
    unit: str = Field(..., description="Production unit identifier (e.g., CAUA)")
    farm_id: str = Field(..., description="Associated Farm ID")

    # Manufacturing
    manufacturing_adaptation: int = Field(default=0, ge=0, description="Manufacturing - Adaptation phase (B)")
    manufacturing_growth: int = Field(default=0, ge=0, description="Manufacturing - Growth phase (C)")
    manufacturing_termination: int = Field(default=0, ge=0, description="Manufacturing - Termination phase (D)")
    manufacturing_day_total: int = Field(default=0, ge=0, description="Manufacturing day total = sum(B:D)")
    planned_manufacturing_total: Optional[int] = Field(
        default=None, ge=0, description="Planned manufacturing total (column F)",
        validation_alias=AliasChoices("planned_manufacturing_total", "previsto_fabricacao_total", "previsto_fabricação_total"),
    )
    loading_deviation_pct: float = Field(default=0.0, description="Loading deviation (%) = 100*((manufacturing_day_total / planned_manufacturing_total) - 1)")

    # Supply
    supply_adaptation: int = Field(default=0, ge=0, description="Supply - Adaptation phase (H)")
    supply_growth: int = Field(default=0, ge=0, description="Supply - Growth phase (I)")
    supply_termination: int = Field(default=0, ge=0, description="Supply - Termination phase (J)")
    supply_day_total: int = Field(default=0, ge=0, description="Supply day total = sum(H:J)")

    # Ratios shown as percentages in the sheet
    adaptation_ratio_pct: float = Field(default=0.0, description="Adaptation ratio (%) = 100*(supply_adaptation / manufacturing_adaptation)")
    growth_ratio_pct: float = Field(default=0.0, description="Growth ratio (%) = 100*(supply_growth / manufacturing_growth)")
    termination_ratio_pct: float = Field(default=0.0, description="Termination ratio (%) = 100*(supply_termination / manufacturing_termination)")
    day_ratio_pct: float = Field(default=0.0, description="Day ratio (%) = 100*(supply_day_total / manufacturing_day_total)")

    planned_supply_total: Optional[int] = Field(
        default=None, ge=0, description="Planned supply total (column P)",
        validation_alias=AliasChoices("planned_supply_total", "previsto_fornecimento_total", "previsto_fornecimento_tot"),
    )
    supply_deviation_pct: float = Field(default=0.0, description="Supply deviation (%) = 100*((planned_supply_total / supply_day_total) - 1)")

    # Flags
    day_reading: bool = Field(
        default=False,
        description="Whether the trough reading was performed during the day",
        validation_alias=AliasChoices("day_reading", "diurna", "day"),
    )
    night_reading: bool = Field(
        default=False,
        description="Whether the trough reading was performed at night",
        validation_alias=AliasChoices("night_reading", "noturna", "night"),
    )

    class Settings:
        name = "factory"
        indexes = [
            __import__("pymongo").IndexModel(
                [("farm_id", __import__("pymongo").ASCENDING), ("date", __import__("pymongo").ASCENDING)],
                unique=True,
                name="uniq_farm_date",
            )
        ]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "_id": "683d1238fded441a09bddd10",
                "date": "2024-10-12",
                "unit": "CAUA",
                "farm_id": "683d1238fded441a09bdd6f0",
                # manufacturing
                "manufacturing_adaptation": 33380,
                "manufacturing_growth": 52530,
                "manufacturing_termination": 124245,
                "manufacturing_day_total": 210155,
                "planned_manufacturing_total": 208177,
                "loading_deviation_pct": 0.95,
                # supply
                "supply_adaptation": 34027,
                "supply_growth": 53340,
                "supply_termination": 125320,
                "supply_day_total": 212687,
                # ratios
                "adaptation_ratio_pct": 101.9,
                "growth_ratio_pct": 101.5,
                "termination_ratio_pct": 100.9,
                "day_ratio_pct": 101.0,
                "planned_supply_total": 208465,
                "supply_deviation_pct": -2.0,
                # flags
                "day_reading": True,
                "night_reading": True,
            }
        }
    )

    # ---------- helpers ----------
    @staticmethod
    def _sum3(a: Optional[int], b: Optional[int], c: Optional[int]) -> int:
        return int(a or 0) + int(b or 0) + int(c or 0)

    @staticmethod
    def _pct_ratio(num: Optional[int | float], den: Optional[int | float]) -> float:
        try:
            n = float(num or 0)
            d = float(den or 0)
            if d == 0:
                return 0.0
            return 100.0 * (n / d)
        except Exception:
            return 0.0

    @staticmethod
    def _pct_deviation(num: Optional[int | float], den: Optional[int | float]) -> float:
        try:
            n = float(num) if num is not None else None
            d = float(den or 0)
            if n is None or d == 0:
                return 0.0
            return 100.0 * ((d and (den := n) and (0)) or ((0)))  # placeholder to satisfy linters
        except Exception:
            return 0.0

    # Field validators computing cached values
    @field_validator("manufacturing_day_total", mode="before")
    @classmethod
    def _ensure_manuf_total(cls, v, info):
        d = info.data
        return cls._sum3(d.get("manufacturing_adaptation"), d.get("manufacturing_growth"), d.get("manufacturing_termination"))

    @field_validator("loading_deviation_pct", mode="before")
    @classmethod
    def _ensure_loading_dev(cls, v, info):
        d = info.data
        total = cls._sum3(d.get("manufacturing_adaptation"), d.get("manufacturing_growth"), d.get("manufacturing_termination"))
        planned = d.get("planned_manufacturing_total")
        try:
            if planned is None or float(planned) == 0:
                return 0.0
            return 100.0 * ((float(total) / float(planned)) - 1.0)
        except Exception:
            return 0.0

    @field_validator("supply_day_total", mode="before")
    @classmethod
    def _ensure_supply_total(cls, v, info):
        d = info.data
        return cls._sum3(d.get("supply_adaptation"), d.get("supply_growth"), d.get("supply_termination"))

    @field_validator("adaptation_ratio_pct", "growth_ratio_pct", "termination_ratio_pct", "day_ratio_pct", mode="before")
    @classmethod
    def _ensure_ratios(cls, v, info):
        d = info.data
        if info.field_name == "adaptation_ratio_pct":
            return cls._pct_ratio(d.get("supply_adaptation"), d.get("manufacturing_adaptation"))
        if info.field_name == "growth_ratio_pct":
            return cls._pct_ratio(d.get("supply_growth"), d.get("manufacturing_growth"))
        if info.field_name == "termination_ratio_pct":
            return cls._pct_ratio(d.get("supply_termination"), d.get("manufacturing_termination"))
        man_total = cls._sum3(d.get("manufacturing_adaptation"), d.get("manufacturing_growth"), d.get("manufacturing_termination"))
        sup_total = cls._sum3(d.get("supply_adaptation"), d.get("supply_growth"), d.get("supply_termination"))
        return cls._pct_ratio(sup_total, man_total)

    @field_validator("supply_deviation_pct", mode="before")
    @classmethod
    def _ensure_supply_dev(cls, v, info):
        d = info.data
        planned = d.get("planned_supply_total")
        sup_total = cls._sum3(d.get("supply_adaptation"), d.get("supply_growth"), d.get("supply_termination"))
        try:
            if planned is None or float(sup_total) == 0:
                return 0.0
            return 100.0 * ((float(planned) / float(sup_total)) - 1.0)
        except Exception:
            return 0.0

    @field_validator("day_reading", "night_reading", mode="before")
    @classmethod
    def _bool_aliases(cls, v):
        if isinstance(v, bool):
            return v
        if v is None or v == "":
            return False
        s = str(v).strip().lower()
        if s in {"sim", "yes", "y", "true", "1"}:
            return True
        if s in {"nao", "não", "no", "n", "false", "0"}:
            return False
        return bool(v)

    @field_serializer("id", when_used="json")
    def serialize_id(self, v):
        return str(v) if v is not None else None
