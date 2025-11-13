from __future__ import annotations

import datetime as dt
from typing import List, Optional

from fastapi import HTTPException

from project.api.models.factory import Factory
from project.api.models.farm import Farm
from project.api.models.user import User
from .schemas import FactoryCreate, FactoryRead, FactoryUpdate
from ...utils import get_doc_by_id, build_date_range_filter, apply_updates, get_accessible_farm_ids


def _sum3(a: Optional[int], b: Optional[int], c: Optional[int]) -> int:
    return int(a or 0) + int(b or 0) + int(c or 0)


def _recompute(doc: Factory) -> None:
    # Manufacturing totals and deviation
    man_total = _sum3(doc.manufacturing_adaptation, doc.manufacturing_growth, doc.manufacturing_termination)
    doc.manufacturing_day_total = man_total
    try:
        if doc.planned_manufacturing_total and float(doc.planned_manufacturing_total) != 0:
            doc.loading_deviation_pct = 100.0 * ((float(man_total) / float(doc.planned_manufacturing_total)) - 1.0)
        else:
            doc.loading_deviation_pct = 0.0
    except Exception:
        doc.loading_deviation_pct = 0.0

    # Supply totals and ratios
    sup_total = _sum3(doc.supply_adaptation, doc.supply_growth, doc.supply_termination)
    doc.supply_day_total = sup_total

    def pct_ratio(num: Optional[int], den: Optional[int]) -> float:
        try:
            n = float(num or 0)
            d = float(den or 0)
            if d == 0:
                return 0.0
            return 100.0 * (n / d)
        except Exception:
            return 0.0

    doc.adaptation_ratio_pct = pct_ratio(doc.supply_adaptation, doc.manufacturing_adaptation)
    doc.growth_ratio_pct = pct_ratio(doc.supply_growth, doc.manufacturing_growth)
    doc.termination_ratio_pct = pct_ratio(doc.supply_termination, doc.manufacturing_termination)
    doc.day_ratio_pct = pct_ratio(sup_total, man_total)

    # Supply deviation
    try:
        if doc.planned_supply_total and float(sup_total) != 0:
            doc.supply_deviation_pct = 100.0 * ((float(doc.planned_supply_total) / float(sup_total)) - 1.0)
        else:
            doc.supply_deviation_pct = 0.0
    except Exception:
        doc.supply_deviation_pct = 0.0


async def create_entry(payload: FactoryCreate) -> FactoryRead:
    # Validate farm
    try:
        farm = await Farm.get(payload.farm_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid farm_id format")
    if not farm:
        raise HTTPException(status_code=400, detail="Invalid farm_id: farm not found")

    # Prevent duplicates by (farm_id, date)
    existing = await Factory.find_one({
        Factory.farm_id: payload.farm_id,
        Factory.date: payload.date,
    })
    if existing:
        raise HTTPException(status_code=409, detail="Entry already exists for this farm_id and date")

    doc = Factory(**payload.model_dump())
    _recompute(doc)
    try:
        await doc.insert()
    except Exception as e:
        if e.__class__.__name__ == "DuplicateKeyError":
            raise HTTPException(status_code=409, detail="Entry already exists for this farm_id and date")
        raise
    return FactoryRead(**doc.model_dump(mode="json"))


async def list_entries(
    user: User,
    unit: Optional[str] = None,
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
    farm_id: Optional[str] = None,
) -> List[FactoryRead]:
    query: dict = {}
    if unit:
        query[Factory.unit] = unit
    range_q = build_date_range_filter(start_date, end_date)
    if range_q:
        query[Factory.date] = range_q

    if user.is_admin:
        if farm_id:
            query[Factory.farm_id] = farm_id
    else:
        accessible_ids = await get_accessible_farm_ids(user)
        if farm_id:
            if farm_id not in accessible_ids:
                return []
            query[Factory.farm_id] = farm_id
        else:
            query[Factory.farm_id] = {"$in": list(accessible_ids) if accessible_ids else ["__none__"]}

    items = await Factory.find_many(query).sort("date").to_list()
    return [FactoryRead(**it.model_dump(mode="json")) for it in items]


async def get_entry(entry_id: str, user: User) -> FactoryRead:
    doc = await get_doc_by_id(Factory, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    if not user.is_admin:
        farm = await Farm.get(doc.farm_id)
        if not farm or (user.email != farm.owner_email and user.email not in (farm.shared_with or [])):
            raise HTTPException(status_code=403, detail="Access denied")
    return FactoryRead(**doc.model_dump(mode="json"))


async def update_entry(entry_id: str, updates: FactoryUpdate) -> FactoryRead:
    doc = await get_doc_by_id(Factory, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    data = updates.model_dump(exclude_unset=True)
    apply_updates(doc, data)
    _recompute(doc)

    conflict = await Factory.find_one({
        Factory.farm_id: doc.farm_id,
        Factory.date: doc.date,
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
    return FactoryRead(**doc.model_dump(mode="json"))


async def delete_entry(entry_id: str) -> dict:
    doc = await get_doc_by_id(Factory, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    await doc.delete()
    return {"msg": "Entry deleted"}
