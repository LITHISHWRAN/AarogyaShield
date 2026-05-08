import structlog

logger = structlog.get_logger()


async def list_policies() -> list:
    # PostgreSQL query added in Phase 2
    logger.info("Listing policies")
    return []


async def get_policy(policy_id: str) -> dict:
    # PostgreSQL query added in Phase 2
    logger.info("Fetching policy", policy_id=policy_id)
    return {}
