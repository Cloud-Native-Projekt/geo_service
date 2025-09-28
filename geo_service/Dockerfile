# Default prod command (no reload)
###########################################
# BUILDER stage
###########################################
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Disable Python downloads, because we want to use the system interpreter
# across both images. If using a managed Python version, it needs to be
# copied from the build image into the final image; see `standalone.Dockerfile`
# for an example.
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Cache and sync dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY ./geo_service /app/geo_service
COPY ./pyproject.toml /app
COPY ./uv.lock /app 

# Sync dependencies again for final installation
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

###########################################
# PRODUCTION stage
###########################################
FROM python:3.13-slim-bookworm AS production

# Create app user and group
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid app --shell /bin/bash --create-home app

# Copy the application from the builder
COPY --from=builder --chown=app:app /app /app

# Create cache directories for OSMPythonTools with proper permissions
RUN mkdir -p /app/cache /home/app/.cache/OSMPythonTools && \
    chown -R app:app /app/cache /home/app/.cache

# Switch to app user
USER app

# Production-specific env
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

CMD ["uvicorn", "geo_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
