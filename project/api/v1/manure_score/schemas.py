from __future__ import annotations

import datetime as dt
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


class ManureScoreBase(BaseModel):
    date: dt.date = Field(..., description="Reference date (YYYY-MM-DD)")
    unit: str = Field(..., description="Production unit identifier")
    farm_id: str = Field(..., description="Associated Farm ID")
    diet: Optional[str] = Field(default=None, description="Diet name/category")

    score_1: int = Field(default=0, ge=0)
    score_2: int = Field(default=0, ge=0)
    score_3: int = Field(default=0, ge=0)
    score_3_5: int = Field(default=0, ge=0)
    score_4: int = Field(default=0, ge=0)

    @field_validator("score_1", "score_2", "score_3", "score_3_5", "score_4", mode="before")
    @classmethod
    def _num_ok(cls, v):
        if v is None:
            return 0
        try:
            iv = int(v)
        except Exception:
            raise ValueError("Scores must be integers >= 0")
        if iv < 0:
            raise ValueError("Scores must be >= 0")
        return iv


class ManureScoreCreate(ManureScoreBase):
    pass


class ManureScoreUpdate(BaseModel):
    unit: Optional[str] = None
    diet: Optional[str] = None
    score_1: Optional[int] = Field(default=None, ge=0)
    score_2: Optional[int] = Field(default=None, ge=0)
    score_3: Optional[int] = Field(default=None, ge=0)
    score_3_5: Optional[int] = Field(default=None, ge=0)
    score_4: Optional[int] = Field(default=None, ge=0)


class ManureScoreRead(ManureScoreBase):
    id: Optional[str] = Field(default=None)
    total: int = Field(default=0, ge=0)
    pct_1: float = Field(default=0, ge=0, le=100)
    pct_2: float = Field(default=0, ge=0, le=100)
    pct_3: float = Field(default=0, ge=0, le=100)
    pct_3_5: float = Field(default=0, ge=0, le=100)
    pct_4: float = Field(default=0, ge=0, le=100)
    desirable_pct: float = Field(default=0, ge=0, le=100, description="% of feces in desirable score (3 + 3.5)")


class ManureScoreList(BaseModel):
    items: List[ManureScoreRead]
