from __future__ import annotations

import datetime as dt
from typing import List, Optional

from fastapi import HTTPException

from project.api.models.storage_inspection import StorageInspection
from project.api.models.farm import Farm
from project.api.models.user import User
from .schemas import StorageInspectionCreate, StorageInspectionRead, StorageInspectionUpdate
from ...utils import get_doc_by_id, build_date_range_filter, apply_updates, get_accessible_farm_ids


def _compute_days_without_use(date_val: Optional[dt.date], closing: Optional[dt.date]) -> int:
    try:
        if not date_val or not closing:
            return 0
        return max(0, int((date_val - closing).days))
    except Exception:
        return 0


def _recompute(doc: StorageInspection) -> None:
    doc.time_without_use_days = _compute_days_without_use(doc.date, doc.closing_date)


async def create_entry(payload: StorageInspectionCreate) -> StorageInspectionRead:
    # Validate farm
    try:
        farm = await Farm.get(payload.farm_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid farm_id format")
    if not farm:
        raise HTTPException(status_code=400, detail="Invalid farm_id: farm not found")

    # Prevent duplicates by (farm_id, date, ingredient)
    existing = await StorageInspection.find_one({
        StorageInspection.farm_id: payload.farm_id,
        StorageInspection.date: payload.date,
        StorageInspection.ingredient: payload.ingredient,
    })
    if existing:
        raise HTTPException(status_code=409, detail="Entry already exists for this farm_id, date and ingredient")

    doc = StorageInspection(**payload.model_dump())
    _recompute(doc)
    try:
        await doc.insert()
    except Exception as e:
        if e.__class__.__name__ == "DuplicateKeyError":
            raise HTTPException(status_code=409, detail="Entry already exists for this farm_id, date and ingredient")
        raise
    return StorageInspectionRead(**doc.model_dump(mode="json"))


async def list_entries(
    user: User,
    unit: Optional[str] = None,
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
    farm_id: Optional[str] = None,
    ingredient: Optional[str] = None,
) -> List[StorageInspectionRead]:
    query: dict = {}
    if unit:
        query[StorageInspection.unit] = unit
    if ingredient:
        query[StorageInspection.ingredient] = ingredient
    range_q = build_date_range_filter(start_date, end_date)
    if range_q:
        query[StorageInspection.date] = range_q

    if user.is_admin:
        if farm_id:
            query[StorageInspection.farm_id] = farm_id
    else:
        accessible_ids = await get_accessible_farm_ids(user)
        if farm_id:
            if farm_id not in accessible_ids:
                return []
            query[StorageInspection.farm_id] = farm_id
        else:
            query[StorageInspection.farm_id] = {"$in": list(accessible_ids) if accessible_ids else ["__none__"]}

    items = await StorageInspection.find_many(query).sort("date").to_list()
    return [StorageInspectionRead(**it.model_dump(mode="json")) for it in items]


async def get_entry(entry_id: str, user: User) -> StorageInspectionRead:
    doc = await get_doc_by_id(StorageInspection, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    if not user.is_admin:
        farm = await Farm.get(doc.farm_id)
        if not farm or (user.email != farm.owner_email and user.email not in (farm.shared_with or [])):
            raise HTTPException(status_code=403, detail="Access denied")
    return StorageInspectionRead(**doc.model_dump(mode="json"))


async def update_entry(entry_id: str, updates: StorageInspectionUpdate) -> StorageInspectionRead:
    doc = await get_doc_by_id(StorageInspection, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    data = updates.model_dump(exclude_unset=True)
    apply_updates(doc, data)
    _recompute(doc)

    # Ensure uniqueness remains for (farm_id, date, ingredient)
    conflict = await StorageInspection.find_one({
        StorageInspection.farm_id: doc.farm_id,
        StorageInspection.date: doc.date,
        StorageInspection.ingredient: doc.ingredient,
        "_id": {"$ne": doc.id},
    })
    if conflict:
        raise HTTPException(status_code=409, detail="Another entry already exists for this farm_id, date and ingredient")

    try:
        await doc.save()
    except Exception as e:
        if e.__class__.__name__ == "DuplicateKeyError":
            raise HTTPException(status_code=409, detail="Another entry already exists for this farm_id, date and ingredient")
        raise
    return StorageInspectionRead(**doc.model_dump(mode="json"))


async def delete_entry(entry_id: str) -> dict:
    doc = await get_doc_by_id(StorageInspection, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    await doc.delete()
    return {"msg": "Entry deleted"}
