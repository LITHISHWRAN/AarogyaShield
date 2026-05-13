from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_ENV: str = "development"
    APP_SECRET_KEY: str
    LOG_LEVEL: str = "INFO"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    # PostgreSQL
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str
    REDIS_SESSION_TTL: int = 86400
    REDIS_URL: str | None = None   # ← add this line

    # Qdrant
    QDRANT_HOST: str
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "policies"
    QDRANT_API_KEY: str | None = None

    @property
    def QDRANT_URL(self) -> str:
        if self.QDRANT_HOST.startswith("http"):
            return self.QDRANT_HOST
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

    # Admin credentials (hash generated via scripts/hash_password.py)
    ADMIN_USERNAME: str
    ADMIN_PASSWORD_HASH: str

    # LLM
    GOOGLE_API_KEY: str
    LLM_PROVIDER: str = "google"
    LLM_MODEL: str = "gemini-2.5-flash"
    LLM_MAX_TOKENS: int = 8192
    LLM_TEMPERATURE: float = 0.3

    # Embeddings — Google Gemini embedding-001 (768-dim)
    EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    EMBEDDING_DIMENSION: int = 3072
    # RAG
    RAG_TOP_K: int = 5   # chunks per retrieval query

    # Chat memory
    CHAT_MAX_HISTORY_TURNS: int = 20   # turns sent to LLM (full history kept in Redis)


settings = Settings()
