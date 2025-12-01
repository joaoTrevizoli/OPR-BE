from __future__ import annotations

from typing import List, Optional

from fastapi import HTTPException

from project.api.models.farm import Farm
from project.api.models.user import User
from .schemas import FarmCreate, FarmRead, FarmUpdate
from ...utils import get_doc_by_id


def _normalize_emails(emails: Optional[List[str]]) -> List[str]:
    if not emails:
        return []
    return sorted({str(e).strip().lower() for e in emails if e and str(e).strip()})


async def create_farm(payload: FarmCreate, owner_email: str) -> FarmRead:
    doc = Farm(
        name=payload.name,
        country=payload.country,
        state_province=payload.state_province,
        city=getattr(payload, "city", None),
        owner_name=getattr(payload, "owner_name", None),
        notes=payload.notes,
        lat_long=payload.lat_long,  # already coerced by schema
        owner_email=owner_email,
        shared_with=[],
    )
    await doc.insert()
    return FarmRead(**doc.model_dump(mode="json"))


async def list_farms_for_user(user_email: str, is_admin: bool = False) -> List[FarmRead]:
    # Admin sees all farms; otherwise accessible if owner or shared_with contains user
    if is_admin:
        items = await Farm.find_all().sort("name").to_list()
    else:
        items = await Farm.find(
            {"$or": [{"owner_email": user_email}, {"shared_with": user_email}]}
        ).sort("name").to_list()
    return [FarmRead(**it.model_dump(mode="json")) for it in items]


async def get_farm(entry_id: str, user_email: str, is_admin: bool = False) -> FarmRead:
    doc = await get_doc_by_id(Farm, entry_id, error_detail="Invalid farm_id format")
    if not doc:
        raise HTTPException(status_code=404, detail="Farm not found")
    if not is_admin and user_email != doc.owner_email and user_email not in (doc.shared_with or []):
        raise HTTPException(status_code=403, detail="Access denied")
    return FarmRead(**doc.model_dump(mode="json"))


async def update_farm(entry_id: str, user_email: str, updates: FarmUpdate) -> FarmRead:
    doc = await get_doc_by_id(Farm, entry_id, error_detail="Invalid farm_id format")
    if not doc:
        raise HTTPException(status_code=404, detail="Farm not found")
    if user_email != doc.owner_email:
        raise HTTPException(status_code=403, detail="Only the owner can update the farm")
    data = updates.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(doc, k, v)
    await doc.save()
    return FarmRead(**doc.model_dump(mode="json"))


from project.api.models.feed_dry_matter import FeedDryMatter
from project.api.models.manure_score import ManureScore
from project.api.models.diet_cost import DietCost


async def delete_farm(entry_id: str, user_email: str) -> dict:
    doc = await get_doc_by_id(Farm, entry_id, error_detail="Invalid farm_id format")
    if not doc:
        raise HTTPException(status_code=404, detail="Farm not found")
    if user_email != doc.owner_email:
        raise HTTPException(status_code=403, detail="Only the owner can delete the farm")

    # Cascade delete related data (best-effort): manure scores, feed dry matter, etc.
    # Use bulk delete on queries to remove all documents linked by farm_id.
    try:
        await ManureScore.find(ManureScore.farm_id == entry_id).delete()
    except Exception:
        # Ignore failures here to avoid blocking farm deletion, but you may log in real app
        pass
    try:
        await FeedDryMatter.find(FeedDryMatter.farm_id == entry_id).delete()
    except Exception:
        pass
    try:
        await DietCost.find(DietCost.farm_id == entry_id).delete()
    except Exception:
        pass
    # Legacy PennState (percentage-based) removed from the project; nothing to delete here anymore

    await doc.delete()
    return {"msg": "Farm and related data deleted"}


async def share_farm(entry_id: str, owner_email: str, add: Optional[List[str]], remove: Optional[List[str]]) -> FarmRead:
    doc = await get_doc_by_id(Farm, entry_id, error_detail="Invalid farm_id format")
    if not doc:
        raise HTTPException(status_code=404, detail="Farm not found")
    if owner_email != doc.owner_email:
        raise HTTPException(status_code=403, detail="Only the owner can share the farm")

    add_n = [e for e in _normalize_emails(add) if e != owner_email]
    remove_n = _normalize_emails(remove)

    # Validate that users exist (best-effort; ignore non-existing but do not add them)
    valid_add: List[str] = []
    for e in add_n:
        u = await User.find_one(User.email == e)
        if u:
            valid_add.append(e)

    current = set(doc.shared_with or [])
    current.update(valid_add)
    current.difference_update(set(remove_n))
    doc.shared_with = sorted(current)
    await doc.save()
    return FarmRead(**doc.model_dump(mode="json"))
