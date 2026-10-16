FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY apps/api/ ./
RUN pip install ".[postgres]"

# The from-scratch Vortex GPT (vortex/ package). Checkpoints are mounted at runtime.
ARG INSTALL_NATIVE=true
RUN if [ "$INSTALL_NATIVE" = "true" ]; then \
      pip install torch --index-url https://download.pytorch.org/whl/cpu; \
    fi
COPY vortex/ /app/native/vortex/

COPY models/ /app/models/

RUN useradd --create-home --uid 1000 vortex \
    && mkdir -p /app/data \
    && chown -R vortex:vortex /app/data
USER vortex

ENV VORTEX_REGISTRY_PATH=/app/models/registry.yaml \
    VORTEX_DATABASE_URL=sqlite+aiosqlite:////app/data/vortex.db \
    VORTEX_NATIVE_PATH=/app/native \
    VORTEX_NATIVE_CHECKPOINTS=/app/native/checkpoints

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn vortex_api.main:create_app --factory --host 0.0.0.0 --port 8000 --proxy-headers"]
