from fastapi import Cookie, Header, HTTPException, Query
from jose import jwt, JWTError
from app.config import settings

async def get_current_user(
    access_token: str = Query(None),
    authorization: str = Header(None),
    x_auth_token: str = Header(None),
    app_token: str = Cookie(None),
) -> int:
    candidates = []
    if isinstance(access_token, str) and access_token:
        candidates.append(access_token)
    if isinstance(authorization, str) and authorization.startswith("Bearer "):
        candidates.append(authorization.split(" ", 1)[1])
    if isinstance(x_auth_token, str) and x_auth_token:
        candidates.append(x_auth_token)
    if isinstance(app_token, str) and app_token:
        candidates.append(app_token)

    if not candidates:
        raise HTTPException(status_code=401, detail="Not authenticated")

    for token in candidates:
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
            user_id = int(payload.get("sub", 0))
            if user_id:
                return user_id
        except (JWTError, TypeError, ValueError):
            continue
    raise HTTPException(status_code=401, detail="Invalid token")
