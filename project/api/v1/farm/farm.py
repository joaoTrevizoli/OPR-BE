
from typing import List, Optional

from fastapi import APIRouter, Request, Body

from project.config import settings
from project.api.v1.decorators import auth_guard
from project.api.v1.authentication.controllers import get_current_user
from project.api.models.user import User
from .schemas import FarmCreate, FarmRead, FarmUpdate, ShareRequest
from . import controllers as ctrl

router = APIRouter(
    prefix=f"{settings.API_VERSION}/farm",
    tags=["farm"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=FarmRead)
@auth_guard(require_admin=False, allow_read_only=False)
async def create_farm(request: Request, payload: FarmCreate = Body(...)):
    user: User = await get_current_user(request)
    return await ctrl.create_farm(payload, owner_email=user.email)


@router.get("/", response_model=List[FarmRead])
@auth_guard(require_admin=False, allow_read_only=True)
async def list_farms(request: Request):
    user: User = await get_current_user(request)
    return await ctrl.list_farms_for_user(user_email=user.email, is_admin=bool(user.is_admin))


@router.get("/{farm_id}", response_model=FarmRead)
@auth_guard(require_admin=False, allow_read_only=True)
async def get_farm(request: Request, farm_id: str):
    user: User = await get_current_user(request)
    return await ctrl.get_farm(farm_id, user_email=user.email, is_admin=bool(user.is_admin))


@router.put("/{farm_id}", response_model=FarmRead)
@auth_guard(require_admin=False, allow_read_only=False)
async def update_farm(request: Request, farm_id: str, updates: FarmUpdate = Body(...)):
    user: User = await get_current_user(request)
    return await ctrl.update_farm(farm_id, user_email=user.email, updates=updates)


@router.delete("/{farm_id}")
@auth_guard(require_admin=False, allow_read_only=False)
async def delete_farm(request: Request, farm_id: str):
    user: User = await get_current_user(request)
    return await ctrl.delete_farm(farm_id, user_email=user.email)


@router.post("/{farm_id}/share", response_model=FarmRead)
@auth_guard(require_admin=False, allow_read_only=False)
async def share_farm(request: Request, farm_id: str, payload: ShareRequest = Body(...)):
    user: User = await get_current_user(request)
    add = payload.add or []
    remove = payload.remove or []
    return await ctrl.share_farm(farm_id, owner_email=user.email, add=add, remove=remove)
