"""Utilities to control workflow simulation timing.

These helpers centralize how we scale sleep durations so we can tweak pacing
from configuration without touching each node.
"""
from __future__ import annotations

import asyncio
import time
from src.core.config import get_settings


def _clamp(value: float, minimum: float = 0.0) -> float:
    return value if value >= minimum else minimum


def scale_duration(duration_seconds: float) -> float:
    """Return the adjusted duration after applying workflow timing settings."""
    if duration_seconds <= 0:
        return 0.0

    settings = get_settings()
    scale: float = getattr(settings, "WORKFLOW_TIMING_SCALE", 1.0) or 0.0
    min_sleep: float = getattr(settings, "WORKFLOW_MIN_SLEEP_SECONDS", 0.0) or 0.0

    scaled = duration_seconds * max(scale, 0.0)
    if scaled <= 0.0:
        return 0.0

    if min_sleep > 0.0:
        scaled = max(min_sleep, scaled)
    return scaled


async def workflow_sleep(duration_seconds: float) -> None:
    """Sleep asynchronously using the scaled workflow duration."""
    adjusted = scale_duration(duration_seconds)
    if adjusted <= 0.0:
        if duration_seconds > 0:
            await asyncio.sleep(0)
        return
    await asyncio.sleep(adjusted)


def workflow_sleep_sync(duration_seconds: float) -> None:
    """Sleep synchronously using the scaled workflow duration."""
    adjusted = scale_duration(duration_seconds)
    if adjusted <= 0.0:
        if duration_seconds > 0:
            time.sleep(0)
        return
    time.sleep(adjusted)
