from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from jose import jwt

from project.config import settings


def _create_token(claims: Dict[str, Any], expires_delta: timedelta, token_type: str) -> str:
    payload = {
        **claims,
        "type": token_type,
        "exp": datetime.utcnow() + expires_delta,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(claims: Dict[str, Any], minutes: Optional[int] = None) -> str:
    expire_minutes = minutes if minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    return _create_token(claims, timedelta(minutes=expire_minutes), token_type="access")


def create_refresh_token(claims: Dict[str, Any], days: Optional[int] = None) -> str:
    expire_days = days if days is not None else settings.REFRESH_TOKEN_EXPIRE_DAYS
    return _create_token(claims, timedelta(days=expire_days), token_type="refresh")


def reset_email_html(reset_link: str, user_name: str | None = None) -> str:
    display_name = user_name or ""
    return f"""
    <div style='font-family:Arial,Helvetica,sans-serif;background:#f5f7f2;padding:24px;'>
      <div style='max-width:560px;margin:0 auto;background:#ffffff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.06);padding:32px;text-align:center;'>
        <h1 style='color:#f36f21;margin:0 0 8px;font-size:28px;'>Integritas VITALIA</h1>
        <p style='color:#7a8a8e;margin:0 0 24px;'>by Phibro Animal Health</p>
        <p style='color:#333;margin:0 0 16px;'>Hello {display_name},</p>
        <p style='color:#333;margin:0 0 24px;'>We received a request to reset your password. Click the button below to create a new password.</p>
        <a href='{reset_link}' style='display:inline-block;background:#66a63a;color:#fff;text-decoration:none;padding:12px 24px;border-radius:6px;font-weight:bold;'>Reset Password</a>
        <p style='color:#7a8a8e;margin:24px 0 0;font-size:12px;'>If you did not request this, you can safely ignore this email.</p>
      </div>
    </div>
    """
