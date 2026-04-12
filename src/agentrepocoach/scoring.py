"""Shared scoring primitives used by every component."""
from __future__ import annotations

import time
from pathlib import Path


def scale_linear(value: float, zero_at: float, full_at: float, max_pts: float) -> float:
    """Linear interpolation from ``zero_at`` -> 0 to ``full_at`` -> ``max_pts``.

    Clamps outside the range. Handles the inverted case (``zero_at`` > ``full_at``)
    for "lower is better" metrics.
    """
    if zero_at == full_at:
        return float(max_pts) if value == full_at else 0.0
    if zero_at < full_at:
        if value <= zero_at:
            return 0.0
        if value >= full_at:
            return float(max_pts)
        return max_pts * (value - zero_at) / (full_at - zero_at)
    # Inverted: lower is better.
    if value >= zero_at:
        return 0.0
    if value <= full_at:
        return float(max_pts)
    return max_pts * (zero_at - value) / (zero_at - full_at)


def file_mtime_age_days(path: Path) -> float:
    """Return the age of ``path`` in days (fractional). Returns +inf if missing."""
    if not path.exists():
        return float("inf")
    return (time.time() - path.stat().st_mtime) / 86400.0
