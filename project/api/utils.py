from fastapi import HTTPException
from passlib.context import CryptContext
from hashlib import sha256
from beanie.odm.documents import Document
from typing import Optional, Any
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    if isinstance(password, str):
        pw_bytes = password.encode("utf-8")
    else:
        pw_bytes = password
    if len(pw_bytes) > 72:
        password = sha256(pw_bytes).hexdigest()
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    if isinstance(plain, str):
        pw_bytes = plain.encode("utf-8")
    else:
        pw_bytes = plain
    if len(pw_bytes) > 72:
        plain = sha256(pw_bytes).hexdigest()
    return pwd_context.verify(plain, hashed)

async def get_doc_by_id(document: type[Document], doc_id: str, error_detail: str = "Invalid entry_id format"):
    try:
        doc = await document.get(doc_id)
        return doc
    except Exception:
        raise HTTPException(status_code=400, detail=error_detail)


def build_date_range_filter(start: Optional[Any], end: Optional[Any]) -> Optional[dict]:
    if not start and not end:
        return None
    range_q: dict = {}
    if start:
        range_q["$gte"] = start
    if end:
        range_q["$lte"] = end
    return range_q if range_q else None


def apply_updates(doc: Any, updates: dict) -> None:
    for k, v in updates.items():
        setattr(doc, k, v)


async def get_accessible_farm_ids(user: Any) -> set[str]:
    """Return set of farm_id strings the user can access.
    Admin users can access all farms, returned as an empty set signaling no restriction.
    Non-admins get the set of farms owned by or shared with them.
    """
    if getattr(user, "is_admin", False):
        return set()
    # Local import to avoid heavy cross-module imports at startup time
    from project.api.models.farm import Farm  # type: ignore
    accessible_farms = await Farm.find({
        "$or": [{"owner_email": user.email}, {"shared_with": user.email}]
    }).to_list()
    return {str(f.id) for f in accessible_farms if getattr(f, "id", None) is not None}