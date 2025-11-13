from __future__ import annotations

import datetime as dt
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


class TroughScoreBase(BaseModel):
    date: dt.date = Field(..., description="Reference date (YYYY-MM-DD)")
    unit: str = Field(..., description="Production unit identifier")
    farm_id: str = Field(..., description="Associated Farm ID")

    score_1: Optional[int] = Field(default=0, ge=0)
    score_2: Optional[int] = Field(default=0, ge=0)
    score_3: Optional[int] = Field(default=0, ge=0)

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

    @field_validator('score_1', 'score_2', 'score_3', mode='before')
    @classmethod
    def int_ok(cls, v):
        return cls._coerce_int(v)


class TroughScoreCreate(TroughScoreBase):
    pass


class TroughScoreUpdate(BaseModel):
    score_1: Optional[int] = Field(default=None, ge=0)
    score_2: Optional[int] = Field(default=None, ge=0)
    score_3: Optional[int] = Field(default=None, ge=0)

    @field_validator('score_1', 'score_2', 'score_3', mode='before')
    @classmethod
    def int_ok(cls, v):
        return TroughScoreBase._coerce_int(v)


class TroughScoreRead(TroughScoreBase):
    id: Optional[str] = Field(default=None)
    total: int = Field(default=0)
    pct_score_1: float = Field(default=0.0)
    pct_score_2: float = Field(default=0.0)
    pct_score_3: float = Field(default=0.0)


class TroughScoreList(BaseModel):
    items: List[TroughScoreRead]
