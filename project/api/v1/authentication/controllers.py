from typing import Optional
from datetime import datetime, timedelta

from fastapi import HTTPException, Body, Depends, Request
from jose import jwt, JWTError

from project.api.models.user import User
from project.api.utils import hash_password, verify_password
from project.config import settings
from .schemas import (
    UserCreate,
    UserRead,
    UserUpdate,
    LoginRequest,
    TokenResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from .utils import create_access_token, create_refresh_token, reset_email_html


async def get_current_user(request: Request) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        user = await User.find_one(User.email == sub)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Inactive user")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def create_user(payload: UserCreate):
    if await User.find_one(User.email == payload.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=payload.email,
        name=payload.name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        apps=payload.apps,
        is_authorized=payload.is_authorized,
        is_active=payload.is_active,
        is_admin=payload.is_admin,
        read_only=payload.read_only,
    )
    await user.insert()
    return UserRead(
        id=str(user.id) if user.id is not None else None,
        email=user.email,
        name=user.name,
        role=user.role,
        apps=user.apps,
        is_authorized=user.is_authorized,
        is_active=user.is_active,
        is_admin=user.is_admin,
        read_only=user.read_only,
    )


async def login(payload: LoginRequest):
    user = await User.find_one(User.email == payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active or not user.is_authorized:
        raise HTTPException(status_code=403, detail="User is not authorized or inactive")
    claims = {
        "sub": user.email,
        "email": user.email,
        "role": user.role,
        "name": user.name,
        "apps": user.apps,
        "is_authorized": user.is_authorized,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "read_only": user.read_only,
    }
    access_token = create_access_token(claims)
    refresh_token = create_refresh_token(claims)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


async def refresh_token(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        email = payload.get("sub")
        user = await User.find_one(User.email == email)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Inactive user")
        claims = {
            "sub": user.email,
            "email": user.email,
            "role": user.role,
            "name": user.name,
            "apps": user.apps,
            "is_authorized": user.is_authorized,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "read_only": user.read_only,
        }
        access_token = create_access_token(claims)
        new_refresh_token = create_refresh_token(claims)
        return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


async def request_password_reset(payload: PasswordResetRequest):
    user = await User.find_one(User.email == payload.email)
    if not user:
        return {"message": "If the email exists, a reset link has been sent."}
    expires_minutes = settings.PASSWORD_RESET_EXPIRE_MINUTES
    expire_dt = datetime.utcnow() + timedelta(minutes=expires_minutes)
    token = jwt.encode({"sub": user.email, "type": "password_reset", "exp": expire_dt}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    user.password_reset_token = token
    user.password_reset_expires = expire_dt.isoformat()
    await user.save()

    reset_link = f"{settings.PASSWORD_RESET_URL}?token={token}"

    if settings.BREVO_API_KEY:
        try:
            import requests
            payload = {
                "sender": {"email": settings.BREVO_FROM_EMAIL, "name": "VITALIA"},
                "to": [{"email": user.email, "name": user.name or user.email}],
                "subject": "Reset your VITALIA password",
                "htmlContent": reset_email_html(reset_link, user.name),
            }
            headers = {
                "accept": "application/json",
                "api-key": settings.BREVO_API_KEY,
                "content-type": "application/json",
            }
            resp = requests.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers, timeout=10)
            print(resp)
            if resp.status_code >= 300:
                print(f"Brevo error: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"Brevo error: {e}")
    else:
        print(f"Password reset link for {user.email}: {reset_link}")

    return {"message": "If the email exists, a reset link has been sent."}


async def reset_password(payload: PasswordResetConfirm):
    try:
        data = jwt.decode(payload.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if data.get("type") != "password_reset":
            raise HTTPException(status_code=400, detail="Invalid token type")
        email = data.get("sub")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = await User.find_one(User.email == email)
    if not user or not user.password_reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    if user.password_reset_token != payload.token:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    try:
        stored_exp = datetime.fromisoformat(user.password_reset_expires) if user.password_reset_expires else None
    except Exception:
        stored_exp = None
    if stored_exp and datetime.utcnow() > stored_exp:
        raise HTTPException(status_code=400, detail="Token has expired")

    user.hashed_password = hash_password(payload.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    await user.save()

    return {"message": "Password has been reset successfully."}


async def update_user(email: str, updates: UserUpdate, current_user: User):

    db_user = await User.find_one(User.email == email)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if updates.name is not None:
        db_user.name = updates.name

    if updates.password is not None:
        db_user.hashed_password = hash_password(updates.password)
    if updates.role is not None:
        db_user.role = updates.role
    if updates.apps is not None:
        db_user.apps = updates.apps
    if updates.is_authorized is not None:
        db_user.is_authorized = updates.is_authorized
    if updates.is_active is not None:
        db_user.is_active = updates.is_active
    if updates.is_admin is not None:
        db_user.is_admin = updates.is_admin
    if updates.read_only is not None:
        db_user.read_only = updates.read_only

    await db_user.save()
    return UserRead(
        id=db_user.id,
        email=db_user.email,
        name=db_user.name,
        role=db_user.role,
        apps=db_user.apps,
        is_authorized=db_user.is_authorized,
        is_active=db_user.is_active,
        is_admin=db_user.is_admin,
        read_only=db_user.read_only,
    )


async def delete_user(
    email: Optional[str] = None,
    password: Optional[str] = None,
    current_user: User = None,
):
    target_email = email or current_user.email

    if target_email != current_user.email:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin privileges required")
    else:
        if not password:
            raise HTTPException(status_code=400, detail="Password is required to delete your own account")
        if not verify_password(password, current_user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

    db_user = await User.find_one(User.email == target_email)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    await db_user.delete()
    return {"msg": "User deleted"}
