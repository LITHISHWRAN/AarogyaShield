# ── Stage 1: Base ─────────────────────────────────────────────────────────────
# Shared foundation for both dev and prod targets.
# Installs system deps and Python packages once — subsequent stages inherit
# without re-running apt-get or pip.
FROM python:3.11-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        # Required to compile psycopg2 and other C extensions
        build-essential \
        libpq-dev \
        # pg_isready — used in start.sh to wait for PostgreSQL
        postgresql-client \
        # curl — used by healthcheck
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ── Stage 2: Development ──────────────────────────────────────────────────────
# Thin target used by docker-compose.yml (default).
# Source code is bind-mounted at runtime — no COPY needed.
# The Hugging Face model cache is a named Docker volume so the model
# is downloaded once and reused across container rebuilds.
FROM base AS development

EXPOSE 8000

# Uvicorn with --reload for hot-reload in development
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--reload", "--reload-dir", "/app"]


# ── Stage 3: Production ───────────────────────────────────────────────────────
# Self-contained image — no bind mounts, non-root user, model pre-downloaded.
FROM base AS production

# Create a non-root system user.
# Running as root in a container is unnecessary and increases attack surface.
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

# Copy application code and set ownership in one layer
COPY --chown=appuser:appuser . .

# Make startup script executable before switching users
RUN chmod +x scripts/start.sh

# Switch to non-root for model download and all subsequent layers
USER appuser

# Pre-download the sentence-transformers model.
# Baking the model into the image eliminates the 2-minute cold-start delay
# on first request. HF_HOME is scoped to /app/.cache so the appuser owns it.
ENV HF_HOME=/app/.cache/huggingface
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

# start.sh waits for PostgreSQL, then starts uvicorn
CMD ["./scripts/start.sh"]
