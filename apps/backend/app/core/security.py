from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24   # 24 h — regular users
ADMIN_TOKEN_EXPIRE_HOURS = 8            # 8 h  — tighter window for admin sessions

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode(
        {"sub": subject, "exp": expire},
        settings.APP_SECRET_KEY,
        algorithm=ALGORITHM,
    )


def create_admin_token(username: str) -> str:
    """Issues a short-lived JWT that carries role='admin'.
    Only this function can produce a token with that claim."""
    expire = datetime.now(timezone.utc) + timedelta(hours=ADMIN_TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": username, "role": "admin", "exp": expire},
        settings.APP_SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
