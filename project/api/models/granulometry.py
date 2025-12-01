from __future__ import annotations

import datetime as dt
from typing import Optional

from beanie import Document
from pydantic import Field, ConfigDict, field_serializer, field_validator


class Granulometry(Document):
    """Granulometry (particle size) distribution by sieves.

    Inputs (counts) and whole-grain total; backend computes totals, proportions, and
    the granulometry index based on the provided spreadsheet formula:

        G = p6*6 + p3_25*avg(6,3.25) + p2*avg(3.25,2) + p1_25*avg(2,1.25) + p0*avg(1.25,0)

    where pX are proportions (fractions 0..1). We store proportions as 0–100, so the
    computation uses (pct/100).

    Uniqueness: (farm_id, date, sample) — sample is an optional label for the sample.
    """

    # Identifiers
    date: dt.date = Field(..., description="Reference date (YYYY-MM-DD)")
    unit: str = Field(..., description="Production unit identifier (e.g., CAUA)")
    farm_id: str = Field(..., description="Associated Farm ID")
    sample: Optional[str] = Field(default=None, description="Optional sample name/label")

    # Raw inputs: counts retained at each sieve
    count_6mm: int = Field(default=0, ge=0, description="Count at 6.00 mm sieve")
    count_3_25mm: int = Field(default=0, ge=0, description="Count at 3.25 mm sieve")
    count_2mm: int = Field(default=0, ge=0, description="Count at 2.00 mm sieve")
    count_1_25mm: int = Field(default=0, ge=0, description="Count at 1.25 mm sieve")
    count_bottom: int = Field(default=0, ge=0, description="Count at bottom (0 mm)")

    whole_grain_total: Optional[int] = Field(default=None, ge=0, description="Total whole grains observed")

    # Cached totals and proportions (0–100)
    total_count: int = Field(default=0, ge=0, description="Total count across all sieves (cached)")
    pct_6mm: float = Field(default=0.0, ge=0, le=100, description="% at 6.00 mm (0–100)")
    pct_3_25mm: float = Field(default=0.0, ge=0, le=100, description="% at 3.25 mm (0–100)")
    pct_2mm: float = Field(default=0.0, ge=0, le=100, description="% at 2.00 mm (0–100)")
    pct_1_25mm: float = Field(default=0.0, ge=0, le=100, description="% at 1.25 mm (0–100)")
    pct_bottom: float = Field(default=0.0, ge=0, le=100, description="% at bottom (0–100)")

    # Cached granulometry index result (mm)
    granulometry_mm: float = Field(default=0.0, description="Granulometry index (mm)")

    class Settings:
        name = "granulometry"
        indexes = [
            __import__("pymongo").IndexModel(
                [
                    ("farm_id", __import__("pymongo").ASCENDING),
                    ("date", __import__("pymongo").ASCENDING),
                    ("sample", __import__("pymongo").ASCENDING),
                ],
                unique=True,
                name="uniq_farm_date_sample",
            )
        ]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "_id": "683d1238fded441a09bded30",
                "date": "2024-10-15",
                "unit": "CAUA",
                "farm_id": "683d1238fded441a09bdd6f0",
                "sample": "CORN MEAL",
                "count_6mm": 0,
                "count_3_25mm": 20,
                "count_2mm": 118,
                "count_1_25mm": 140,
                "count_bottom": 17,
                "whole_grain_total": 0,
                "total_count": 295,
                "pct_6mm": 0.0,
                "pct_3_25mm": 6.78,
                "pct_2mm": 40.0,
                "pct_1_25mm": 47.46,
                "pct_bottom": 5.76,
                "granulometry_mm": 2.17,
            }
        }
    )

    # ---------- helpers ----------
    @staticmethod
    def _sum5(a: Optional[int], b: Optional[int], c: Optional[int], d: Optional[int], e: Optional[int]) -> int:
        return int(a or 0) + int(b or 0) + int(c or 0) + int(d or 0) + int(e or 0)

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
    def _granulometry(p6: float, p3_25: float, p2: float, p1_25: float, p0: float) -> float:
        # Convert to fractions
        f6 = p6 / 100.0
        f3 = p3_25 / 100.0
        f2 = p2 / 100.0
        f1 = p1_25 / 100.0
        f0 = p0 / 100.0
        return (
            f6 * 6.0
            + f3 * ((6.0 + 3.25) / 2.0)
            + f2 * ((3.25 + 2.0) / 2.0)
            + f1 * ((2.0 + 1.25) / 2.0)
            + f0 * ((1.25 + 0.0) / 2.0)
        )

    # ---------- cached computations via validators ----------
    @field_validator("total_count", mode="before")
    @classmethod
    def _ensure_total(cls, v, info):
        d = info.data
        return cls._sum5(d.get("count_6mm"), d.get("count_3_25mm"), d.get("count_2mm"), d.get("count_1_25mm"), d.get("count_bottom"))

    @field_validator("pct_6mm", "pct_3_25mm", "pct_2mm", "pct_1_25mm", "pct_bottom", mode="before")
    @classmethod
    def _ensure_pcts(cls, v, info):
        d = info.data
        total = cls._sum5(d.get("count_6mm"), d.get("count_3_25mm"), d.get("count_2mm"), d.get("count_1_25mm"), d.get("count_bottom"))
        field = info.field_name
        if field == "pct_6mm":
            return cls._pct(d.get("count_6mm"), total)
        if field == "pct_3_25mm":
            return cls._pct(d.get("count_3_25mm"), total)
        if field == "pct_2mm":
            return cls._pct(d.get("count_2mm"), total)
        if field == "pct_1_25mm":
            return cls._pct(d.get("count_1_25mm"), total)
        return cls._pct(d.get("count_bottom"), total)

    @field_validator("granulometry_mm", mode="before")
    @classmethod
    def _ensure_granulometry(cls, v, info):
        d = info.data
        total = cls._sum5(d.get("count_6mm"), d.get("count_3_25mm"), d.get("count_2mm"), d.get("count_1_25mm"), d.get("count_bottom"))
        p6 = cls._pct(d.get("count_6mm"), total)
        p3 = cls._pct(d.get("count_3_25mm"), total)
        p2 = cls._pct(d.get("count_2mm"), total)
        p1 = cls._pct(d.get("count_1_25mm"), total)
        p0 = cls._pct(d.get("count_bottom"), total)
        return cls._granulometry(p6, p3, p2, p1, p0)

    @field_serializer("id", when_used="json")
    def serialize_id(self, v):
        return str(v) if v is not None else None
