from fastapi import APIRouter, Body, Depends
from project.config import settings
from project.api.models.user import User
from .schemas import (
    UserCreate,
    UserRead,
    UserUpdate,
    LoginRequest,
    TokenResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from . import controllers as auth_ctrl

router = APIRouter(
    prefix=f"{settings.API_VERSION}/authentication",
    tags=["authentication"],
    responses={404: {"description": "Not found"}},
)

@router.post("/create_user", response_model=UserRead)
async def create_user(payload: UserCreate):
    return await auth_ctrl.create_user(payload)

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    return await auth_ctrl.login(payload)

@router.post("/refresh_token", response_model=TokenResponse)
async def refresh_token(refresh_token: str = Body(...)):
    return await auth_ctrl.refresh_token(refresh_token)

@router.post("/request_password_reset")
async def request_password_reset(payload: PasswordResetRequest):
    return await auth_ctrl.request_password_reset(payload)

@router.post("/reset_password")
async def reset_password(payload: PasswordResetConfirm):
    return await auth_ctrl.reset_password(payload)

@router.put("/update_user", response_model=UserRead)
async def update_user(email: str = Body(...), updates: UserUpdate = Body(...), current_user: User = Depends(auth_ctrl.get_current_user)):
    return await auth_ctrl.update_user(email, updates, current_user)

@router.delete("/delete_user")
async def delete_user(
    email: str | None = Body(default=None),
    password: str | None = Body(default=None),
    current_user: User = Depends(auth_ctrl.get_current_user),
):
    return await auth_ctrl.delete_user(email, password, current_user)

# Re-export for decorators compatibility
get_current_user = auth_ctrl.get_current_user
