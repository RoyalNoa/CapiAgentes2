import math

from src.voice import metrics


def _gauge_value(gauge) -> float:
    return gauge._value.get()


def _counter_value(counter) -> float:
    return counter._value.get()


def _hist_sum(histogram) -> float:
    return histogram._sum.get()


def test_stream_metrics_records_bytes_and_warnings():
    start_active = _gauge_value(metrics.VOICE_ACTIVE_STREAMS)
    start_bytes = _counter_value(metrics.VOICE_STREAM_BYTES)
    start_warnings = metrics.VOICE_STREAM_WARNINGS.labels(reason="duration_exceeded")._value.get()

    ctx = metrics.stream_started(session_id="sess", user_id="user", sample_rate_hz=16000, limit_seconds=2)
    assert math.isclose(_gauge_value(metrics.VOICE_ACTIVE_STREAMS), start_active + 1.0)

    duration = metrics.stream_frame_received(ctx, bytes_length=3200)
    # 3200 bytes -> 1600 samples -> 0.1 s @ 16kHz
    assert math.isclose(duration, 0.1, rel_tol=1e-3)
    assert math.isclose(_counter_value(metrics.VOICE_STREAM_BYTES), start_bytes + 3200.0)

    metrics.stream_finished(ctx, result="warning", warning_reason="duration_exceeded")
    assert math.isclose(_gauge_value(metrics.VOICE_ACTIVE_STREAMS), start_active)
    assert math.isclose(
        metrics.VOICE_STREAM_WARNINGS.labels(reason="duration_exceeded")._value.get(),
        start_warnings + 1.0,
    )


def test_voice_turn_latency_tracks_success_and_failure():
    start_success = metrics.VOICE_TURNS.labels(result="success")._value.get()
    start_error = metrics.VOICE_TURNS.labels(result="error")._value.get()
    start_latency = _hist_sum(metrics.VOICE_TURN_LATENCY)

    token = metrics.voice_turn_started()
    metrics.voice_turn_completed(token)
    after_success = metrics.VOICE_TURNS.labels(result="success")._value.get()
    assert math.isclose(after_success, start_success + 1.0)

    token = metrics.voice_turn_started()
    metrics.voice_turn_failed(token)
    after_error = metrics.VOICE_TURNS.labels(result="error")._value.get()
    assert math.isclose(after_error, start_error + 1.0)

    # Hist sum should increase (monotonic)
    end_latency = _hist_sum(metrics.VOICE_TURN_LATENCY)
    assert end_latency >= start_latency
