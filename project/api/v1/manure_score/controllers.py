from __future__ import annotations

import datetime as dt
from typing import List, Optional

from fastapi import HTTPException

from project.api.models.manure_score import ManureScore
from project.api.models.farm import Farm
from project.api.models.user import User
from .schemas import ManureScoreCreate, ManureScoreRead, ManureScoreUpdate


def _compute_total(payload: ManureScoreCreate | ManureScoreUpdate | ManureScore) -> int:
    return int(getattr(payload, "score_1", 0) or 0) + int(getattr(payload, "score_2", 0) or 0) + int(getattr(payload, "score_3", 0) or 0) + int(getattr(payload, "score_3_5", 0) or 0) + int(getattr(payload, "score_4", 0) or 0)


def _to_read(doc: ManureScore) -> ManureScoreRead:
    total = max(int(doc.total or 0), 0)
    if total <= 0:
        total = _compute_total(doc)
    def pct(v: int) -> float:
        return round((float(v) / float(total)) * 100.0, 1) if total > 0 else 0.0
    p1 = pct(doc.score_1)
    p2 = pct(doc.score_2)
    p3 = pct(doc.score_3)
    p35 = pct(doc.score_3_5)
    p4 = pct(doc.score_4)
    desirable = round(min(100.0, p3 + (p2/2)), 2)
    return ManureScoreRead(
        id=str(doc.id) if doc.id is not None else None,
        date=doc.date,
        unit=doc.unit,
        farm_id=doc.farm_id,
        diet=doc.diet,
        score_1=doc.score_1,
        score_2=doc.score_2,
        score_3=doc.score_3,
        score_3_5=doc.score_3_5,
        score_4=doc.score_4,
        total=total,
        pct_1=p1,
        pct_2=p2,
        pct_3=p3,
        pct_3_5=p35,
        pct_4=p4,
        desirable_pct=desirable,
    )


async def create_entry(payload: ManureScoreCreate) -> ManureScoreRead:
    # Validate farm existence with graceful handling of invalid IDs
    try:
        farm = await Farm.get(payload.farm_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid farm_id format")
    if not farm:
        raise HTTPException(status_code=400, detail="Invalid farm_id: farm not found")
    total = _compute_total(payload)
    doc = ManureScore(
        date=payload.date,
        unit=payload.unit,
        farm_id=payload.farm_id,
        diet=payload.diet,
        score_1=payload.score_1,
        score_2=payload.score_2,
        score_3=payload.score_3,
        score_3_5=payload.score_3_5,
        score_4=payload.score_4,
        total=total,
    )
    await doc.insert()
    return _to_read(doc)


async def list_entries(
    user: User,
    unit: Optional[str] = None,
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
    farm_id: Optional[str] = None,
    diet: Optional[str] = None,
) -> List[ManureScoreRead]:
    query: dict = {}
    if unit:
        query[ManureScore.unit] = unit
    if diet:
        query[ManureScore.diet] = diet
    if start_date or end_date:
        range_q = {}
        if start_date:
            range_q["$gte"] = start_date
        if end_date:
            range_q["$lte"] = end_date
        query[ManureScore.date] = range_q

    if user.is_admin:
        if farm_id:
            query[ManureScore.farm_id] = farm_id
    else:
        accessible_farms = await Farm.find({"$or": [{"owner_email": user.email}, {"shared_with": user.email}]}).to_list()
        accessible_ids = {str(f.id) for f in accessible_farms if f.id is not None}
        if farm_id:
            if farm_id not in accessible_ids:
                return []
            query[ManureScore.farm_id] = farm_id
        else:
            query[ManureScore.farm_id] = {"$in": list(accessible_ids) if accessible_ids else ["__none__"]}

    items = await ManureScore.find_many(query).sort("date").to_list()
    return [_to_read(it) for it in items]


async def get_entry(entry_id: str, user: User) -> ManureScoreRead:
    doc = await ManureScore.get(entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    if not user.is_admin:
        farm = await Farm.get(doc.farm_id)
        if not farm or (user.email != farm.owner_email and user.email not in (farm.shared_with or [])):
            raise HTTPException(status_code=403, detail="Access denied")
    return _to_read(doc)


async def update_entry(entry_id: str, updates: ManureScoreUpdate) -> ManureScoreRead:
    doc = await ManureScore.get(entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    data = updates.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(doc, k, v)
    doc.total = _compute_total(doc)
    await doc.save()
    return _to_read(doc)


async def delete_entry(entry_id: str) -> dict:
    doc = await ManureScore.get(entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    await doc.delete()
    return {"msg": "Entry deleted"}
