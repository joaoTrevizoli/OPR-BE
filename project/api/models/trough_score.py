from __future__ import annotations

import datetime as dt
from typing import Optional

from beanie import Document
from pydantic import Field, ConfigDict, field_serializer, field_validator


class TroughScore(Document):
    """Water Trough Score per farm and date.

    Based on the provided table ("Escore de Bebedouro"), this model stores the
    counts of observations classified as 1, 2, or 3 and keeps cached totals and
    percentages for convenience.

    - total = score_1 + score_2 + score_3
    - pct_score_1 = 100 * score_1 / total (when total > 0 else 0)
    - pct_score_2 = 100 * score_2 / total (when total > 0 else 0)
    - pct_score_3 = 100 * score_3 / total (when total > 0 else 0)

    Uniqueness: (farm_id, date)
    """

    date: dt.date = Field(..., description="Reference date (YYYY-MM-DD)")
    unit: str = Field(..., description="Production unit identifier (e.g., CAUA)")
    farm_id: str = Field(..., description="Associated Farm ID")

    score_1: int = Field(default=0, ge=0, description="Count with water trough score 1")
    score_2: int = Field(default=0, ge=0, description="Count with water trough score 2")
    score_3: int = Field(default=0, ge=0, description="Count with water trough score 3")

    # Cached fields
    total: int = Field(default=0, ge=0, description="Total observations (cached)")
    pct_score_1: float = Field(default=0.0, ge=0, le=100, description="% of score 1 (0–100)")
    pct_score_2: float = Field(default=0.0, ge=0, le=100, description="% of score 2 (0–100)")
    pct_score_3: float = Field(default=0.0, ge=0, le=100, description="% of score 3 (0–100)")

    class Settings:
        name = "trough_score"
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
                "_id": "683d1238fded441a09bdde01",
                "date": "2024-10-11",
                "unit": "CAUA",
                "farm_id": "683d1238fded441a09bdd6f0",
                "score_1": 6,
                "score_2": 8,
                "score_3": 5,
                "total": 19,
                "pct_score_1": 31.58,
                "pct_score_2": 42.11,
                "pct_score_3": 26.32,
            }
        }
    )

    # -------- helpers --------
    @staticmethod
    def _sum3(a: Optional[int], b: Optional[int], c: Optional[int]) -> int:
        return int(a or 0) + int(b or 0) + int(c or 0)

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

    # -------- cached computations via validators --------
    @field_validator("total", mode="before")
    @classmethod
    def _ensure_total(cls, v, info):
        d = info.data
        return cls._sum3(d.get("score_1"), d.get("score_2"), d.get("score_3"))

    @field_validator("pct_score_1", "pct_score_2", "pct_score_3", mode="before")
    @classmethod
    def _ensure_pcts(cls, v, info):
        d = info.data
        total = cls._sum3(d.get("score_1"), d.get("score_2"), d.get("score_3"))
        if info.field_name == "pct_score_1":
            return cls._pct(d.get("score_1"), total)
        if info.field_name == "pct_score_2":
            return cls._pct(d.get("score_2"), total)
        return cls._pct(d.get("score_3"), total)

    @field_serializer("id", when_used="json")
    def serialize_id(self, v):
        return str(v) if v is not None else None
