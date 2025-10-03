from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from src.application.services.token_usage_service import TokenUsageService


def _iso(days_delta: int) -> str:
    target = datetime.utcnow() + timedelta(days=days_delta)
    return target.replace(microsecond=0).isoformat() + 'Z'


def test_token_usage_service_timeline(tmp_path: Path) -> None:
    service = TokenUsageService(token_file=tmp_path / "token_tracking.json")

    service.record_usage(
        "summary",
        tokens_used=100,
        cost_usd=0.12,
        prompt_tokens=70,
        completion_tokens=30,
        usage_timestamp=_iso(-2),
    )
    service.record_usage(
        "summary",
        tokens_used=50,
        cost_usd=0.05,
        prompt_tokens=30,
        completion_tokens=20,
        usage_timestamp=_iso(-1),
    )
    service.record_usage(
        "branch",
        tokens_used=40,
        cost_usd=0.02,
        prompt_tokens=25,
        completion_tokens=15,
        usage_timestamp=_iso(-1),
    )

    summary = service.get_summary(days=3)

    assert summary["total_tokens"] == 190
    assert summary["total_prompt_tokens"] == 125
    assert summary["total_completion_tokens"] == 65
    assert summary["total_cost_usd"] == 0.19

    timeline = summary["cost_timeline"]
    assert len(timeline) == 2

    day_map = {point["date"]: point for point in timeline}
    assert summary["total_tokens"] == sum(point["total_tokens"] for point in timeline)

    latest_date = max(day_map)
    day2 = day_map[latest_date]
    assert day2["total_tokens"] == 90
    assert day2["agents"]["summary"]["tokens"] == 50
    assert day2["agents"]["branch"]["tokens"] == 40
    assert day2["total_cost_usd"] == 0.07
