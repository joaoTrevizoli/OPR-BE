from __future__ import annotations

import datetime as dt
from typing import List, Optional

from fastapi import HTTPException

from project.api.models.penn_state_diet import PennStateDiet
from project.api.models.farm import Farm
from project.api.models.user import User
from .schemas import PennStateDietCreate, PennStateDietRead, PennStateDietUpdate
from ...utils import get_doc_by_id, build_date_range_filter, apply_updates, get_accessible_farm_ids


def _sum4(a: int | None, b: int | None, c: int | None, d: int | None) -> int:
    return int(a or 0) + int(b or 0) + int(c or 0) + int(d or 0)


def _pct(part: int | None, total: int) -> float:
    try:
        p = float(part or 0)
        t = float(total or 0)
        if t == 0:
            return 0.0
        return 100.0 * (p / t)
    except Exception:
        return 0.0


def _recompute(doc: PennStateDiet) -> None:
    total = _sum4(doc.count_19mm, doc.count_8mm, doc.count_1_18mm, doc.count_bottom)
    doc.total_count = total
    doc.pct_19mm = _pct(doc.count_19mm, total)
    doc.pct_8mm = _pct(doc.count_8mm, total)
    doc.pct_1_18mm = _pct(doc.count_1_18mm, total)
    doc.pct_bottom = _pct(doc.count_bottom, total)

    eff = float(doc.pct_19mm) + float(doc.pct_8mm) + (float(doc.pct_1_18mm) / 2.0)
    doc.effectiveness_factor_pct = eff
    fdn = float(doc.fdn_bromate_pct or 0.0)
    doc.fdnef_pct = fdn * (eff / 100.0)


async def create_entry(payload: PennStateDietCreate) -> PennStateDietRead:
    # Validate farm
    try:
        farm = await Farm.get(payload.farm_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid farm_id format")
    if not farm:
        raise HTTPException(status_code=400, detail="Invalid farm_id: farm not found")

    # Prevent duplicates
    existing = await PennStateDiet.find_one({
        PennStateDiet.farm_id: payload.farm_id,
        PennStateDiet.date: payload.date,
        PennStateDiet.diet: payload.diet,
    })
    if existing:
        raise HTTPException(status_code=409, detail="Entry already exists for this farm_id, date and diet")

    doc = PennStateDiet(**payload.model_dump())
    _recompute(doc)
    try:
        await doc.insert()
    except Exception as e:
        if e.__class__.__name__ == "DuplicateKeyError":
            raise HTTPException(status_code=409, detail="Entry already exists for this farm_id, date and diet")
        raise
    return PennStateDietRead(**doc.model_dump(mode="json"))


async def list_entries(
    user: User,
    unit: Optional[str] = None,
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
    farm_id: Optional[str] = None,
    diet: Optional[str] = None,
) -> List[PennStateDietRead]:
    query: dict = {}
    if unit:
        query[PennStateDiet.unit] = unit
    if diet:
        query[PennStateDiet.diet] = diet
    range_q = build_date_range_filter(start_date, end_date)
    if range_q:
        query[PennStateDiet.date] = range_q

    if user.is_admin:
        if farm_id:
            query[PennStateDiet.farm_id] = farm_id
    else:
        accessible_ids = await get_accessible_farm_ids(user)
        if farm_id:
            if farm_id not in accessible_ids:
                return []
            query[PennStateDiet.farm_id] = farm_id
        else:
            query[PennStateDiet.farm_id] = {"$in": list(accessible_ids) if accessible_ids else ["__none__"]}

    items = await PennStateDiet.find_many(query).sort("date").to_list()
    return [PennStateDietRead(**it.model_dump(mode="json")) for it in items]


async def get_entry(entry_id: str, user: User) -> PennStateDietRead:
    doc = await get_doc_by_id(PennStateDiet, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    if not user.is_admin:
        farm = await Farm.get(doc.farm_id)
        if not farm or (user.email != farm.owner_email and user.email not in (farm.shared_with or [])):
            raise HTTPException(status_code=403, detail="Access denied")
    return PennStateDietRead(**doc.model_dump(mode="json"))


async def update_entry(entry_id: str, updates: PennStateDietUpdate) -> PennStateDietRead:
    doc = await get_doc_by_id(PennStateDiet, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    data = updates.model_dump(exclude_unset=True)
    apply_updates(doc, data)
    _recompute(doc)

    conflict = await PennStateDiet.find_one({
        PennStateDiet.farm_id: doc.farm_id,
        PennStateDiet.date: doc.date,
        PennStateDiet.diet: doc.diet,
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
    return PennStateDietRead(**doc.model_dump(mode="json"))


async def delete_entry(entry_id: str) -> dict:
    doc = await get_doc_by_id(PennStateDiet, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    await doc.delete()
    return {"msg": "Entry deleted"}
