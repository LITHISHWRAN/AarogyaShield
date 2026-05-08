import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.security import create_admin_token, verify_password
from app.modules.auth.schemas import TokenResponse

logger = structlog.get_logger()

router = APIRouter()


@router.post("/login", response_model=TokenResponse, tags=["admin"])
async def admin_login(form: OAuth2PasswordRequestForm = Depends()):
    """Admin credential endpoint.

    Both username mismatch and password mismatch return the identical 401 response —
    prevents username enumeration. bcrypt.verify handles constant-time comparison.
    """
    username_ok = form.username == settings.ADMIN_USERNAME
    password_ok = verify_password(form.password, settings.ADMIN_PASSWORD_HASH)

    if not username_ok or not password_ok:
        logger.warning("Admin login failed", username=form.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_admin_token(form.username)
    logger.info("Admin login successful", username=form.username)
    return TokenResponse(access_token=token)
