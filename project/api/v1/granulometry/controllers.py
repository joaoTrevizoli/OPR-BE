from __future__ import annotations

import datetime as dt
from typing import List, Optional

from fastapi import HTTPException

from project.api.models.granulometry import Granulometry
from project.api.models.farm import Farm
from project.api.models.user import User
from .schemas import GranulometryCreate, GranulometryRead, GranulometryUpdate
from ...utils import get_doc_by_id, build_date_range_filter, apply_updates, get_accessible_farm_ids


def _sum5(a: Optional[int], b: Optional[int], c: Optional[int], d: Optional[int], e: Optional[int]) -> int:
    return int(a or 0) + int(b or 0) + int(c or 0) + int(d or 0) + int(e or 0)


def _pct(part: Optional[int], total: int) -> float:
    try:
        p = float(part or 0)
        t = float(total or 0)
        if t == 0:
            return 0.0
        return 100.0 * (p / t)
    except Exception:
        return 0.0


def _granulometry(p6: float, p3_25: float, p2: float, p1_25: float, p0: float) -> float:
    f6 = p6 / 100.0
    f3 = p3_25 / 100.0
    f2 = p2 / 100.0
    f1 = p1_25 / 100.0
    f0 = p0 / 100.0
    return (
        f6 * 6.0
        + f3 * ((6.0 + 3.25) / 2.0)
        + f2 * ((3.25 + 2.0) / 2.0)
        + f1 * ((2.0 + 1.25) / 2.0)
        + f0 * ((1.25 + 0.0) / 2.0)
    )


def _recompute(doc: Granulometry) -> None:
    total = _sum5(doc.count_6mm, doc.count_3_25mm, doc.count_2mm, doc.count_1_25mm, doc.count_bottom)
    doc.total_count = total
    doc.pct_6mm = _pct(doc.count_6mm, total)
    doc.pct_3_25mm = _pct(doc.count_3_25mm, total)
    doc.pct_2mm = _pct(doc.count_2mm, total)
    doc.pct_1_25mm = _pct(doc.count_1_25mm, total)
    doc.pct_bottom = _pct(doc.count_bottom, total)
    doc.granulometry_mm = _granulometry(doc.pct_6mm, doc.pct_3_25mm, doc.pct_2mm, doc.pct_1_25mm, doc.pct_bottom)


async def create_entry(payload: GranulometryCreate) -> GranulometryRead:
    # Validate farm
    try:
        farm = await Farm.get(payload.farm_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid farm_id format")
    if not farm:
        raise HTTPException(status_code=400, detail="Invalid farm_id: farm not found")

    # Prevent duplicates by (farm_id, date, sample)
    existing = await Granulometry.find_one({
        Granulometry.farm_id: payload.farm_id,
        Granulometry.date: payload.date,
        Granulometry.sample: payload.sample,
    })
    if existing:
        raise HTTPException(status_code=409, detail="Entry already exists for this farm_id, date and sample")

    doc = Granulometry(**payload.model_dump())
    _recompute(doc)
    try:
        await doc.insert()
    except Exception as e:
        if e.__class__.__name__ == "DuplicateKeyError":
            raise HTTPException(status_code=409, detail="Entry already exists for this farm_id, date and sample")
        raise
    return GranulometryRead(**doc.model_dump(mode="json"))


async def list_entries(
    user: User,
    unit: Optional[str] = None,
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
    farm_id: Optional[str] = None,
    sample: Optional[str] = None,
) -> List[GranulometryRead]:
    query: dict = {}
    if unit:
        query[Granulometry.unit] = unit
    if sample:
        query[Granulometry.sample] = sample
    range_q = build_date_range_filter(start_date, end_date)
    if range_q:
        query[Granulometry.date] = range_q

    if user.is_admin:
        if farm_id:
            query[Granulometry.farm_id] = farm_id
    else:
        accessible_ids = await get_accessible_farm_ids(user)
        if farm_id:
            if farm_id not in accessible_ids:
                return []
            query[Granulometry.farm_id] = farm_id
        else:
            query[Granulometry.farm_id] = {"$in": list(accessible_ids) if accessible_ids else ["__none__"]}

    items = await Granulometry.find_many(query).sort("date").to_list()
    return [GranulometryRead(**it.model_dump(mode="json")) for it in items]


async def get_entry(entry_id: str, user: User) -> GranulometryRead:
    doc = await get_doc_by_id(Granulometry, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    if not user.is_admin:
        farm = await Farm.get(doc.farm_id)
        if not farm or (user.email != farm.owner_email and user.email not in (farm.shared_with or [])):
            raise HTTPException(status_code=403, detail="Access denied")
    return GranulometryRead(**doc.model_dump(mode="json"))


async def update_entry(entry_id: str, updates: GranulometryUpdate) -> GranulometryRead:
    doc = await get_doc_by_id(Granulometry, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    data = updates.model_dump(exclude_unset=True)
    apply_updates(doc, data)
    _recompute(doc)

    # Ensure uniqueness remains
    conflict = await Granulometry.find_one({
        Granulometry.farm_id: doc.farm_id,
        Granulometry.date: doc.date,
        Granulometry.sample: doc.sample,
        "_id": {"$ne": doc.id},
    })
    if conflict:
        raise HTTPException(status_code=409, detail="Another entry already exists for this farm_id, date and sample")

    try:
        await doc.save()
    except Exception as e:
        if e.__class__.__name__ == "DuplicateKeyError":
            raise HTTPException(status_code=409, detail="Another entry already exists for this farm_id, date and sample")
        raise
    return GranulometryRead(**doc.model_dump(mode="json"))


async def delete_entry(entry_id: str) -> dict:
    doc = await get_doc_by_id(Granulometry, entry_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    await doc.delete()
    return {"msg": "Entry deleted"}
