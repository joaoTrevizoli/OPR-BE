from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import HTTPException

from project.api.models.feed_dry_matter import FeedDryMatter
from project.api.models.farm import Farm
from project.api.models.user import User
from .schemas import FeedDryMatterCreate, FeedDryMatterRead, FeedDryMatterUpdate
from ...utils import get_doc_by_id, build_date_range_filter, apply_updates, get_accessible_farm_ids


async def create_entry(payload: FeedDryMatterCreate) -> FeedDryMatterRead:
    # Validate that the referenced farm exists with graceful handling of invalid IDs
    try:
        farm = await Farm.get(payload.farm_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid farm_id format")
    if not farm:
        raise HTTPException(status_code=400, detail="Invalid farm_id: farm not found")
    # Prevent duplicate by (farm_id, date)
    existing = await FeedDryMatter.find_one({
        FeedDryMatter.farm_id: payload.farm_id,
        FeedDryMatter.date: payload.date,
    })
    if existing:
        raise HTTPException(status_code=409, detail="Entry already exists for this farm_id and date")

    doc = FeedDryMatter(**payload.dict())
    try:
        await doc.insert()
    except Exception as e:
        if e.__class__.__name__ == "DuplicateKeyError":
            raise HTTPException(status_code=409, detail="Entry already exists for this farm_id and date")
        raise
    return FeedDryMatterRead(**doc.model_dump(mode="json"))


async def list_entries(user: User, unit: Optional[str] = None, start_date: Optional[date] = None, end_date: Optional[date] = None, farm_id: Optional[str] = None) -> List[FeedDryMatterRead]:
    query = {}
    if unit:
        query[FeedDryMatter.unit] = unit
    # Date range filter
    range_q = build_date_range_filter(start_date, end_date)
    if range_q:
        query[FeedDryMatter.date] = range_q

    if user.is_admin:
        # Admin can see all; apply farm_id filter if provided
        if farm_id:
            query[FeedDryMatter.farm_id] = farm_id
    else:
        # Restrict to farms the user owns or is shared with
        accessible_ids = await get_accessible_farm_ids(user)
        if farm_id:
            # Intersect requested farm with accessible set
            if farm_id not in accessible_ids:
                return []
            query[FeedDryMatter.farm_id] = farm_id
        else:
            query[FeedDryMatter.farm_id] = {"$in": list(accessible_ids) if accessible_ids else ["__none__"]}

    items = await FeedDryMatter.find_many(query).sort("date").to_list()
    return [FeedDryMatterRead(**it.model_dump(mode="json")) for it in items]


async def get_entry(entry_id: str, user: User) -> FeedDryMatterRead:
    doc = await get_doc_by_id(FeedDryMatter, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    if not user.is_admin:
        farm = await Farm.get(doc.farm_id)
        if not farm or (user.email != farm.owner_email and user.email not in (farm.shared_with or [])):
            raise HTTPException(status_code=403, detail="Access denied")
    return FeedDryMatterRead(**doc.model_dump(mode="json"))


async def update_entry(entry_id: str, updates: FeedDryMatterUpdate) -> FeedDryMatterRead:
    doc = await get_doc_by_id(FeedDryMatter, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    data = updates.model_dump(exclude_unset=True)
    apply_updates(doc, data)

    # Check for uniqueness conflict with updated keys (farm_id, date)
    conflict = await FeedDryMatter.find_one({
        FeedDryMatter.farm_id: doc.farm_id,
        FeedDryMatter.date: doc.date,
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
    return FeedDryMatterRead(**doc.model_dump(mode="json"))


async def delete_entry(entry_id: str) -> dict:
    doc = await get_doc_by_id(FeedDryMatter, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    await doc.delete()
    return {"msg": "Entry deleted"}
