from __future__ import annotations

import datetime as dt
from typing import List, Optional

from fastapi import HTTPException

from project.api.models.penn_state import PennState
from project.api.models.farm import Farm
from project.api.models.user import User
from .schemas import PennStateCreate, PennStateRead, PennStateUpdate
from ...utils import get_doc_by_id, build_date_range_filter, apply_updates, get_accessible_farm_ids


def _to_read(doc: PennState) -> PennStateRead:
    i = float(doc.pct_19mm or 0.0)
    j = float(doc.pct_8mm or 0.0)
    k = float(doc.pct_3_8mm or 0.0)
    desirable = max(0.0, min(100.0, round(k + (j / 2.0) + (i / 3.0), 1)))
    return PennStateRead(
        id=str(doc.id) if doc.id is not None else None,
        date=doc.date,
        unit=doc.unit,
        farm_id=doc.farm_id,
        diet=doc.diet,
        pct_19mm=doc.pct_19mm,
        pct_8mm=doc.pct_8mm,
        pct_3_8mm=doc.pct_3_8mm,
        pct_fines=doc.pct_fines,
        desirable_pct=desirable,
    )


async def create_entry(payload: PennStateCreate) -> PennStateRead:
    # Validate farm existence with graceful handling of invalid IDs
    try:
        farm = await Farm.get(payload.farm_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid farm_id format")
    if not farm:
        raise HTTPException(status_code=400, detail="Invalid farm_id: farm not found")

    # Prevent duplicate by (farm_id, date, diet)
    existing = await PennState.find_one({
        PennState.farm_id: payload.farm_id,
        PennState.date: payload.date,
        PennState.diet: payload.diet,
    })
    if existing:
        raise HTTPException(status_code=409, detail="Entry already exists for this farm_id, date and diet")

    doc = PennState(
        date=payload.date,
        unit=payload.unit,
        farm_id=payload.farm_id,
        diet=payload.diet,
        pct_19mm=payload.pct_19mm,
        pct_8mm=payload.pct_8mm,
        pct_3_8mm=payload.pct_3_8mm,
        pct_fines=payload.pct_fines,
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
) -> List[PennStateRead]:
    query: dict = {}
    if unit:
        query[PennState.unit] = unit
    if diet:
        query[PennState.diet] = diet
    range_q = build_date_range_filter(start_date, end_date)
    if range_q:
        query[PennState.date] = range_q

    if user.is_admin:
        if farm_id:
            query[PennState.farm_id] = farm_id
    else:
        accessible_ids = await get_accessible_farm_ids(user)
        if farm_id:
            if farm_id not in accessible_ids:
                return []
            query[PennState.farm_id] = farm_id
        else:
            query[PennState.farm_id] = {"$in": list(accessible_ids) if accessible_ids else ["__none__"]}

    items = await PennState.find_many(query).sort("date").to_list()
    return [_to_read(it) for it in items]


async def get_entry(entry_id: str, user: User) -> PennStateRead:
    doc = await get_doc_by_id(PennState, entry_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    if not user.is_admin:
        farm = await Farm.get(doc.farm_id)
        if not farm or (user.email != farm.owner_email and user.email not in (farm.shared_with or [])):
            raise HTTPException(status_code=403, detail="Access denied")
    return _to_read(doc)


async def update_entry(entry_id: str, updates: PennStateUpdate) -> PennStateRead:
    doc = await get_doc_by_id(PennState, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    data = updates.model_dump(exclude_unset=True)
    apply_updates(doc, data)

    # Check for uniqueness conflict with updated keys
    conflict = await PennState.find_one({
        PennState.farm_id: doc.farm_id,
        PennState.date: doc.date,
        PennState.diet: doc.diet,
        "_id": {"$ne": doc.id},
    })
    if conflict:
        raise HTTPException(status_code=409, detail="Another entry already exists for this farm_id, date and diet")

    try:
        await doc.save()
    except Exception as e:
        if e.__class__.__name__ == "DuplicateKeyError":
            raise HTTPException(status_code=409, detail="Another entry already exists for this farm_id, date and diet")
        raise
    return _to_read(doc)


async def delete_entry(entry_id: str) -> dict:
    doc = await get_doc_by_id(PennState, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    await doc.delete()
    return {"msg": "Entry deleted"}
