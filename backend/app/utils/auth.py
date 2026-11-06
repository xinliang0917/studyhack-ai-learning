from fastapi import Cookie, Depends, HTTPException, Header, status
from jose import jwt, JWTError
from app.config import settings

async def get_current_user(
    authorization: str = Header(None),
    x_auth_token: str = Header(None),
    app_token: str = Cookie(None),
) -> int:
    token = None
    if isinstance(app_token, str) and app_token:
        token = app_token
    elif isinstance(authorization, str) and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    elif isinstance(x_auth_token, str) and x_auth_token:
        token = x_auth_token
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload.get("sub", 0))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
