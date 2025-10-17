from functools import wraps
from fastapi import HTTPException
from fastapi import Request

from project.api.v1.authentication.authentication import get_current_user


def auth_guard(
    require_admin: bool = False,
    require_authorized: bool = True,
    require_active: bool = True,
    allowed_roles: list[str] | None = None,
    allowed_apps: list[str] | None = None,
    allow_read_only: bool = True,
):
    def decorator(view_function):
        @wraps(view_function)
        async def wrapped(request: Request, *args, **kwargs):
            user = await get_current_user(request)

            if require_active and not user.is_active:
                raise HTTPException(status_code=403, detail="User is not active")
            if require_authorized and not user.is_authorized:
                raise HTTPException(status_code=403, detail="User is not authorized")
            if require_admin and not user.is_admin:
                raise HTTPException(status_code=403, detail="Admin privileges required")
            if not allow_read_only and user.read_only:
                raise HTTPException(status_code=403, detail="Read-only users cannot perform this action")
            if allowed_roles is not None:
                if (user.role or "").lower() not in [r.lower() for r in allowed_roles]:
                    raise HTTPException(status_code=403, detail="Insufficient role")
            if allowed_apps is not None and user.apps is not None:
                user_apps = [a.strip().lower() for a in str(user.apps).split(',') if a.strip()] if user.apps else []
                allowed_apps_l = [a.lower() for a in allowed_apps]
                if not any(a in user_apps for a in allowed_apps_l):
                    raise HTTPException(status_code=403, detail="App access denied")

            return await view_function(request, *args, **kwargs)
        return wrapped
    return decorator
