from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import HTTPException

from project.api.models.feed_dry_matter import FeedDryMatter
from project.api.models.farm import Farm
from project.api.models.user import User
from .schemas import FeedDryMatterCreate, FeedDryMatterRead, FeedDryMatterUpdate


async def create_entry(payload: FeedDryMatterCreate) -> FeedDryMatterRead:
    # Validate that the referenced farm exists with graceful handling of invalid IDs
    try:
        farm = await Farm.get(payload.farm_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid farm_id format")
    if not farm:
        raise HTTPException(status_code=400, detail="Invalid farm_id: farm not found")
    doc = FeedDryMatter(**payload.dict())
    await doc.insert()
    return FeedDryMatterRead(**doc.model_dump(mode="json"))


async def list_entries(user: User, unit: Optional[str] = None, start_date: Optional[date] = None, end_date: Optional[date] = None, farm_id: Optional[str] = None) -> List[FeedDryMatterRead]:
    query = {}
    if unit:
        query[FeedDryMatter.unit] = unit
    # Date range filter
    if start_date or end_date:
        range_q = {}
        if start_date:
            range_q["$gte"] = start_date
        if end_date:
            range_q["$lte"] = end_date
        query[FeedDryMatter.date] = range_q

    if user.is_admin:
        # Admin can see all; apply farm_id filter if provided
        if farm_id:
            query[FeedDryMatter.farm_id] = farm_id
    else:
        # Restrict to farms the user owns or is shared with
        accessible_farms = await Farm.find({"$or": [{"owner_email": user.email}, {"shared_with": user.email}]}).to_list()
        accessible_ids = {str(f.id) for f in accessible_farms if f.id is not None}
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
    doc = await FeedDryMatter.get(entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    if not user.is_admin:
        farm = await Farm.get(doc.farm_id)
        if not farm or (user.email != farm.owner_email and user.email not in (farm.shared_with or [])):
            raise HTTPException(status_code=403, detail="Access denied")
    return FeedDryMatterRead(**doc.model_dump(mode="json"))


async def update_entry(entry_id: str, updates: FeedDryMatterUpdate) -> FeedDryMatterRead:
    doc = await FeedDryMatter.get(entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    data = updates.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(doc, k, v)
    await doc.save()
    return FeedDryMatterRead(**doc.model_dump(mode="json"))


async def delete_entry(entry_id: str) -> dict:
    doc = await FeedDryMatter.get(entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    await doc.delete()
    return {"msg": "Entry deleted"}
