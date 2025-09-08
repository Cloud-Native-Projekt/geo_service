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
    --mount=type=bind,source=geo_service/uv.lock,target=uv.lock \
    --mount=type=bind,source=geo_service/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY ./geo_service /app/geo_service
COPY ./geo_service/pyproject.toml /app
COPY ./geo_service/uv.lock /app 

# Sync dependencies again for final installation
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

###########################################
# PRODUCTION stage
###########################################
FROM python:3.13-slim-bookworm AS production

# Copy the application from the builder
COPY --from=builder --chown=app:app /app /app

# Production-specific env
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Set the command to run your application
CMD ["uvicorn", "geo_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
