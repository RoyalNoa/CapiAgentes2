from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta
from json import JSONDecodeError
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional

from src.core.logging import get_logger

_logger = get_logger(__name__)
_lock = Lock()



class TokenUsageService:
    """Gestiona la persistencia del uso de tokens de los agentes."""

    def __init__(self, token_file: Path | None = None) -> None:
        backend_root = Path(__file__).resolve().parents[3]
        self._token_file = token_file or backend_root / "ia_workspace" / "data" / "token_tracking.json"
        self._token_file.parent.mkdir(parents=True, exist_ok=True)

    def record_usage(
        self,
        agent_name: str,
        tokens_used: int,
        cost_usd: float,
        *,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        model: Optional[str] = None,
        provider: str = "openai",
        usage_timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persist real token usage metrics for an agent."""

        prompt_tokens = int(prompt_tokens or 0)
        completion_tokens = int(completion_tokens or 0)
        tokens_value = int(tokens_used or (prompt_tokens + completion_tokens))
        if tokens_value <= 0:
            raise ValueError("tokens_used debe ser mayor a cero")

        agent_id = self._normalize_agent_name(agent_name)
        cost_value = max(float(cost_usd), 0.0)
        timestamp = usage_timestamp or datetime.utcnow().isoformat()

        with _lock:
            data = self._load_data()
            agents = data.setdefault("agents", {})
            agent_entry = agents.setdefault(agent_id, self._build_empty_agent_entry())
            if self._normalize_agent_entry(agent_entry):
                data["agents"][agent_id] = agent_entry

            agent_entry["total_tokens"] = int(agent_entry.get("total_tokens", 0)) + tokens_value
            agent_entry["prompt_tokens_total"] = int(agent_entry.get("prompt_tokens_total", 0)) + prompt_tokens
            agent_entry["completion_tokens_total"] = int(agent_entry.get("completion_tokens_total", 0)) + completion_tokens
            agent_entry["cost_usd"] = round(float(agent_entry.get("cost_usd", 0.0)) + cost_value, 6)
            agent_entry["last_seen"] = timestamp
            if model:
                agent_entry["last_model"] = model
            if provider:
                agent_entry["provider"] = provider

            history = agent_entry.setdefault("history", [])
            history.append(
                {
                    "timestamp": timestamp,
                    "tokens": tokens_value,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "cost_usd": cost_value,
                    "model": model,
                    "provider": provider,
                }
            )
            if len(history) > 180:
                agent_entry["history"] = history[-180:]

            data["last_updated"] = timestamp
            self._write_data(data)

        return {
            "agent": agent_id,
            "tokens_recorded": tokens_value,
            "prompt_tokens_recorded": prompt_tokens,
            "completion_tokens_recorded": completion_tokens,
            "cost_recorded": cost_value,
            "total_tokens": agent_entry["total_tokens"],
            "total_cost": agent_entry["cost_usd"],
            "prompt_tokens_total": agent_entry["prompt_tokens_total"],
            "completion_tokens_total": agent_entry["completion_tokens_total"],
        }

    def ensure_agents(self, agent_names: Iterable[str]) -> None:
        with _lock:
            data = self._load_data()
            if self._ensure_agent_entries(data, agent_names):
                data["last_updated"] = data.get("last_updated") or datetime.utcnow().isoformat()
                self._write_data(data)

    def get_summary(self, default_agents: Iterable[str] | None = None, days: int = 30) -> Dict[str, Any]:
        if days <= 0:
            days = 30
        with _lock:
            data = self._load_data()
            changed = False
            if default_agents and self._ensure_agent_entries(data, default_agents):
                changed = True
            agents = data.get("agents", {})
            for agent_id, entry in agents.items():
                if self._normalize_agent_entry(entry):
                    changed = True
            if changed:
                data["agents"] = agents
                data["last_updated"] = data.get("last_updated") or datetime.utcnow().isoformat()
                self._write_data(data)

        total_tokens = sum(int(agent.get("total_tokens", 0)) for agent in agents.values())
        total_cost = round(sum(float(agent.get("cost_usd", 0.0)) for agent in agents.values()), 6)
        total_prompt_tokens = sum(int(agent.get("prompt_tokens_total", 0)) for agent in agents.values())
        total_completion_tokens = sum(int(agent.get("completion_tokens_total", 0)) for agent in agents.values())

        timeline = self._build_cost_timeline(agents, days)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "agents": agents,
            "total_tokens": total_tokens,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_cost_usd": total_cost,
            "cost_timeline": timeline,
        }

    def build_empty_summary(self, agent_names: Iterable[str]) -> Dict[str, Any]:
        agents = {self._normalize_agent_name(name): self._build_empty_agent_entry() for name in agent_names}
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "agents": agents,
            "total_tokens": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_cost_usd": 0.0,
            "cost_timeline": [],
        }

    def load_data(self) -> Dict[str, Any]:
        with _lock:
            return self._load_data()

    def _build_cost_timeline(self, agents: Dict[str, Any], days: int) -> List[Dict[str, Any]]:
        cutoff = datetime.utcnow().date() - timedelta(days=days - 1)
        daily_totals: Dict[str, Dict[str, Any]] = {}

        for agent_name, entry in agents.items():
            for record in entry.get("history", []):
                record_dt = self._parse_timestamp(record.get("timestamp"))
                if not record_dt:
                    continue
                if record_dt.date() < cutoff:
                    continue
                key = record_dt.date().isoformat()
                day_entry = daily_totals.setdefault(
                    key,
                    {
                        "date": key,
                        "agents": defaultdict(lambda: {"tokens": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0}),
                    },
                )
                agent_bucket = day_entry["agents"][agent_name]
                agent_bucket["tokens"] += int(record.get("tokens", 0))
                agent_bucket["prompt_tokens"] += int(record.get("prompt_tokens", 0))
                agent_bucket["completion_tokens"] += int(record.get("completion_tokens", 0))
                agent_bucket["cost_usd"] = round(agent_bucket["cost_usd"] + float(record.get("cost_usd", 0.0)), 6)

        timeline: List[Dict[str, Any]] = []
        for date_key in sorted(daily_totals.keys()):
            agents_payload = {}
            total_tokens = 0
            total_cost = 0.0
            total_prompt = 0
            total_completion = 0
            for agent_name, payload in daily_totals[date_key]["agents"].items():
                agents_payload[agent_name] = payload
                total_tokens += payload["tokens"]
                total_cost = round(total_cost + payload["cost_usd"], 6)
                total_prompt += payload["prompt_tokens"]
                total_completion += payload["completion_tokens"]
            timeline.append(
                {
                    "date": date_key,
                    "agents": agents_payload,
                    "total_tokens": total_tokens,
                    "total_prompt_tokens": total_prompt,
                    "total_completion_tokens": total_completion,
                    "total_cost_usd": round(total_cost, 6),
                }
            )
        return timeline

    def _load_data(self) -> Dict[str, Any]:
        if not self._token_file.exists():
            return {"agents": {}, "last_updated": None}

        try:
            with self._token_file.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (JSONDecodeError, OSError) as exc:
            _logger.warning(
                {
                    "event": "token_tracking_load_failed",
                    "error": str(exc),
                }
            )
            return {"agents": {}, "last_updated": None}

    def _write_data(self, data: Dict[str, Any]) -> None:
        temp_file = self._token_file.with_suffix(".tmp")
        with temp_file.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
        temp_file.replace(self._token_file)

    @staticmethod
    def _normalize_agent_name(name: str | None) -> str:
        return (name or "").strip() or "unknown"

    @staticmethod
    def _build_empty_agent_entry() -> Dict[str, Any]:
        return {
            "total_tokens": 0,
            "prompt_tokens_total": 0,
            "completion_tokens_total": 0,
            "cost_usd": 0.0,
            "history": [],
            "provider": "openai",
        }

    def _ensure_agent_entries(self, data: Dict[str, Any], agent_names: Iterable[str]) -> bool:
        updated = False
        agents = data.setdefault("agents", {})
        for name in agent_names or []:
            agent_id = self._normalize_agent_name(name)
            if agent_id not in agents:
                agents[agent_id] = self._build_empty_agent_entry()
                updated = True
        return updated

    @staticmethod
    def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            if value.endswith("Z"):
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _normalize_agent_entry(entry: Dict[str, Any]) -> bool:
        updated = False
        if "prompt_tokens_total" not in entry:
            entry["prompt_tokens_total"] = 0
            updated = True
        if "completion_tokens_total" not in entry:
            entry["completion_tokens_total"] = 0
            updated = True
        if "history" not in entry or not isinstance(entry.get("history"), list):
            entry["history"] = []
            updated = True
        return updated
