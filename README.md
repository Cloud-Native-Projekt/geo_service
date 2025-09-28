# Overview

A FastAPI microservice that derives geographic context information for a point (latitude/longitude + radius (max 5 km)) from OpenStreetMap / Overpass. It currently returns: distance to power infrastructure, protected area status, forest presence/type, and whether the location has buildings around it.

## Purpose

Typical use cases: pre‑validation or scoring for site selection (energy projects, infrastructure planning, environmental assessment).

## Endpoints

All endpoints are `GET` and (except health) require `lat`, `lng`, `radius` query parameters.

| Endpoint          | Description                                 | Sample Response Snippet                                                             |
| ----------------- | ------------------------------------------- | ----------------------------------------------------------------------------------- | ------- |
| `/geo/health`     | Lightweight health/liveness check           | `{ "status": "healthy" }`                                                           |
| `/geo/power`      | Distance to nearest substation & power line | `{ "nearest_substation_distance_m": float, "nearest_powerline_distance_m": float }` |
| `/geo/protection` | Whether point lies in a protected area      | `{ "in_protected_area": bool, "designation": str                                    | null }` |
| `/geo/forest`     | Forest presence & (simplified) type         | `{ "in_forest": bool, "type": str                                                   | null }` |
| `/geo/builtup`    | Builtdings in area / populated indicator    | `{ "in_populated_area": bool }`                                                     |

Example:

```bash
curl "http://localhost:8000/geo/forest?lat=48.232089&lng=11.466577&radius=5000"
```

## Directory Structure

```text
geo_service/
  config.py          # Pydantic settings
  main.py            # FastAPI app, lifespan, router registration
  dependencies.py    # Dependency wiring (GeoService instance)
  routes/            # API router definitions
  schemas/           # Pydantic request/response models
  services/          # Business orchestration + TTL caching
  repositories/      # Overpass / OSM access + geometry logic
    implementations/ # Concrete repository (queries, distance calculations)
    interfaces/      # Interfaces for testability & future adapters
  tests/             # Pytest suite
```

### Layering

- `routes` → translate HTTP to domain objects (`GeoCond`)
- `services` → orchestrate repo calls, apply TTL cache + per-key locks
- `repositories` → Overpass queries + geospatial calculations
- `schemas` → validation & clear response contracts

## Caching & Performance

Multi-layer:

1. In-memory TTL cache (service layer) keyed by `(domain, lat_rounded, lng_rounded, radius)`
2. Per-key `asyncio.Lock` to prevent thundering herd effects
3. Repository-level `@lru_cache(maxsize=128)` for raw Overpass results (no TTL)
4. Coordinate rounding (`GEO_CACHE_PRECISION`, default 6) to boost hit rate
5. Parallelism cap for Overpass via semaphore (`OVERPASS_MAX_PAR`)

## Tests

| File                  | Focus                                                                  |
| --------------------- | ---------------------------------------------------------------------- |
| `test_geo_service.py` | Functional end-to-end tests of all geo endpoints (various coordinates) |

Fixtures / Utilities:

- `conftest.py` provides a test client.

Run all tests (in container):

```bash
docker compose exec geo_service pytest -q
```

## Run in Docker

Development:

```bash
docker compose up --watch
```

Detached:

```bash
docker compose up -d
```
