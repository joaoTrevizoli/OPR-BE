from beanie import Document
from pydantic import Field, ConfigDict, field_serializer
from typing import Optional

class User(Document):
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User Name")
    hashed_password: str = Field(..., description="Hashed password")
    role: Optional[str] = Field(default=None, description="User role")
    apps: Optional[str] = Field(default=None, description="App identifier(s) this user can access")
    is_authorized: bool = Field(default=True, description="Is the user authorized to use the system")
    is_active: bool = Field(default=True, description="Is the user account active")
    is_admin: bool = Field(default=False, description="Is the user an administrator")
    read_only: bool = Field(default=False, description="Restrict to read-only actions")
    password_reset_token: Optional[str] = Field(default=None, description="Password reset token")
    password_reset_expires: Optional[str] = Field(default=None, description="ISO datetime when reset token expires")

    class Settings:
        name = "users"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "_id": "683d1238fded441a09bdd6e4",
                "email": "john.doe@example.com",
                "hashed_password": "$2b$12$hash...",
                "role": "manager",
                "apps": "web",
                "is_authorized": True,
                "is_active": True,
                "is_admin": False,
                "read_only": False,
            }
        }
    )

    @field_serializer("id", when_used="json")
    def serialize_id(self, v):
        return str(v) if v is not None else None
