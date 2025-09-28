"""Parallel endpoints service latency test.

Goal:
    One parallel batch (one call per geo endpoint)
    must complete under the total time limit (10 seconds).
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

SECONDS_LIMIT = 10.0  # Total wall-clock limit
MAX_WORKERS = 4  # Enough threads for all endpoints
LOCATION = {"lat": 50.1109, "lng": 8.6821, "radius": 5000}  # Frankfurt am Main


def _requests() -> list[tuple[str, str, dict[str, float]]]:
    """Return single parallel batch: one request per endpoint."""
    return [
        ("power", "/geo/power", LOCATION),
        ("protection", "/geo/protection", LOCATION),
        ("forest", "/geo/forest", LOCATION),
        ("builtup", "/geo/builtup", LOCATION),
    ]


def _request(client, path: str, params: dict[str, Any]):
    start = time.perf_counter()
    resp = client.get(path, params=params)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return path, resp.status_code, elapsed_ms


def test_parallel_endpoints_under_sla(test_app):
    """One parallel batch (5 endpoints) must complete under SLA."""
    request_set = _requests()
    start = time.perf_counter()

    results: list[tuple[str, int, float]] = []
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(request_set))) as pool:
        futures = [
            pool.submit(_request, test_app, path, params)
            for _, path, params in request_set
        ]
        for fut in as_completed(futures):
            path, status, elapsed_ms = fut.result()
            results.append((path, status, elapsed_ms))
            assert status == 200, f"Endpoint {path} returned {status}"

    total_elapsed = time.perf_counter() - start

    assert (
        total_elapsed < SECONDS_LIMIT
    ), f"Parallel endpoints exceeded time: {total_elapsed:.2f}s >= {SECONDS_LIMIT:.2f}s; requests={len(results)}"
