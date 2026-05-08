import structlog

from app.core.security import hash_password, create_access_token

logger = structlog.get_logger()


async def register_user(email: str, password: str, full_name: str) -> dict:
    # Persisted to PostgreSQL in Phase 2
    logger.info("Registering user", email=email)
    hashed = hash_password(password)
    return {"email": email, "full_name": full_name, "hashed_password": hashed}


async def authenticate_user(email: str, password: str) -> str:
    # DB lookup + verify added in Phase 2
    logger.info("Authenticating user", email=email)
    return create_access_token(subject=email)
