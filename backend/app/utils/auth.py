from fastapi import Depends, HTTPException, status, Header
from jose import jwt, JWTError
from app.config import settings

async def get_current_user(
    authorization: str = Header(None),
    x_auth_token: str = Header(None),
) -> int:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    elif x_auth_token:
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
