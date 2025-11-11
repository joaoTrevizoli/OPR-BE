from __future__ import annotations

import datetime as dt
from typing import List, Optional

from fastapi import HTTPException

from project.api.models.manure_score import ManureScore
from project.api.models.farm import Farm
from project.api.models.user import User
from .schemas import ManureScoreCreate, ManureScoreRead, ManureScoreUpdate
from ...utils import get_doc_by_id, build_date_range_filter, apply_updates, get_accessible_farm_ids


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

    # Prevent duplicate by (farm_id, date, diet)
    existing = await ManureScore.find_one({
        ManureScore.farm_id: payload.farm_id,
        ManureScore.date: payload.date,
        ManureScore.diet: payload.diet,
    })
    if existing:
        raise HTTPException(status_code=409, detail="Entry already exists for this farm_id, date and diet")

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
    try:
        await doc.insert()
    except Exception as e:
        if e.__class__.__name__ == "DuplicateKeyError":
            raise HTTPException(status_code=409, detail="Entry already exists for this farm_id, date and diet")
        raise
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
    range_q = build_date_range_filter(start_date, end_date)
    if range_q:
        query[ManureScore.date] = range_q

    if user.is_admin:
        if farm_id:
            query[ManureScore.farm_id] = farm_id
    else:
        accessible_ids = await get_accessible_farm_ids(user)
        if farm_id:
            if farm_id not in accessible_ids:
                return []
            query[ManureScore.farm_id] = farm_id
        else:
            query[ManureScore.farm_id] = {"$in": list(accessible_ids) if accessible_ids else ["__none__"]}

    items = await ManureScore.find_many(query).sort("date").to_list()
    return [_to_read(it) for it in items]


async def get_entry(entry_id: str, user: User) -> ManureScoreRead:
    doc = await get_doc_by_id(ManureScore, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    if not user.is_admin:
        farm = await Farm.get(doc.farm_id)
        if not farm or (user.email != farm.owner_email and user.email not in (farm.shared_with or [])):
            raise HTTPException(status_code=403, detail="Access denied")
    return _to_read(doc)


async def update_entry(entry_id: str, updates: ManureScoreUpdate) -> ManureScoreRead:
    doc = await get_doc_by_id(ManureScore, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    data = updates.model_dump(exclude_unset=True)
    apply_updates(doc, data)

    # Check for uniqueness conflict with updated keys
    conflict = await ManureScore.find_one({
        ManureScore.farm_id: doc.farm_id,
        ManureScore.date: doc.date,
        ManureScore.diet: doc.diet,
        "_id": {"$ne": doc.id},
    })
    if conflict:
        raise HTTPException(status_code=409, detail="Another entry already exists for this farm_id, date and diet")

    doc.total = _compute_total(doc)
    try:
        await doc.save()
    except Exception as e:
        if e.__class__.__name__ == "DuplicateKeyError":
            raise HTTPException(status_code=409, detail="Another entry already exists for this farm_id, date and diet")
        raise
    return _to_read(doc)


async def delete_entry(entry_id: str) -> dict:
    doc = await get_doc_by_id(ManureScore, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    await doc.delete()
    return {"msg": "Entry deleted"}
