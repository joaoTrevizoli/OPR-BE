from __future__ import annotations

import datetime as dt
from typing import List, Optional

from fastapi import HTTPException

from project.api.models.diet_cost import DietCost
from project.api.models.farm import Farm
from project.api.models.user import User
from .schemas import DietCostCreate, DietCostRead, DietCostUpdate


async def create_entry(payload: DietCostCreate) -> DietCostRead:
    # Validate farm existence with graceful handling of invalid IDs
    try:
        farm = await Farm.get(payload.farm_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid farm_id format")
    if not farm:
        raise HTTPException(status_code=400, detail="Invalid farm_id: farm not found")

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
    await doc.insert()
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
    if start_date or end_date:
        range_q = {}
        if start_date:
            range_q["$gte"] = start_date
        if end_date:
            range_q["$lte"] = end_date
        query[DietCost.date] = range_q

    if user.is_admin:
        if farm_id:
            query[DietCost.farm_id] = farm_id
    else:
        accessible_farms = await Farm.find({"$or": [{"owner_email": user.email}, {"shared_with": user.email}]}).to_list()
        accessible_ids = {str(f.id) for f in accessible_farms if f.id is not None}
        if farm_id:
            if farm_id not in accessible_ids:
                return []
            query[DietCost.farm_id] = farm_id
        else:
            query[DietCost.farm_id] = {"$in": list(accessible_ids) if accessible_ids else ["__none__"]}

    items = await DietCost.find_many(query).sort("date").to_list()
    return [DietCostRead(**it.model_dump(mode="json")) for it in items]


async def get_entry(entry_id: str, user: User) -> DietCostRead:
    doc = await DietCost.get(entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    if not user.is_admin:
        farm = await Farm.get(doc.farm_id)
        if not farm or (user.email != farm.owner_email and user.email not in (farm.shared_with or [])):
            raise HTTPException(status_code=403, detail="Access denied")
    return DietCostRead(**doc.model_dump(mode="json"))


async def update_entry(entry_id: str, updates: DietCostUpdate) -> DietCostRead:
    doc = await DietCost.get(entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    data = updates.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(doc, k, v)
    await doc.save()
    return DietCostRead(**doc.model_dump(mode="json"))


async def delete_entry(entry_id: str) -> dict:
    doc = await DietCost.get(entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    await doc.delete()
    return {"msg": "Entry deleted"}
