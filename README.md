# geo-service-app

Repository for all components of the geo app.
Service for reviewing infrastructure such as power lines and land use (forests, buildings, existing wind/solar power plants, etc.) within a specific radius

## Getting started

For development run `docker compose up --watch` to automatically restart the services once a file has changed.

For production run `docker compose up -d` to start the containers in detached mode without building the images new.

## Run tests
1. run: `docker compose up -d --build` (-d: runs container in background)
2. run  `docker compose exec geo_service pytest /app/geo_service/tests/test_geo_service.py`

## Update uv lock file
 run: `uv sync`
 (or if error: `uv sync --allow-insecure-host github.com --allow-insecure-host pypi.org --allow-insecure-host files.pythonhosted.org`)
 