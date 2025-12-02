from __future__ import annotations

import datetime as dt
from typing import Optional

from beanie import Document
from pydantic import Field, ConfigDict, field_serializer, field_validator


class PennStateDiet(Document):
    """Penn State diet view with counts input, proportions, Effectiveness and FDNef.

    User enters the NUMBER of particles retained at each sieve and bottom plus
    the FDN (bromate) percentage. Backend computes:
    - total_count = sum of all four sieves
    - pct_19mm, pct_8mm, pct_1_18mm, pct_bottom (0–100) from counts
    - effectiveness_factor_pct = pct_19mm + pct_8mm + (pct_1_18mm / 2)
    - fdnef_pct = fdn_bromate_pct * (effectiveness_factor_pct / 100)

    All percentage fields are represented as 0–100 values.
    Uniqueness: (farm_id, date, diet).
    """

    date: dt.date = Field(..., description="Reference date for the sampling")
    unit: str = Field(..., description="Production unit identifier (e.g., CAUA)")
    farm_id: str = Field(..., description="Associated Farm (property) ID")
    diet: Optional[str] = Field(default=None, description="Diet name/category")
    sample: Optional[str] = Field(default=None, description="Optional sample name/label")

    # Raw inputs: counts from each sieve
    count_19mm: int = Field(default=0, ge=0, description="Count retained at 19 mm sieve")
    count_8mm: int = Field(default=0, ge=0, description="Count retained at 8 mm sieve")
    count_1_18mm: int = Field(default=0, ge=0, description="Count retained at 1.18 mm sieve")
    count_bottom: int = Field(default=0, ge=0, description="Count at bottom/fines")

    # Cached totals and proportions (computed from counts)
    total_count: int = Field(default=0, ge=0, description="Total observations (cached)")
    pct_19mm: float = Field(default=0.0, ge=0, le=100, description="Proportion at 19 mm sieve (%)")
    pct_8mm: float = Field(default=0.0, ge=0, le=100, description="Proportion at 8 mm sieve (%)")
    pct_1_18mm: float = Field(default=0.0, ge=0, le=100, description="Proportion at 1.18 mm sieve (%)")
    pct_bottom: float = Field(default=0.0, ge=0, le=100, description="Proportion at bottom/fines (%)")

    # Input: FDN bromate percentage
    fdn_bromate_pct: Optional[float] = Field(default=None, ge=0, le=100, description="FDN bromate (%)")

    # Cached computed fields
    effectiveness_factor_pct: float = Field(default=0.0, ge=0, le=100, description="Effectiveness Factor (%)")
    fdnef_pct: float = Field(default=0.0, ge=0, le=100, description="FDNef (%)")

    class Settings:
        name = "penn_state_diet"
        indexes = [
            __import__("pymongo").IndexModel(
                [("farm_id", __import__("pymongo").ASCENDING), ("date", __import__("pymongo").ASCENDING), ("diet", __import__("pymongo").ASCENDING)],
                unique=True,
                name="uniq_farm_date_diet",
            )
        ]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "_id": "683d1238fded441a09bdd750",
                "date": "2024-10-22",
                "unit": "CAUA",
                "farm_id": "683d1238fded441a09bdd6f0",
                "diet": "ADAPTATION",
                "sample": "SAMPLE A",
                # inputs (counts)
                "count_19mm": 8,
                "count_8mm": 17,
                "count_1_18mm": 3,
                "count_bottom": 32,
                # cached totals and proportions
                "total_count": 60,
                "pct_19mm": 13.33,
                "pct_8mm": 28.33,
                "pct_1_18mm": 5.00,
                "pct_bottom": 53.33,
                # inputs (FDN bromate) and results
                "fdn_bromate_pct": 57.7,
                "effectiveness_factor_pct": 13.33 + 28.33 + (5.0 / 2),
                "fdnef_pct": (57.7 * ((13.33 + 28.33 + (5.0 / 2)) / 100.0)),
            }
        }
    )

    @staticmethod
    def _sum_counts(a: Optional[int], b: Optional[int], c: Optional[int], d: Optional[int]) -> int:
        return int(a or 0) + int(b or 0) + int(c or 0) + int(d or 0)

    @staticmethod
    def _pct(part: Optional[int], total: int) -> float:
        try:
            p = float(part or 0)
            t = float(total or 0)
            if t == 0:
                return 0.0
            return 100.0 * (p / t)
        except Exception:
            return 0.0

    @staticmethod
    def _calc_effectiveness(p19: float, p8: float, p1_18: float) -> float:
        return float(p19 or 0.0) + float(p8 or 0.0) + (float(p1_18 or 0.0) / 2.0)

    @staticmethod
    def _calc_fdnef(fdn_bromate: Optional[float], effectiveness: float) -> float:
        if fdn_bromate is None:
            return 0.0
        return float(fdn_bromate) * (effectiveness / 100.0)

    @field_validator("total_count", mode="before")
    @classmethod
    def _ensure_total(cls, v, info):
        d = info.data
        return cls._sum_counts(d.get("count_19mm"), d.get("count_8mm"), d.get("count_1_18mm"), d.get("count_bottom"))

    @field_validator("pct_19mm", "pct_8mm", "pct_1_18mm", "pct_bottom", mode="before")
    @classmethod
    def _ensure_pcts(cls, v, info):
        d = info.data
        total = cls._sum_counts(d.get("count_19mm"), d.get("count_8mm"), d.get("count_1_18mm"), d.get("count_bottom"))
        if info.field_name == "pct_19mm":
            return cls._pct(d.get("count_19mm"), total)
        if info.field_name == "pct_8mm":
            return cls._pct(d.get("count_8mm"), total)
        if info.field_name == "pct_1_18mm":
            return cls._pct(d.get("count_1_18mm"), total)
        return cls._pct(d.get("count_bottom"), total)

    @field_validator("effectiveness_factor_pct", mode="before")
    @classmethod
    def _ensure_effectiveness(cls, v, info):
        d = info.data
        p19 = cls._pct(d.get("count_19mm"), cls._sum_counts(d.get("count_19mm"), d.get("count_8mm"), d.get("count_1_18mm"), d.get("count_bottom")))
        p8 = cls._pct(d.get("count_8mm"), cls._sum_counts(d.get("count_19mm"), d.get("count_8mm"), d.get("count_1_18mm"), d.get("count_bottom")))
        p118 = cls._pct(d.get("count_1_18mm"), cls._sum_counts(d.get("count_19mm"), d.get("count_8mm"), d.get("count_1_18mm"), d.get("count_bottom")))
        return cls._calc_effectiveness(p19, p8, p118)

    @field_validator("fdnef_pct", mode="before")
    @classmethod
    def _ensure_fdnef(cls, v, info):
        d = info.data
        total = cls._sum_counts(d.get("count_19mm"), d.get("count_8mm"), d.get("count_1_18mm"), d.get("count_bottom"))
        p19 = cls._pct(d.get("count_19mm"), total)
        p8 = cls._pct(d.get("count_8mm"), total)
        p118 = cls._pct(d.get("count_1_18mm"), total)
        eff = cls._calc_effectiveness(p19, p8, p118)
        return cls._calc_fdnef(d.get("fdn_bromate_pct"), eff)

    @field_serializer("id", when_used="json")
    def serialize_id(self, v):
        return str(v) if v is not None else None
