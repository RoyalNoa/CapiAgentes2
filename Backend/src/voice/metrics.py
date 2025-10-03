"""Lightweight Prometheus-style metrics helpers for voice streaming."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal, Optional

from prometheus_client import Counter, Gauge, Histogram  # type: ignore

# Gauges
VOICE_ACTIVE_STREAMS = Gauge(
    "voice_active_streams",
    "Number of voice WebSocket streams currently opened",
)

# Counters
VOICE_STREAM_BYTES = Counter(
    "voice_stream_bytes_total",
    "Total audio bytes received from clients",
)
VOICE_STREAM_WARNINGS = Counter(
    "voice_stream_warnings_total",
    "Number of voice streams terminated with warnings",
    labelnames=("reason",),
)
VOICE_TURNS = Counter(
    "voice_turns_total",
    "Completed voice turns processed by the orchestrator",
    labelnames=("result",),
)

# Histograms
VOICE_STREAM_DURATION = Histogram(
    "voice_stream_duration_seconds",
    "Observed voice capture duration per turn",
    buckets=(0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0, 60.0),
)
VOICE_TURN_LATENCY = Histogram(
    "voice_turn_latency_milliseconds",
    "Latency of voice turns from transcript ingestion to response",
    buckets=(200, 500, 1000, 2000, 3000, 5000, 10000, 20000),
)


@dataclass
class StreamMetricsContext:
    """Runtime statistics collected during a single voice stream."""

    session_id: str
    user_id: str
    sample_rate_hz: int
    started_at: float = field(default_factory=time.monotonic)
    bytes_received: int = 0
    limit_seconds: Optional[int] = None
    completed: bool = False

    def register_bytes(self, amount: int) -> float:
        self.bytes_received += amount
        VOICE_STREAM_BYTES.inc(amount)
        duration = self.estimated_duration_seconds
        return duration

    @property
    def estimated_duration_seconds(self) -> float:
        if self.sample_rate_hz <= 0:
            return 0.0
        # 16-bit PCM -> 2 bytes per sample
        samples = self.bytes_received / 2
        return samples / float(self.sample_rate_hz)

    def finalize(self, *, result: Literal["success", "warning", "error"], warning_reason: str | None = None) -> None:
        if self.completed:
            return
        self.completed = True
        _ = time.monotonic() - self.started_at
        VOICE_ACTIVE_STREAMS.dec()
        if warning_reason:
            VOICE_STREAM_WARNINGS.labels(reason=warning_reason).inc()
        VOICE_STREAM_DURATION.observe(self.estimated_duration_seconds)


def stream_started(*, session_id: str, user_id: str, sample_rate_hz: int, limit_seconds: Optional[int]) -> StreamMetricsContext:
    VOICE_ACTIVE_STREAMS.inc()
    return StreamMetricsContext(
        session_id=session_id,
        user_id=user_id,
        sample_rate_hz=sample_rate_hz,
        limit_seconds=limit_seconds,
    )


def stream_frame_received(ctx: StreamMetricsContext, *, bytes_length: int) -> float:
    """Update counters for a new audio frame. Returns estimated duration."""
    return ctx.register_bytes(bytes_length)


def stream_finished(ctx: StreamMetricsContext, *, result: Literal["success", "warning", "error"], warning_reason: str | None = None) -> None:
    ctx.finalize(result=result, warning_reason=warning_reason)


def voice_turn_started() -> float:
    return time.perf_counter()


def voice_turn_completed(started_at: float) -> None:
    elapsed_ms = (time.perf_counter() - started_at) * 1000.0
    VOICE_TURN_LATENCY.observe(elapsed_ms)
    VOICE_TURNS.labels(result="success").inc()


def voice_turn_failed(started_at: float) -> None:
    elapsed_ms = (time.perf_counter() - started_at) * 1000.0
    VOICE_TURN_LATENCY.observe(elapsed_ms)
    VOICE_TURNS.labels(result="error").inc()

