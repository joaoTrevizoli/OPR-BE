from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Query, Body, Request

from project.config import settings
from project.api.v1.decorators import auth_guard
from project.api.v1.authentication.controllers import get_current_user
from project.api.models.user import User
from .schemas import (
    PennStateDietCreate,
    PennStateDietRead,
    PennStateDietUpdate,
)
from . import controllers as ctrl

router = APIRouter(
    prefix=f"{settings.API_VERSION}/penn-state-diet",
    tags=["penn-state-diet"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=PennStateDietRead)
@auth_guard(require_admin=False, allow_read_only=False)
async def create_ps_diet(request: Request, payload: PennStateDietCreate = Body(...)):
    return await ctrl.create_entry(payload)


@router.get("/", response_model=List[PennStateDietRead])
@auth_guard(require_admin=False, allow_read_only=True)
async def list_ps_diet(
    request: Request,
    unit: Optional[str] = Query(default=None),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    farm_id: Optional[str] = Query(default=None),
    diet: Optional[str] = Query(default=None),
):
    user: User = await get_current_user(request)
    return await ctrl.list_entries(user=user, unit=unit, start_date=start_date, end_date=end_date, farm_id=farm_id, diet=diet)


@router.get("/{entry_id}", response_model=PennStateDietRead)
@auth_guard(require_admin=False, allow_read_only=True)
async def get_ps_diet(request: Request, entry_id: str):
    user: User = await get_current_user(request)
    return await ctrl.get_entry(entry_id, user=user)


@router.put("/{entry_id}", response_model=PennStateDietRead)
@auth_guard(require_admin=False, allow_read_only=False)
async def update_ps_diet(request: Request, entry_id: str, updates: PennStateDietUpdate = Body(...)):
    return await ctrl.update_entry(entry_id, updates)


@router.delete("/{entry_id}")
@auth_guard(require_admin=False, allow_read_only=False)
async def delete_ps_diet(request: Request, entry_id: str):
    return await ctrl.delete_entry(entry_id)
