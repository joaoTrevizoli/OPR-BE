from __future__ import annotations

import datetime as dt
from typing import List, Optional

from fastapi import HTTPException

from project.api.models.trough_score import TroughScore
from project.api.models.farm import Farm
from project.api.models.user import User
from .schemas import TroughScoreCreate, TroughScoreRead, TroughScoreUpdate
from ...utils import get_doc_by_id, build_date_range_filter, apply_updates, get_accessible_farm_ids


def _sum3(a: Optional[int], b: Optional[int], c: Optional[int]) -> int:
    return int(a or 0) + int(b or 0) + int(c or 0)


def _recompute(doc: TroughScore) -> None:
    total = _sum3(doc.score_1, doc.score_2, doc.score_3)
    doc.total = total
    try:
        if total > 0:
            doc.pct_score_1 = 100.0 * (float(doc.score_1 or 0) / float(total))
            doc.pct_score_2 = 100.0 * (float(doc.score_2 or 0) / float(total))
            doc.pct_score_3 = 100.0 * (float(doc.score_3 or 0) / float(total))
        else:
            doc.pct_score_1 = doc.pct_score_2 = doc.pct_score_3 = 0.0
    except Exception:
        doc.pct_score_1 = doc.pct_score_2 = doc.pct_score_3 = 0.0


async def create_entry(payload: TroughScoreCreate) -> TroughScoreRead:
    # Validate farm
    try:
        farm = await Farm.get(payload.farm_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid farm_id format")
    if not farm:
        raise HTTPException(status_code=400, detail="Invalid farm_id: farm not found")

    # Prevent duplicates by (farm_id, date)
    existing = await TroughScore.find_one({
        TroughScore.farm_id: payload.farm_id,
        TroughScore.date: payload.date,
    })
    if existing:
        raise HTTPException(status_code=409, detail="Entry already exists for this farm_id and date")

    doc = TroughScore(**payload.model_dump())
    _recompute(doc)
    try:
        await doc.insert()
    except Exception as e:
        if e.__class__.__name__ == "DuplicateKeyError":
            raise HTTPException(status_code=409, detail="Entry already exists for this farm_id and date")
        raise
    return TroughScoreRead(**doc.model_dump(mode="json"))


async def list_entries(
    user: User,
    unit: Optional[str] = None,
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
    farm_id: Optional[str] = None,
) -> List[TroughScoreRead]:
    query: dict = {}
    if unit:
        query[TroughScore.unit] = unit
    range_q = build_date_range_filter(start_date, end_date)
    if range_q:
        query[TroughScore.date] = range_q

    if user.is_admin:
        if farm_id:
            query[TroughScore.farm_id] = farm_id
    else:
        accessible_ids = await get_accessible_farm_ids(user)
        if farm_id:
            if farm_id not in accessible_ids:
                return []
            query[TroughScore.farm_id] = farm_id
        else:
            query[TroughScore.farm_id] = {"$in": list(accessible_ids) if accessible_ids else ["__none__"]}

    items = await TroughScore.find_many(query).sort("date").to_list()
    return [TroughScoreRead(**it.model_dump(mode="json")) for it in items]


async def get_entry(entry_id: str, user: User) -> TroughScoreRead:
    doc = await get_doc_by_id(TroughScore, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    if not user.is_admin:
        farm = await Farm.get(doc.farm_id)
        if not farm or (user.email != farm.owner_email and user.email not in (farm.shared_with or [])):
            raise HTTPException(status_code=403, detail="Access denied")
    return TroughScoreRead(**doc.model_dump(mode="json"))


async def update_entry(entry_id: str, updates: TroughScoreUpdate) -> TroughScoreRead:
    doc = await get_doc_by_id(TroughScore, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    data = updates.model_dump(exclude_unset=True)
    apply_updates(doc, data)
    _recompute(doc)

    # Ensure uniqueness (farm_id, date) remains
    conflict = await TroughScore.find_one({
        TroughScore.farm_id: doc.farm_id,
        TroughScore.date: doc.date,
        "_id": {"$ne": doc.id},
    })
    if conflict:
        raise HTTPException(status_code=409, detail="Another entry already exists for this farm_id and date")

    try:
        await doc.save()
    except Exception as e:
        if e.__class__.__name__ == "DuplicateKeyError":
            raise HTTPException(status_code=409, detail="Another entry already exists for this farm_id and date")
        raise
    return TroughScoreRead(**doc.model_dump(mode="json"))


async def delete_entry(entry_id: str) -> dict:
    doc = await get_doc_by_id(TroughScore, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    await doc.delete()
    return {"msg": "Entry deleted"}
