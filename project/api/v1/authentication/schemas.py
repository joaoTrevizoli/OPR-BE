from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: Optional[str] = None
    role: Optional[str] = None
    apps: Optional[str] = None
    is_authorized: bool = True
    is_active: bool = True
    is_admin: bool = False
    read_only: bool = False


class UserRead(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    email: EmailStr
    name: Optional[str] = None
    role: Optional[str] = None
    apps: Optional[str] = None
    is_authorized: bool
    is_active: bool
    is_admin: bool
    read_only: bool

    class Config:
        from_attributes = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "id": "683d1238fded441a09bdd6e4",
                "email": "user@example.com",
                "name": "Jane Doe",
                "role": "user",
                "apps": "dashboard,analytics",
                "is_authorized": True,
                "is_active": True,
                "is_admin": False,
                "read_only": False,
            }
        }


class UserUpdate(BaseModel):
    password: Optional[str] = Field(default=None, min_length=6)
    name: Optional[str] = None
    role: Optional[str] = None
    apps: Optional[str] = None
    is_authorized: Optional[bool] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    read_only: Optional[bool] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=6)
