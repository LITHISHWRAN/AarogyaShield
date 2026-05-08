from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.core.security import ALGORITHM

# tokenUrl tells OpenAPI UI where to fetch a token — must match the login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/admin/login")


async def require_admin(token: str = Depends(oauth2_scheme)) -> str:
    """FastAPI dependency that validates a Bearer token and asserts role='admin'.

    Raises 401 for missing/invalid/expired tokens.
    Raises 403 for valid tokens that lack the admin role (prevents role escalation).
    Returns the admin username on success.
    """
    invalid_token = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise invalid_token

    subject: str | None = payload.get("sub")
    role: str | None = payload.get("role")

    if subject is None:
        raise invalid_token

    # Role check is separate from signature check — a valid user JWT never carries role='admin'
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return subject
