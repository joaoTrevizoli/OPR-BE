from typing import List, Optional

from fastapi import APIRouter, HTTPException, Body, Request
from pydantic import BaseModel, Field, EmailStr

from project.api.models.user import User
from project.api.v1.authentication.schemas import UserRead
from project.api.v1.decorators import auth_guard
from project.api.utils import hash_password
from project.config import settings

router = APIRouter(prefix=f"{settings.API_VERSION}/admin", tags=["admin"], responses={404: {"description": "Not found"}})


class AdminUserUpdate(BaseModel):
    password: Optional[str] = Field(default=None, min_length=6)
    name: Optional[str] = None
    role: Optional[str] = None
    apps: Optional[str] = None
    is_authorized: Optional[bool] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    read_only: Optional[bool] = None
    new_email: Optional[EmailStr] = Field(default=None, description="If provided, change the user's email to this value")
    add_apps: Optional[List[str]] = Field(default=None, description="Apps to add to user's access list")
    remove_apps: Optional[List[str]] = Field(default=None, description="Apps to remove from user's access list")


def _normalize_apps(apps_str: Optional[str]) -> list:
    if not apps_str:
        return []
    return [a.strip().lower() for a in str(apps_str).split(',') if a.strip()]


def _apps_list_to_str(apps_list: list) -> str:
    return ",".join(sorted({a for a in apps_list if a}))


@router.get("/users", response_model=List[UserRead])
@auth_guard(require_admin=True, allow_read_only=False)
async def list_users(request: Request):
    users = await User.find_all().to_list()
    return [UserRead(id=str(u.id) if u.id is not None else None, email=u.email, name=u.name, role=u.role, apps=u.apps, is_authorized=u.is_authorized,
                     is_active=u.is_active, is_admin=u.is_admin, read_only=u.read_only) for u in users]


@router.get("/users/{email}", response_model=UserRead)
@auth_guard(require_admin=True, allow_read_only=False)
async def get_user(request: Request, email: EmailStr):
    user = await User.find_one(User.email == email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserRead(id=str(user.id) if user.id is not None else None, email=user.email, name=user.name, role=user.role, apps=user.apps, is_authorized=user.is_authorized,
                    is_active=user.is_active, is_admin=user.is_admin, read_only=user.read_only)


@router.put("/users/{email}", response_model=UserRead)
@auth_guard(require_admin=True, allow_read_only=False)
async def admin_update_user(request: Request, email: EmailStr, updates: AdminUserUpdate = Body(...)):
    user = await User.find_one(User.email == email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if updates.new_email and updates.new_email != user.email:
        if await User.find_one(User.email == updates.new_email):
            raise HTTPException(status_code=400, detail="New email is already registered")
        user.email = str(updates.new_email)

    if updates.name is not None:
        user.name = updates.name

    if updates.password is not None:
        user.hashed_password = hash_password(updates.password)

    if updates.role is not None:
        user.role = updates.role

    if updates.is_authorized is not None:
        user.is_authorized = updates.is_authorized
    if updates.is_active is not None:
        user.is_active = updates.is_active
    if updates.is_admin is not None:
        user.is_admin = updates.is_admin
    if updates.read_only is not None:
        user.read_only = updates.read_only

    if updates.apps is not None:
        user.apps = updates.apps
    else:
        current_apps = _normalize_apps(user.apps)
        if updates.add_apps:
            to_add = [a.strip().lower() for a in updates.add_apps if a and a.strip()]
            current_apps = list(set(current_apps).union(set(to_add)))
        if updates.remove_apps:
            to_remove = {a.strip().lower() for a in updates.remove_apps if a and a.strip()}
            current_apps = [a for a in current_apps if a not in to_remove]
        if updates.add_apps or updates.remove_apps:
            user.apps = _apps_list_to_str(current_apps)

    await user.save()
    return UserRead(id=str(user.id) if user.id is not None else None, email=user.email, name=user.name, role=user.role, apps=user.apps, is_authorized=user.is_authorized,
                    is_active=user.is_active, is_admin=user.is_admin, read_only=user.read_only)


@router.delete("/users/{email}")
@auth_guard(require_admin=True, allow_read_only=False)
async def admin_delete_user(request: Request, email: EmailStr):
    user = await User.find_one(User.email == email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await user.delete()
    return {"msg": "User deleted"}
