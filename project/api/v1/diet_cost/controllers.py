from __future__ import annotations

import datetime as dt
from typing import List, Optional

from fastapi import HTTPException

from project.api.models.diet_cost import DietCost
from project.api.models.farm import Farm
from project.api.models.user import User
from .schemas import DietCostCreate, DietCostRead, DietCostUpdate
from ...utils import get_doc_by_id, build_date_range_filter, apply_updates, get_accessible_farm_ids


async def create_entry(payload: DietCostCreate) -> DietCostRead:
    # Validate farm existence with graceful handling of invalid IDs
    try:
        farm = await Farm.get(payload.farm_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid farm_id format")
    if not farm:
        raise HTTPException(status_code=400, detail="Invalid farm_id: farm not found")

    # Prevent duplicate by (farm_id, date, diet)
    existing = await DietCost.find_one({
        DietCost.farm_id: payload.farm_id,
        DietCost.date: payload.date,
        DietCost.diet: payload.diet,
    })
    if existing:
        raise HTTPException(status_code=409, detail="Entry already exists for this farm_id, date and diet")

    doc = DietCost(
        date=payload.date,
        unit=payload.unit,
        farm_id=payload.farm_id,
        diet=payload.diet,
        cost_mn_per_ton=payload.cost_mn_per_ton,
        cost_ms_per_ton=payload.cost_ms_per_ton,
        time_in_diet_days=payload.time_in_diet_days,
        cost_mn_per_phase=payload.cost_mn_per_phase,
        cost_ms_per_phase=payload.cost_ms_per_phase,
    )
    try:
        await doc.insert()
    except Exception as e:
        # Fallback if DB unique index rejects duplicate
        if e.__class__.__name__ == "DuplicateKeyError":
            raise HTTPException(status_code=409, detail="Entry already exists for this farm_id, date and diet")
        raise
    return DietCostRead(**doc.model_dump(mode="json"))


async def list_entries(
    user: User,
    unit: Optional[str] = None,
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
    farm_id: Optional[str] = None,
    diet: Optional[str] = None,
) -> List[DietCostRead]:
    query: dict = {}
    if unit:
        query[DietCost.unit] = unit
    if diet:
        query[DietCost.diet] = diet
    range_q = build_date_range_filter(start_date, end_date)
    if range_q:
        query[DietCost.date] = range_q

    if user.is_admin:
        if farm_id:
            query[DietCost.farm_id] = farm_id
    else:
        accessible_ids = await get_accessible_farm_ids(user)
        if farm_id:
            if farm_id not in accessible_ids:
                return []
            query[DietCost.farm_id] = farm_id
        else:
            query[DietCost.farm_id] = {"$in": list(accessible_ids) if accessible_ids else ["__none__"]}

    items = await DietCost.find_many(query).sort("date").to_list()
    return [DietCostRead(**it.model_dump(mode="json")) for it in items]


async def get_entry(entry_id: str, user: User) -> DietCostRead:
    doc = await get_doc_by_id(DietCost, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    if not user.is_admin:
        farm = await Farm.get(doc.farm_id)
        if not farm or (user.email != farm.owner_email and user.email not in (farm.shared_with or [])):
            raise HTTPException(status_code=403, detail="Access denied")
    return DietCostRead(**doc.model_dump(mode="json"))


async def update_entry(entry_id: str, updates: DietCostUpdate) -> DietCostRead:
    doc = await get_doc_by_id(DietCost, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    data = updates.model_dump(exclude_unset=True)
    apply_updates(doc, data)

    # Check for uniqueness conflict with updated keys
    conflict = await DietCost.find_one({
        DietCost.farm_id: doc.farm_id,
        DietCost.date: doc.date,
        DietCost.diet: doc.diet,
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
    return DietCostRead(**doc.model_dump(mode="json"))


async def delete_entry(entry_id: str) -> dict:
    doc = await get_doc_by_id(DietCost, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    await doc.delete()
    return {"msg": "Entry deleted"}
