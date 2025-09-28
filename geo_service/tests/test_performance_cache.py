"""Performance test verifying HTTP-layer cache effectiveness for geo endpoints.

Measures cold vs. warm latency for two locations (Berlin / Cologne) across all
geo endpoints and asserts:
    * Warm requests are not dramatically slower than cold ones (tolerance factor).
    * At least one endpoint exhibits a minimum speedup (cache effectiveness signal).
Print output was intentionally removed; assertions now carry the diagnostics.
"""

from __future__ import annotations

import math
import time
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Configuration constants (tweak with care)
# ---------------------------------------------------------------------------
SPEEDUP_MIN = 1.10  # Minimum acceptable speedup for at least one endpoint
WARM_SLOWDOWN_FACTOR = 1.5  # Warm request must not exceed this multiple of cold

# Coordinate payloads chosen to avoid collision with other tests & represent
LOCATION_A = {"lat": 52.52, "lng": 13.405, "radius": 5000}  # Berlin
LOCATION_B = {"lat": 50.9375, "lng": 6.9603, "radius": 5000}  # Cologne


def _timed_request(client, path: str, params: dict | None = None) -> tuple[float, Any]:
    """Issue a synchronous GET request and return (elapsed_ms, response).

    Using time.perf_counter for high‑resolution timing. We intentionally include
    the network stack + serialization overhead inside the timing to reflect
    real perceived latency from a client's viewpoint (even though in tests the
    client is in‑process).
    """
    start = time.perf_counter()
    resp = client.get(path, params=params)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return elapsed_ms, resp


def _ratio(cold: float, warm: float) -> float:
    """Return cold/warm speedup ratio, or NaN if warm is zero / invalid."""
    if warm <= 0:
        return math.nan
    return cold / warm


def test_performance_cache(test_app):
    """Measure cold vs. warm timings over geo endpoints and validate cache impact."""
    serial_order: list[tuple[str, str, dict]] = [
        ("power", "/geo/power", LOCATION_A),
        ("protection", "/geo/protection", LOCATION_A),
        ("forest", "/geo/forest", LOCATION_A),
        ("builtup", "/geo/builtup", LOCATION_A),
    ]

    # Domain-only subset for LOCATION_B
    domain_only: list[tuple[str, str, dict]] = [
        ("power", "/geo/power", LOCATION_B),
        ("protection", "/geo/protection", LOCATION_B),
        ("forest", "/geo/forest", LOCATION_B),
        ("builtup", "/geo/builtup", LOCATION_B),
    ]

    # --- Phase 1: Cold serial (LOCATION_A) ---
    cold_serial: dict[str, float] = {}
    for label, path, params in serial_order:
        dur, resp = _timed_request(test_app, path, params)
        assert (
            resp.status_code == 200
        ), f"Cold serial {label} failed ({resp.status_code})"
        cold_serial[label] = dur

    # --- Phase 2: Cold domain (LOCATION_B) ---
    cold_domain: dict[str, float] = {}
    for label, path, params in domain_only:
        dur, resp = _timed_request(test_app, path, params)
        assert (
            resp.status_code == 200
        ), f"Cold domain {label} failed ({resp.status_code})"
        cold_domain[label] = dur

    # --- Phase 3: Warm serial (LOCATION_A) ---
    warm_serial: dict[str, float] = {}
    for label, path, params in serial_order:
        dur, resp = _timed_request(test_app, path, params)
        assert (
            resp.status_code == 200
        ), f"Warm serial {label} failed ({resp.status_code})"
        warm_serial[label] = dur

    # --- Phase 4: Warm domain (LOCATION_B) ---
    warm_domain: dict[str, float] = {}
    for label, path, params in domain_only:
        dur, resp = _timed_request(test_app, path, params)
        assert (
            resp.status_code == 200
        ), f"Warm domain {label} failed ({resp.status_code})"
        warm_domain[label] = dur

    # Assert warm not dramatically slower (tolerate variance)
    for label, cold_time in cold_serial.items():
        warm_time = warm_serial[label]
        assert (
            warm_time <= cold_time * WARM_SLOWDOWN_FACTOR
        ), f"Warm serial {label} slower than expected: cold={cold_time:.2f}ms warm={warm_time:.2f}ms"
    for label, cold_time in cold_domain.items():
        warm_time = warm_domain[label]
        assert (
            warm_time <= cold_time * WARM_SLOWDOWN_FACTOR
        ), f"Warm domain {label} slower than expected: cold={cold_time:.2f}ms warm={warm_time:.2f}ms"

    # Collect speedups for endpoints across both locations
    speedups = [_ratio(cold_serial[l], warm_serial[l]) for l in cold_serial] + [
        _ratio(cold_domain[l], warm_domain[l]) for l in cold_domain
    ]

    # Ensure at least one endpoint shows an improvement >= SPEEDUP_MIN
    meaningful_speedups = [s for s in speedups if not math.isnan(s)]
    if not any(s >= SPEEDUP_MIN for s in meaningful_speedups):
        max_speedup = max(meaningful_speedups) if meaningful_speedups else float("nan")
        pytest.fail(
            f"No significant speedup >= {SPEEDUP_MIN:.2f} observed. Max speedup={max_speedup:.2f}; "
            f"ratios={[f'{s:.2f}' for s in meaningful_speedups]}"
        )
