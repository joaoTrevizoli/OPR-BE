from __future__ import annotations

import datetime as dt
from typing import List, Optional

from fastapi import HTTPException

from project.api.models.penn_state import PennState
from project.api.models.farm import Farm
from project.api.models.user import User
from .schemas import PennStateCreate, PennStateRead, PennStateUpdate


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
    await doc.insert()
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
    if start_date or end_date:
        range_q = {}
        if start_date:
            range_q["$gte"] = start_date
        if end_date:
            range_q["$lte"] = end_date
        query[PennState.date] = range_q

    if user.is_admin:
        if farm_id:
            query[PennState.farm_id] = farm_id
    else:
        accessible_farms = await Farm.find({"$or": [{"owner_email": user.email}, {"shared_with": user.email}]}).to_list()
        accessible_ids = {str(f.id) for f in accessible_farms if f.id is not None}
        if farm_id:
            if farm_id not in accessible_ids:
                return []
            query[PennState.farm_id] = farm_id
        else:
            query[PennState.farm_id] = {"$in": list(accessible_ids) if accessible_ids else ["__none__"]}

    items = await PennState.find_many(query).sort("date").to_list()
    return [_to_read(it) for it in items]


async def get_entry(entry_id: str, user: User) -> PennStateRead:
    doc = await PennState.get(entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    if not user.is_admin:
        farm = await Farm.get(doc.farm_id)
        if not farm or (user.email != farm.owner_email and user.email not in (farm.shared_with or [])):
            raise HTTPException(status_code=403, detail="Access denied")
    return _to_read(doc)


async def update_entry(entry_id: str, updates: PennStateUpdate) -> PennStateRead:
    doc = await PennState.get(entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    data = updates.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(doc, k, v)
    await doc.save()
    return _to_read(doc)


async def delete_entry(entry_id: str) -> dict:
    doc = await PennState.get(entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    await doc.delete()
    return {"msg": "Entry deleted"}
