"""Thin Redis connectivity module.

Session data management has moved to app.memory.session_store.
This module is retained for the /health/ready check (app.main imports check_redis).
"""
from __future__ import annotations

from app.memory.session_store import get_redis


async def check_redis() -> bool:
    try:
        await get_redis().ping()
        return True
    except Exception:
        return False
