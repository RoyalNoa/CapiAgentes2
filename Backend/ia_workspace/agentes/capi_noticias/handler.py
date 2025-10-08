"""
Capi Noticias Agent
===================

Agente especializado en monitorear noticias de Ambito.com con foco
financiero para detectar eventos que puedan afectar el flujo de
efectivo en sucursales bancarias.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import hashlib
import textwrap
import unicodedata
from collections import Counter
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Callable
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from src.core.exceptions import AgentError
from src.domain.agents.agent_protocol import BaseAgent, AgentRequest, AgentResponse, IntentType
from src.infrastructure.agents.progress_emitter import agent_progress

AgentResult = AgentResponse

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 12.0
HISTORY_LIMIT = 50
DEFAULT_SOURCES = [
    "https://www.ambito.com/finanzas",
    "https://www.ambito.com/economia",
    "https://www.ambito.com/politica"
]
DEFAULT_INTERVAL_MINUTES = 60
MAX_ARTICLES_PER_SOURCE = 5

ALLOWED_DOMAINS = {"ambito.com"}
CHARS_PER_TOKEN = 4
USD_PER_1K_TOKENS = 0.0015

DEFAULT_SEGMENT_CONFIG = {
    "daily": {
        "file": "daily.json",
        "min_priority": 4.0,
        "fallback_min": 5,
        "max_items": 25,
        "lookback_hours": 36
    },
    "weekly": {
        "file": "weekly.json",
        "min_priority": 5.5,
        "fallback_min": 12,
        "max_items": 45,
        "lookback_days": 7
    },
    "monthly": {
        "file": "monthly.json",
        "min_priority": 6.5,
        "fallback_min": 18,
        "max_items": 60,
        "lookback_days": 30
    }
}


def _is_allowed_domain(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return False
    return any(host == domain or host.endswith(f".{domain}") for domain in ALLOWED_DOMAINS)


@dataclass
class NewsArticle:
    """Representa una noticia normalizada."""

    url: str
    headline: str
    summary: str
    published_at: Optional[datetime]
    source: str
    score: float
    tags: List[str] = field(default_factory=list)
    raw_keywords: List[str] = field(default_factory=list)
    snippet: str = ""
    impact_level: str = "low"
    relevance_signals: List[str] = field(default_factory=list)
    branch_targets: List[str] = field(default_factory=list)
    urgency_level: str = "normal"
    suggested_actions: List[str] = field(default_factory=list)
    priority_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "headline": self.headline,
            "summary": self.summary,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "source": self.source,
            "score": round(self.score, 2),
            "tags": sorted(set(self.tags)),
            "raw_keywords": self.raw_keywords,
            "snippet": self.snippet,
            "impact_level": self.impact_level,
            "relevance_signals": sorted(set(self.relevance_signals)),
            "branch_targets": sorted(set(self.branch_targets)),
            "urgency_level": self.urgency_level,
            "suggested_actions": self.suggested_actions,
            "priority_score": round(self.priority_score, 2),
        }


class CapiNoticiasConfigManager:
    """Gestiona configuracin y estado persistente del agente."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        workspace_root = Path(__file__).resolve().parents[2]
        self.data_dir = workspace_root / "data" / "noticias"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.data_dir / "config.json"
        self.status_path = self.data_dir / "status.json"
        self.history_path = self.data_dir / "news_history.json"
        self.runs_dir = self.data_dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.segments_dir = self.data_dir / "segments"
        self.segments_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> Dict[str, Any]:
        default = {
            "enabled": True,
            "interval_minutes": DEFAULT_INTERVAL_MINUTES,
            "max_articles_per_source": MAX_ARTICLES_PER_SOURCE,
            "source_urls": DEFAULT_SOURCES,
            "last_updated": datetime.utcnow().isoformat(),
        }
        with self._lock:
            config = self._read_json(self.config_path, default)

            source_urls = config.get("source_urls") or []
            config["source_urls"] = [
                url.strip() for url in source_urls if isinstance(url, str) and url.strip()
            ] or DEFAULT_SOURCES

            interval = config.get("interval_minutes", DEFAULT_INTERVAL_MINUTES)
            config["interval_minutes"] = max(5, int(interval) if isinstance(interval, (int, float)) else DEFAULT_INTERVAL_MINUTES)

            per_source = config.get("max_articles_per_source", MAX_ARTICLES_PER_SOURCE)
            config["max_articles_per_source"] = max(1, int(per_source) if isinstance(per_source, (int, float)) else MAX_ARTICLES_PER_SOURCE)

            if "enabled" not in config:
                config["enabled"] = True

            segments = config.get("segments") or {}
            merged_segments = {}
            for name, defaults in DEFAULT_SEGMENT_CONFIG.items():
                user_cfg = segments.get(name) or {}
                merged = defaults.copy()
                for key, value in user_cfg.items():
                    if key not in defaults or value is None:
                        continue
                    default_value = defaults[key]
                    try:
                        if isinstance(default_value, float):
                            merged[key] = float(value)
                        elif isinstance(default_value, int):
                            merged[key] = int(value)
                        else:
                            merged[key] = value
                    except (TypeError, ValueError):
                        merged[key] = default_value
                merged_segments[name] = merged
            config["segments"] = merged_segments

            return config

    def get_segment_config(self) -> Dict[str, Dict[str, Any]]:
        config = self.load_config()
        segments = config.get("segments") or {}
        return {name: dict(values) for name, values in segments.items()}

    def save_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            current = self.load_config()
            payload = {k: v for k, v in data.items() if k != "segments"}
            current.update(payload)

            segments_update = data.get("segments") or {}
            if segments_update:
                segments = current.get("segments") or {}
                for name, overrides in segments_update.items():
                    if name not in DEFAULT_SEGMENT_CONFIG:
                        continue
                    base = segments.get(name, DEFAULT_SEGMENT_CONFIG[name].copy()).copy()
                    for key, value in (overrides or {}).items():
                        if key not in DEFAULT_SEGMENT_CONFIG[name] or value is None:
                            continue
                        default_value = DEFAULT_SEGMENT_CONFIG[name][key]
                        try:
                            if isinstance(default_value, float):
                                base[key] = float(value)
                            elif isinstance(default_value, int):
                                base[key] = int(value)
                            else:
                                base[key] = value
                        except (TypeError, ValueError):
                            continue
                    segments[name] = base
                current["segments"] = segments

            current["last_updated"] = datetime.utcnow().isoformat()
            self._write_json(self.config_path, current)
            return current

    def load_status(self) -> Dict[str, Any]:
        default = {
            "is_running": False,
            "last_run": None,
            "last_success": None,
            "last_error": None,
            "next_run": None,
            "last_trigger": None,
            "run_history": []
        }
        with self._lock:
            status = self._read_json(self.status_path, default)
            status.setdefault("run_history", [])
            return status

    def save_status(self, status: Dict[str, Any]) -> None:
        with self._lock:
            history = status.get("run_history", [])
            status["run_history"] = history[-HISTORY_LIMIT:]
            self._write_json(self.status_path, status)

    def mark_running(self, trigger: str, next_run: Optional[datetime]) -> None:
        with self._lock:
            status = self.load_status()
            status.update(
                {
                    "is_running": True,
                    "last_error": None,
                    "last_trigger": trigger,
                    "started_at": datetime.utcnow().isoformat(),
                    "next_run": next_run.isoformat() if next_run else status.get("next_run"),
                }
            )
            self.save_status(status)

    def record_run(
        self,
        *,
        trigger: str,
        success: bool,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        next_run: Optional[datetime] = None,
    ) -> None:
        timestamp = datetime.utcnow().isoformat()
        with self._lock:
            status = self.load_status()
            history = self._read_json(self.history_path, [])

            run_entry = {
                "timestamp": timestamp,
                "trigger": trigger,
                "success": success,
                "error": error_message,
                "article_count": len(result.get("articles", [])) if result else 0,
                "highlights": (result.get("summary") or {}).get("headline") if result else None,
            }
            storage_info = (result or {}).get("storage") or {}
            run_entry["persisted"] = len(storage_info.get("saved", []))
            run_entry["skipped"] = len(storage_info.get("skipped", []))
            if storage_info:
                run_entry["storage_root"] = storage_info.get("root")
                run_entry["storage_errors"] = len(storage_info.get("errors", []))
            metrics_info = (result or {}).get("metrics") or {}
            if metrics_info:
                if "estimated_tokens" in metrics_info:
                    run_entry["estimated_tokens"] = metrics_info.get("estimated_tokens")
                if "estimated_cost_usd" in metrics_info:
                    run_entry["estimated_cost_usd"] = metrics_info.get("estimated_cost_usd")
            history.append(run_entry)
            history = history[-HISTORY_LIMIT:]

            status.update(
                {
                    "is_running": False,
                    "last_run": timestamp,
                    "last_success": timestamp if success else status.get("last_success"),
                    "last_error": error_message,
                    "next_run": next_run.isoformat() if next_run else status.get("next_run"),
                    "last_trigger": trigger,
                    "run_history": history,
                }
            )

            self._write_json(self.history_path, history)
            self.save_status(status)

    def get_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return self._read_json(self.history_path, [])

    def _read_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            text = path.read_text(encoding="utf-8")
            if not text.strip():
                return default
            return json.loads(text)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Error reading %s: %s", path, exc)
            return default

    def _write_json(self, path: Path, data: Any) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Error writing %s: %s", path, exc)


class NoticiasStorage:
    """Persistencia de salidas de Capi Noticias en el workspace."""

    def __init__(
        self,
        runs_root: Path,
        segments_root: Optional[Path] = None,
        segment_config_provider: Optional[Callable[[], Dict[str, Any]]] = None,
    ) -> None:
        self.root = Path(runs_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.segments_root = Path(segments_root) if segments_root else self.root.parent / "segments"
        self.segments_root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self._lock = threading.RLock()
        self._segment_config_provider = segment_config_provider or (
            lambda: {name: defaults.copy() for name, defaults in DEFAULT_SEGMENT_CONFIG.items()}
        )
        self.segment_aggregator = SegmentAggregator(
            self,
            self.root,
            self.segments_root,
            self._segment_config_provider,
        )

    def persist_run(self, run_result: Dict[str, Any]) -> Dict[str, Any]:
        """Guarda noticias y retorna un resumen de la operación."""
        summary: Dict[str, Any] = {
            "saved": [],
            "skipped": [],
            "errors": [],
            "root": str(self.root),
        }

        articles = run_result.get("articles") or []
        if not articles:
            return summary

        generated_at = self._parse_datetime(run_result.get("generated_at")) or datetime.utcnow()

        with self._lock:
            index = self._load_index()
            for article in articles:
                try:
                    canonical_url = (article.get("url") or "").strip()
                    if not canonical_url:
                        raise ValueError("url no disponible para persistencia")
                    if not _is_allowed_domain(canonical_url):
                        summary["skipped"].append(
                            {
                                "fingerprint": None,
                                "url": canonical_url,
                                "reason": "domain_not_allowed",
                            }
                        )
                        continue

                    published = self._parse_datetime(article.get("published_at")) or generated_at
                    fingerprint = self._compute_fingerprint(canonical_url, published)

                    if fingerprint in index:
                        summary["skipped"].append(
                            {
                                "fingerprint": fingerprint,
                                "url": canonical_url,
                                "reason": "duplicate",
                            }
                        )
                        continue

                    output_dir = self._ensure_output_dir(published)
                    title = article.get("headline") or "Sin título"
                    sanitized_title = self._sanitize_title(title)
                    date_prefix = published.strftime("%Y-%m.%d")
                    base_name = f"{date_prefix} - {sanitized_title}"
                    md_path, json_path = self._resolve_output_paths(output_dir, base_name)

                    markdown_body = self._render_markdown(title, article, published, fingerprint)
                    md_path.write_text(markdown_body, encoding="utf-8")

                    json_payload = self._build_json_payload(
                        article,
                        run_result,
                        fingerprint,
                        md_path,
                        json_path,
                        published,
                    )
                    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")

                    entry = {
                        "fingerprint": fingerprint,
                        "headline": title,
                        "url": canonical_url,
                        "published_at": published.isoformat(),
                        "md_path": str(md_path.relative_to(self.root)),
                        "json_path": str(json_path.relative_to(self.root)),
                    }
                    index[fingerprint] = entry
                    summary["saved"].append(entry)
                    self._append_daily_index(output_dir, published, entry)
                except Exception as exc:
                    logger.exception("[capi_noticias] Error al persistir noticia: %s", exc)
                    summary["errors"].append(
                        {
                            "url": (article.get("url") or article.get("source")),
                            "reason": str(exc),
                        }
                    )
            self._save_index(index)

        summary["segments"] = self.segment_aggregator.update_segments(run_result, summary["saved"], index)
        return summary

    def _ensure_output_dir(self, published: datetime) -> Path:
        directory = self.root / f"{published.year:04d}" / f"{published.month:02d}"
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _resolve_output_paths(self, directory: Path, base_name: str) -> Tuple[Path, Path]:
        md_candidate = directory / f"{base_name}.md"
        json_candidate = directory / f"{base_name}.json"
        counter = 2
        while md_candidate.exists() or json_candidate.exists():
            md_candidate = directory / f"{base_name} ({counter}).md"
            json_candidate = directory / f"{base_name} ({counter}).json"
            counter += 1
        return md_candidate, json_candidate

    def _compute_fingerprint(self, url: str, published: datetime) -> str:
        day_key = published.strftime("%Y%m%d")
        return hashlib.sha256(f"{url}|{day_key}".encode("utf-8")).hexdigest()

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        value = value.strip()
        if not value:
            return None
        normalized = value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            try:
                dt = datetime.fromisoformat(normalized.split(".")[0])
            except ValueError:
                return None
        if dt.tzinfo is None:
            return dt
        return dt.astimezone(timezone.utc).replace(tzinfo=None)

    def _sanitize_title(self, title: str) -> str:
        normalized = unicodedata.normalize("NFKD", title)
        ascii_title = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        ascii_title = ascii_title.encode("ascii", "ignore").decode("ascii")
        ascii_title = re.sub(r"[<>:\"/\|?*]", "", ascii_title)
        ascii_title = re.sub(r"\s+", " ", ascii_title).strip()
        if not ascii_title:
            ascii_title = "noticia"
        return ascii_title[:80]

    def _render_markdown(
        self,
        title: str,
        article: Dict[str, Any],
        published: datetime,
        fingerprint: str,
    ) -> str:
        tags = article.get("tags") or []
        signals = article.get("relevance_signals") or []
        branches = article.get("branch_targets") or []
        actions = article.get("suggested_actions") or []
        tags_yaml = ", ".join(f'"{self._escape_yaml(tag)}"' for tag in tags)
        signals_yaml = ", ".join(f'"{self._escape_yaml(sig)}"' for sig in signals)
        branches_yaml = ", ".join(f'"{self._escape_yaml(branch)}"' for branch in branches)
        actions_yaml = ", ".join(f'"{self._escape_yaml(action)}"' for action in actions)
        front_matter = [
            "---",
            f'titulo: "{self._escape_yaml(title)}"',
            f'fecha: "{published.isoformat()}"',
            f'fuente: "{self._escape_yaml(article.get("source", "ambito.com"))}"',
            f'url: "{self._escape_yaml(article.get("url", ""))}"',
            f'impacto: "{self._escape_yaml(article.get("impact_level", "low"))}"',
            f'score: {article.get("score", 0.0):.2f}',
            f'tags: [{tags_yaml}]' if tags_yaml else "tags: []",
            'tickers: []',
            'confianza_fuente: 1.0',
            f'urgencia: "{self._escape_yaml(article.get("urgency_level", "normal"))}"',
            f'priority_score: {article.get("priority_score", 0.0):.2f}',
            f'relevance_signals: [{signals_yaml}]' if signals_yaml else "relevance_signals: []",
            f'branch_targets: [{branches_yaml}]' if branches_yaml else "branch_targets: []",
            f'suggested_actions: [{actions_yaml}]' if actions_yaml else "suggested_actions: []",
            f'fingerprint: "{fingerprint}"',
            "---",
        ]

        summary = article.get("summary") or "Sin resumen disponible."
        snippet = article.get("snippet") or ""

        body_sections = [
            "",
            "# Resumen ejecutivo",
            textwrap.fill(summary, width=100),
            "",
            "## Detalles clave",
            textwrap.fill(snippet, width=100) if snippet else "Sin detalles adicionales.",
            "",
            "## Riesgos y catalizadores",
            "Revisar alertas asociadas en la corrida." if article.get("impact_level") in {"high", "medium"} else "No se identificaron riesgos adicionales.",
            "",
            "## Senales para distribucion",
        ]

        decision_lines: List[str] = []
        if signals:
            decision_lines.append(f"- Senales detectadas: {', '.join(signals)}")
        if branches:
            decision_lines.append(f"- Sucursales a monitorear: {', '.join(branches)}")
        if actions:
            for action in actions:
                decision_lines.append(f"- Accion sugerida: {action}")
        if not decision_lines:
            decision_lines.append("Sin senales destacadas para distribucion.")
        body_sections.extend(decision_lines)

        body_sections.extend([
            "",
            "## Metricas relevantes",
            f"- Puntaje interno: {article.get('score', 0.0):.2f}",
            f"- Prioridad analista: {article.get('priority_score', 0.0):.2f}",
            f"- Urgencia: {article.get('urgency_level', 'normal')}",
        ])
        if tags:
            body_sections.append(f"- Etiquetas: {', '.join(tags)}")

        body_sections.append("")
        return "\n".join(front_matter + body_sections)

    def _build_json_payload(
        self,
        article: Dict[str, Any],
        run_result: Dict[str, Any],
        fingerprint: str,
        md_path: Path,
        json_path: Path,
        published: datetime,
    ) -> Dict[str, Any]:
        return {
            "fingerprint": fingerprint,
            "headline": article.get("headline"),
            "url": article.get("url"),
            "published_at": published.isoformat(),
            "impact_level": article.get("impact_level"),
            "score": article.get("score"),
            "priority_score": article.get("priority_score"),
            "urgency_level": article.get("urgency_level"),
            "tags": article.get("tags", []),
            "relevance_signals": article.get("relevance_signals", []),
            "branch_targets": article.get("branch_targets", []),
            "suggested_actions": article.get("suggested_actions", []),
            "raw_keywords": article.get("raw_keywords", []),
            "summary": article.get("summary"),
            "snippet": article.get("snippet"),
            "source": article.get("source"),
            "run": {
                "generated_at": run_result.get("generated_at"),
                "trigger": run_result.get("trigger"),
                "requested_by": run_result.get("requested_by"),
                "metrics": run_result.get("metrics", {}),
                "alerts": run_result.get("alerts", []),
                "decision_summary": run_result.get("decision_summary", {}),
            },
            "files": {
                "markdown": str(md_path.relative_to(self.root)),
                "json": str(json_path.relative_to(self.root)),
            },
            "stored_at": datetime.utcnow().isoformat(),
        }

    def _append_daily_index(self, directory: Path, published: datetime, entry: Dict[str, Any]) -> None:
        index_path = directory / f"{published.year:04d}-{published.month:02d}-{published.day:02d}.index.jsonl"
        payload = {
            **entry,
            "written_at": datetime.utcnow().isoformat(),
        }
        with index_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _load_index(self) -> Dict[str, Any]:
        if not self.index_path.exists():
            return {}
        try:
            text = self.index_path.read_text(encoding="utf-8")
            return json.loads(text) if text.strip() else {}
        except Exception as exc:
            logger.warning("[capi_noticias] No se pudo leer index.json: %s", exc)
            return {}

    def _save_index(self, index: Dict[str, Any]) -> None:
        try:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            self.index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("[capi_noticias] No se pudo persistir index.json: %s", exc)

    def _escape_yaml(self, value: str) -> str:
        return value.replace('"', '\"')



class SegmentAggregator:
    """Genera segmentos diario/semanal/mensual para el siguiente agente analista."""

    def __init__(
        self,
        storage: "NoticiasStorage",
        runs_root: Path,
        segments_root: Optional[Path] = None,
        segment_config_provider: Optional[Callable[[], Dict[str, Any]]] = None,
    ) -> None:
        self.storage = storage
        self.runs_root = Path(runs_root)
        self.segments_root = Path(segments_root) if segments_root else self.runs_root.parent / "segments"
        self.segments_root.mkdir(parents=True, exist_ok=True)
        self._segment_config_provider = segment_config_provider or (
            lambda: {name: defaults.copy() for name, defaults in DEFAULT_SEGMENT_CONFIG.items()}
        )
        self._lock = threading.RLock()

    def update_segments(
        self,
        run_result: Dict[str, Any],
        saved_entries: List[Dict[str, Any]],
        index: Dict[str, Any],
    ) -> Dict[str, int]:
        articles = run_result.get("articles") or []
        generated_at = self._parse_datetime(run_result.get("generated_at")) or datetime.utcnow()
        summary: Dict[str, int] = {}
        saved_map = {
            entry.get("fingerprint"): entry for entry in saved_entries if entry.get("fingerprint")
        }

        with self._lock:
            segment_config = self._segment_config_provider()
            for timeframe, cfg in segment_config.items():
                data = self._load_segment(cfg["file"], timeframe)
                items = data.get("items", [])
                items = self._filter_old(items, generated_at, cfg)
                candidates = self._build_candidates(articles, saved_map, index, generated_at, cfg)
                items = self._merge_items(items, candidates, cfg)
                data["items"] = items
                data["updated_at"] = datetime.utcnow().isoformat()
                self._save_segment(cfg["file"], data)
                summary[timeframe] = len(items)
        return summary

    def _build_candidates(
        self,
        articles: List[Dict[str, Any]],
        saved_map: Dict[str, Dict[str, Any]],
        index: Dict[str, Any],
        generated_at: datetime,
        cfg: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        min_priority = cfg.get("min_priority", 0.0)
        candidates: List[Dict[str, Any]] = []
        for article in articles:
            priority = float(article.get("priority_score", 0.0) or 0.0)
            url = (article.get("url") or "").strip()
            if not url:
                continue
            published = self._parse_datetime(article.get("published_at")) or generated_at
            fingerprint = self.storage._compute_fingerprint(url, published)
            if priority >= min_priority:
                base = self._compose_segment_item(article, fingerprint, saved_map, index)
                if base:
                    candidates.append(base)

        fallback_min = cfg.get("fallback_min", 0)
        if len(candidates) < fallback_min and articles:
            extra_candidates: List[Dict[str, Any]] = []
            for article in articles:
                url = (article.get("url") or "").strip()
                if not url:
                    continue
                published = self._parse_datetime(article.get("published_at")) or generated_at
                fingerprint = self.storage._compute_fingerprint(url, published)
                base = self._compose_segment_item(article, fingerprint, saved_map, index)
                if base:
                    extra_candidates.append(base)
            extra_candidates.sort(key=lambda item: item["priority_score"], reverse=True)
            seen = {item.get("fingerprint") for item in candidates}
            for candidate in extra_candidates:
                fp = candidate.get("fingerprint")
                if fp and fp not in seen:
                    candidates.append(candidate)
                    seen.add(fp)
                if len(candidates) >= fallback_min:
                    break

        candidates.sort(key=lambda item: item["priority_score"], reverse=True)
        return candidates

    def _compose_segment_item(
        self,
        article: Dict[str, Any],
        fingerprint: str,
        saved_map: Dict[str, Dict[str, Any]],
        index: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not fingerprint:
            return None
        entry = saved_map.get(fingerprint) or index.get(fingerprint) or {}
        return {
            "fingerprint": fingerprint,
            "headline": article.get("headline"),
            "priority_score": float(article.get("priority_score", 0.0) or 0.0),
            "urgency_level": article.get("urgency_level", "normal"),
            "impact_level": article.get("impact_level", "low"),
            "relevance_signals": article.get("relevance_signals", []),
            "branch_targets": article.get("branch_targets", []),
            "suggested_actions": article.get("suggested_actions", []),
            "summary": article.get("summary"),
            "url": article.get("url"),
            "published_at": article.get("published_at"),
            "md_path": entry.get("md_path"),
            "json_path": entry.get("json_path"),
            "stored_at": datetime.utcnow().isoformat(),
        }

    def _merge_items(
        self,
        items: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]],
        cfg: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        registry = {item.get("fingerprint"): item for item in items if item.get("fingerprint")}
        for candidate in candidates:
            fingerprint = candidate.get("fingerprint")
            if not fingerprint:
                continue
            existing = registry.get(fingerprint)
            if not existing or candidate.get("priority_score", 0.0) > existing.get("priority_score", 0.0):
                registry[fingerprint] = candidate
        result = list(registry.values())
        result.sort(
            key=lambda item: (
                item.get("priority_score", 0.0),
                1 if item.get("urgency_level") == "high" else 0,
            ),
            reverse=True,
        )
        max_items = cfg.get("max_items", 50)
        return result[:max_items]

    def _filter_old(
        self,
        items: List[Dict[str, Any]],
        reference: datetime,
        cfg: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        horizon: Optional[datetime] = None
        if "lookback_hours" in cfg:
            horizon = reference - timedelta(hours=cfg["lookback_hours"])
        elif "lookback_days" in cfg:
            horizon = reference - timedelta(days=cfg["lookback_days"])
        if horizon is None:
            return items
        filtered: List[Dict[str, Any]] = []
        for item in items:
            published = self._parse_datetime(item.get("published_at"))
            stored = self._parse_datetime(item.get("stored_at"))
            marker = published or stored
            if marker is None or marker >= horizon:
                filtered.append(item)
        return filtered

    def _load_segment(self, file_name: str, timeframe: str) -> Dict[str, Any]:
        path = self.segments_root / file_name
        if not path.exists():
            return {
                "timeframe": timeframe,
                "items": [],
                "updated_at": datetime.utcnow().isoformat(),
            }
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("segment data must be dict")
        except Exception as exc:
            logger.warning("[capi_noticias] Segmento %s corrupto: %s", file_name, exc)
            return {
                "timeframe": timeframe,
                "items": [],
                "updated_at": datetime.utcnow().isoformat(),
            }
        data.setdefault("timeframe", timeframe)
        data.setdefault("items", [])
        return data

    def _save_segment(self, file_name: str, data: Dict[str, Any]) -> None:
        path = self.segments_root / file_name
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        value = value.strip()
        if not value:
            return None
        normalized = value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            try:
                dt = datetime.fromisoformat(normalized.split(".")[0])
            except ValueError:
                return None
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
class AmbitoNewsFetcher:
    """Obtiene noticias desde Ambito.com y normaliza resultados."""

    def __init__(self, timeout: float = REQUEST_TIMEOUT) -> None:
        self.timeout = timeout
        self.headers = {"User-Agent": USER_AGENT}

    def collect_articles(self, source_urls: Iterable[str], per_source_limit: int) -> List[NewsArticle]:
        articles: List[NewsArticle] = []
        seen: set[str] = set()

        with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
            for source_url in source_urls:
                try:
                    source_html = self._fetch(client, source_url)
                    candidate_urls = self._extract_article_urls(source_html, source_url)
                    logger.info(
                        "[capi_noticias] Encontradas %d urls potenciales en %s",
                        len(candidate_urls),
                        source_url,
                    )
                except Exception as exc:
                    logger.warning("[capi_noticias] No se pudo leer %s: %s", source_url, exc)
                    continue

                for article_url in candidate_urls[:per_source_limit]:
                    if not _is_allowed_domain(article_url):
                        continue
                    if article_url in seen:
                        continue
                    seen.add(article_url)
                    try:
                        article_html = self._fetch(client, article_url)
                        article = self._parse_article(article_html, article_url, source_url)
                        if article:
                            articles.append(article)
                    except Exception as exc:  # pragma: no cover - network issues
                        logger.warning(
                            "[capi_noticias] Error procesando articulo %s: %s",
                            article_url,
                            exc,
                        )
                        continue

        return articles

    def _fetch(self, client: httpx.Client, url: str) -> str:
        response = client.get(url)
        response.raise_for_status()
        return response.text

    def _extract_article_urls(self, html: str, base_url: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        urls: List[str] = []

        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "{}")
            except json.JSONDecodeError:
                continue

            for item in self._iterate_jsonld(data):
                if isinstance(item, dict) and item.get("@type") in {"CollectionPage", "ItemList"}:
                    elements = []
                    if "itemListElement" in item:
                        elements = item["itemListElement"]
                    elif "mainEntity" in item and isinstance(item["mainEntity"], dict):
                        elements = item["mainEntity"].get("itemListElement", [])

                    for entry in elements:
                        url = None
                        if isinstance(entry, dict):
                            url = entry.get("url") or (entry.get("item") or {}).get("@id")
                        if url:
                            candidate = urljoin(base_url, url)
                            if _is_allowed_domain(candidate):
                                urls.append(candidate)

        # Fallback: buscar anchors en tarjetas de noticias
        if not urls:
            for anchor in soup.select("article a"):
                href = anchor.get("href")
                if href and href.startswith("/"):
                    candidate = urljoin(base_url, href)
                    if _is_allowed_domain(candidate):
                        urls.append(candidate)

        # Deduplicar manteniendo orden
        seen: set[str] = set()
        unique_urls = []
        for url in urls:
            if url not in seen and url.startswith("http") and _is_allowed_domain(url):
                unique_urls.append(url)
                seen.add(url)
        return unique_urls

    def _parse_article(self, html: str, url: str, source_url: str) -> Optional[NewsArticle]:
        soup = BeautifulSoup(html, "html.parser")
        article_data: Optional[Dict[str, Any]] = None

        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "{}")
            except json.JSONDecodeError:
                continue

            for item in self._iterate_jsonld(data):
                if isinstance(item, dict) and item.get("@type") in {"NewsArticle", "Article"}:
                    article_data = item
                    break
            if article_data:
                break

        headline = article_data.get("headline") if article_data else None
        if not headline:
            title_tag = soup.find("h1")
            headline = title_tag.get_text(strip=True) if title_tag else "Sin ttulo"

        description = article_data.get("description") if article_data else ""
        keywords_raw = article_data.get("keywords") if article_data else []
        if isinstance(keywords_raw, str):
            raw_keywords = [kw.strip() for kw in keywords_raw.split(",") if kw.strip()]
        elif isinstance(keywords_raw, list):
            raw_keywords = [str(kw).strip() for kw in keywords_raw if str(kw).strip()]
        else:
            raw_keywords = []

        published_at = None
        if article_data:
            for key in ("datePublished", "dateCreated", "uploadDate"):
                if article_data.get(key):
                    try:
                        published_at = datetime.fromisoformat(article_data[key].replace("Z", "+00:00"))
                        break
                    except ValueError:
                        continue

        body = article_data.get("articleBody") if article_data else None
        if not body:
            body_tag = soup.find("div", class_=re.compile("article__body|note-body|content-body"))
            if body_tag:
                body = body_tag.get_text(" ", strip=True)

        snippet_source = body or description or ""
        snippet = snippet_source.strip().replace("\n", " ")[:320]

        return NewsArticle(
            url=url,
            headline=headline.strip(),
            summary=(description or "").strip(),
            published_at=published_at,
            source=source_url,
            score=0.0,
            raw_keywords=raw_keywords,
            snippet=snippet,
        )

    def _iterate_jsonld(self, data: Any):
        if isinstance(data, dict):
            yield data
            for value in data.values():
                yield from self._iterate_jsonld(value)
        elif isinstance(data, list):
            for item in data:
                yield from self._iterate_jsonld(item)


class FinancialNewsAnalyzer:
    """Evala la relevancia financiera de cada noticia."""

    KEYWORD_GROUPS: Dict[str, List[str]] = {
        "cash_operations": [
            "retiro",
            "retiros",
            "extraccion",
            "extraccin",
            "ventanilla",
            "cajero",
            "cajeros",
            "efectivo",
            "billetes",
            "caja",
        ],
        "liquidity": [
            "liquidez",
            "reservas",
            "plazo fijo",
            "plazos fijos",
            "deposito",
            "depsito",
            "depositos",
            "depsitos",
            "fondos",
            "capital",
        ],
        "branch_activity": [
            "sucursal",
            "sucursales",
            "agencia",
            "agencias",
            "bancaria",
            "bancarias",
            "filial",
            "filiales",
        ],
        "risk_alerts": [
            "corrida",
            "corralito",
            "restriccin",
            "restriccion",
            "limite",
            "limitar",
            "tope",
            "crisis",
            "default",
            "alerta",
        ],
        "regulation": [
            "bcra",
            "banco central",
            "norma",
            "resolucin",
            "resolucion",
            "ley",
            "decreto",
            "regulacin",
            "regulacion",
        ],
    }

    GROUP_WEIGHTS: Dict[str, float] = {
        "cash_operations": 2.5,
        "liquidity": 2.0,
        "branch_activity": 1.5,
        "risk_alerts": 3.0,
        "regulation": 1.2,
    }

    RELEVANCE_MAPPING: Dict[str, str] = {
        "cash_operations": "cash_pressure",
        "liquidity": "liquidity_risk",
        "branch_activity": "branch_operations",
        "risk_alerts": "systemic_risk",
        "regulation": "policy_change",
    }

    URGENCY_KEYWORDS: Dict[str, List[str]] = {
        "high": ["corrida", "corralito", "restriccion", "restricci", "paro bancario", "emergencia"],
        "medium": ["alerta", "limitacion", "temor", "tension"],
    }

    BRANCH_KEYWORDS: Dict[str, List[str]] = {
        "caba": ["caba", "buenos aires", "capital federal", "amba"],
        "cordoba": ["cordoba"],
        "rosario": ["rosario", "santa fe"],
        "mendoza": ["mendoza"],
        "tucuman": ["tucuman"],
    }

    BRANCH_LABELS: Dict[str, str] = {
        "caba": "Sucursal CABA - Casa Central",
        "cordoba": "Sucursal Cordoba Centro",
        "rosario": "Sucursal Rosario",
        "mendoza": "Sucursal Mendoza",
        "tucuman": "Sucursal Tucuman",
    }

    ACTION_SUGGESTIONS: Dict[str, str] = {
        "cash_pressure": "Refuerza stock de efectivo y monitorea retiros en sucursales afectadas.",
        "liquidity_risk": "Revisa proyecciones de liquidez y prepara escenarios de stress.",
        "branch_operations": "Coordina soporte operativo y horarios extendidos si crece la demanda.",
        "systemic_risk": "Escala a risk management y prepara comunicacion con clientes clave.",
        "policy_change": "Evalua impacto regulatorio con cumplimiento y ajusta comunicados internos.",
    }

    def score_article(self, article: NewsArticle) -> NewsArticle:
        text = " ".join(filter(None, [article.headline, article.summary, article.snippet])).lower()
        normalized = self._normalize_text(text)
        tags = set(article.tags or [])
        total_score = 0.0

        for group, keywords in self.KEYWORD_GROUPS.items():
            count = 0
            for keyword in keywords:
                pattern = re.compile(rf"\b{re.escape(keyword)}\b")
                count += len(pattern.findall(normalized))
            if count:
                total_score += count * self.GROUP_WEIGHTS.get(group, 1.0)
                tags.add(group)

        for kw in article.raw_keywords:
            normalized_kw = self._normalize_text(kw)
            for group, keywords in self.KEYWORD_GROUPS.items():
                if normalized_kw in keywords:
                    total_score += 0.5
                    tags.add(group)

        impact_level = "low"
        if total_score >= 6:
            impact_level = "high"
        elif total_score >= 3:
            impact_level = "medium"

        relevance_signals = {self.RELEVANCE_MAPPING[tag] for tag in tags if tag in self.RELEVANCE_MAPPING}

        urgency = "normal"
        for keyword in self.URGENCY_KEYWORDS.get("high", []):
            if keyword in normalized:
                urgency = "high"
                break
        if urgency == "normal":
            for keyword in self.URGENCY_KEYWORDS.get("medium", []):
                if keyword in normalized:
                    urgency = "medium"
                    break

        branch_targets = set()
        for branch_key, variants in self.BRANCH_KEYWORDS.items():
            if any(variant in normalized for variant in variants):
                label = self.BRANCH_LABELS.get(branch_key, branch_key.title())
                branch_targets.add(label)

        if urgency == "high":
            relevance_signals.add("systemic_risk")

        suggested_actions = []
        for signal in sorted(relevance_signals):
            action = self.ACTION_SUGGESTIONS.get(signal)
            if action and action not in suggested_actions:
                suggested_actions.append(action)

        if not suggested_actions:
            if impact_level == "high":
                suggested_actions.append("Escala a risk management para evaluar medidas de contencion.")
            elif impact_level == "medium":
                suggested_actions.append("Monitorea flujo de efectivo y comunica hallazgos al equipo regional.")

        published = article.published_at
        if published is not None and published.tzinfo is not None:
            published = published.astimezone(timezone.utc).replace(tzinfo=None)
        hours_since = 12.0
        now_utc = datetime.utcnow()
        if published:
            delta = now_utc - published
            hours_since = max(0.0, delta.total_seconds() / 3600.0)

        if hours_since <= 3:
            freshness = 1.4
        elif hours_since <= 12:
            freshness = 1.2
        elif hours_since <= 24:
            freshness = 1.0
        else:
            freshness = 0.7

        urgency_bonus = {"high": 1.5, "medium": 0.9, "normal": 0.4}.get(urgency, 0.4)
        priority_score = round((total_score * freshness) + urgency_bonus, 2)

        article.score = total_score
        article.tags = sorted(tags)
        article.impact_level = impact_level
        article.relevance_signals = sorted(relevance_signals)
        article.branch_targets = sorted(branch_targets)
        article.urgency_level = urgency
        article.suggested_actions = suggested_actions
        article.priority_score = priority_score
        return article

    def build_analysis(self, articles: List[NewsArticle]) -> Dict[str, Any]:
        if not articles:
            return {
                "articles": [],
                "alerts": [],
                "metrics": {
                    "total_articles": 0,
                    "high_impact": 0,
                    "medium_impact": 0,
                    "low_impact": 0,
                    "tags": {},
                    "signals": {},
                    "priority_high": 0,
                    "priority_medium": 0,
                    "priority_low": 0,
                    "average_priority": 0.0,
                    "max_priority": 0.0,
                },
                "summary": {
                    "headline": "Sin noticias relevantes",
                    "detail": "No se encontraron novedades financieras en las fuentes monitoreadas.",
                },
                "decision_summary": {
                    "high_priority": 0,
                    "medium_priority": 0,
                    "recommended_actions": [],
                    "branches_to_monitor": [],
                },
                "generated_at": datetime.utcnow().isoformat(),
            }

        scored = [self.score_article(article) for article in articles]
        high = [a for a in scored if a.impact_level == "high"]
        medium = [a for a in scored if a.impact_level == "medium"]
        low = [a for a in scored if a.impact_level == "low"]

        sorted_candidates = sorted(high + medium, key=lambda item: (item.priority_score, item.score), reverse=True)
        alerts = [
            {
                "headline": a.headline,
                "url": a.url,
                "impact_level": a.impact_level,
                "score": round(a.score, 2),
                "priority_score": a.priority_score,
                "tags": a.tags,
                "relevance_signals": a.relevance_signals,
                "branch_targets": a.branch_targets,
                "urgency_level": a.urgency_level,
                "suggested_actions": a.suggested_actions,
                "published_at": a.published_at.isoformat() if a.published_at else None,
            }
            for a in sorted_candidates[:5]
        ]

        tag_counter: Counter[str] = Counter()
        signal_counter: Counter[str] = Counter()
        for article in scored:
            tag_counter.update(article.tags)
            signal_counter.update(article.relevance_signals)

        priority_high = [a for a in scored if a.priority_score >= 7.0]
        priority_medium = [a for a in scored if 4.0 <= a.priority_score < 7.0]
        priority_low = [a for a in scored if a.priority_score < 4.0]

        average_priority = round(sum(a.priority_score for a in scored) / len(scored), 2) if scored else 0.0
        max_priority = max((a.priority_score for a in scored), default=0.0)

        summary = self._render_summary(len(scored), len(high), len(medium), alerts, priority_high)

        recommended_actions = sorted({action for article in priority_high + priority_medium for action in article.suggested_actions})
        branches_to_monitor = sorted({branch for article in priority_high for branch in article.branch_targets})
        decision_summary = {
            "high_priority": len(priority_high),
            "medium_priority": len(priority_medium),
            "recommended_actions": recommended_actions,
            "branches_to_monitor": branches_to_monitor,
        }
        if priority_high:
            decision_summary["top_headline"] = priority_high[0].headline
            decision_summary["top_priority_score"] = priority_high[0].priority_score

        return {
            "articles": [a.to_dict() for a in scored],
            "alerts": alerts,
            "metrics": {
                "total_articles": len(scored),
                "high_impact": len(high),
                "medium_impact": len(medium),
                "low_impact": len(low),
                "tags": dict(tag_counter.most_common()),
                "signals": dict(signal_counter.most_common()),
                "priority_high": len(priority_high),
                "priority_medium": len(priority_medium),
                "priority_low": len(priority_low),
                "average_priority": average_priority,
                "max_priority": max_priority,
            },
            "summary": summary,
            "decision_summary": decision_summary,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _render_summary(self, total: int, high: int, medium: int, alerts: List[Dict[str, Any]], priority_high: List[NewsArticle]) -> Dict[str, str]:
        if not total:
            return {
                "headline": "Sin noticias relevantes",
                "detail": "No se encontraron novedades financieras en las fuentes monitoreadas.",
            }

        headline = f"{total} noticias analizadas | {high} altas, {medium} medias"
        if alerts:
            top = alerts[0]
            detail = (
                f"Prioridad {top['urgency_level']} - {top['headline']} (priority {top['priority_score']})."
            )
        else:
            detail = "No se detectaron alertas criticas; continuar monitoreando."

        if priority_high:
            top_article = priority_high[0]
            detail += f" Enfocar recursos en {top_article.headline} (score {top_article.priority_score})."

        return {"headline": headline, "detail": detail}

    def _normalize_text(self, text: str) -> str:
        import unicodedata
        normalized = unicodedata.normalize('NFKD', text.lower())
        return ''.join(ch for ch in normalized if not unicodedata.combining(ch))


class CapiNoticiasAgent(BaseAgent):
    """Agente encargado de monitorear noticias financieras."""

    AGENT_NAME = "capi_noticias"
    DISPLAY_NAME = "Capi Noticias"
    VERSION = "1.0.0"
    SUPPORTED_INTENTS = ["news_monitoring", "news_report"]

    def __init__(self) -> None:
        super().__init__(self.AGENT_NAME)
        self.config_manager = CapiNoticiasConfigManager()
        self.storage = NoticiasStorage(
            self.config_manager.runs_dir,
            self.config_manager.segments_dir,
            self.config_manager.get_segment_config,
        )
        self.fetcher = AmbitoNewsFetcher()
        self.analyzer = FinancialNewsAnalyzer()

    @property
    def supported_intents(self) -> List[IntentType]:
        return [getattr(IntentType, "NEWS_MONITORING", IntentType.UNKNOWN)]

    async def process(self, task: AgentTask) -> AgentResult:
        params = task.metadata or {}
        trigger = params.get("trigger") or "manual"
        source_override = params.get("source_urls")
        per_source = params.get("max_articles_per_source")

        agent_progress.start(
            self.AGENT_NAME,
            task.session_id,
            query=task.query,
            extra={'trigger': trigger}
        )

        try:
            result = self.run_cycle(
                trigger=trigger,
                source_override=source_override,
                per_source_override=per_source,
                requested_by=task.user_id,
            )
            summary = result.get("summary", {})
            message = summary.get("headline") or "Monitoreo de noticias completado"

            agent_progress.success(
                self.AGENT_NAME,
                task.session_id,
                detail=message,
                extra={'articles': len(result.get('articles', [])), 'trigger': trigger}
            )

            return AgentResult(
                success=True,
                data=result,
                message=message,
                metadata={"agent": self.AGENT_NAME, "trigger": trigger},
            )
        except Exception as exc:
            logger.exception("[capi_noticias] Error ejecutando agente: %s", exc)
            self.config_manager.record_run(
                trigger=trigger,
                success=False,
                result={"articles": []},
                error_message=str(exc),
                next_run=datetime.utcnow() + timedelta(minutes=DEFAULT_INTERVAL_MINUTES),
            )

            agent_progress.error(
                self.AGENT_NAME,
                task.session_id,
                detail=str(exc),
                extra={'trigger': trigger}
            )

            return AgentResult(
                success=False,
                data={"error": str(exc)},
                message="No se pudo completar el monitoreo de noticias",
            )

    def run_cycle(
        self,
        *,
        trigger: str,
        source_override: Optional[Iterable[str]] = None,
        per_source_override: Optional[int] = None,
        requested_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        config = self.config_manager.load_config()
        if not config.get("enabled", True) and trigger != "manual":
            raise AgentError("El agente Capi Noticias est deshabilitado")

        source_urls = self._sanitize_urls(source_override or config.get("source_urls", DEFAULT_SOURCES))
        if not source_urls:
            raise AgentError("No hay fuentes configuradas para Capi Noticias")

        per_source = max(1, per_source_override or config.get("max_articles_per_source", MAX_ARTICLES_PER_SOURCE))

        next_run = datetime.utcnow() + timedelta(minutes=config.get("interval_minutes", DEFAULT_INTERVAL_MINUTES))
        self.config_manager.mark_running(trigger, next_run)

        articles = self.fetcher.collect_articles(source_urls, per_source)
        analysis = self.analyzer.build_analysis(articles)

        metrics = dict(analysis.get("metrics", {}))
        token_usage = self._estimate_token_usage(analysis.get("articles", []))
        metrics.update(token_usage)

        payload = {
            "generated_at": analysis.get("generated_at"),
            "trigger": trigger,
            "requested_by": requested_by,
            "source_urls": source_urls,
            "articles": analysis.get("articles", []),
            "alerts": analysis.get("alerts", []),
            "metrics": metrics,
            "summary": analysis.get("summary", {}),
            "decision_summary": analysis.get("decision_summary", {}),
        }

        try:
            storage_result = self.storage.persist_run(payload)
            logger.info(
                {"event": "capi_noticias_persisted", "saved": len(storage_result.get("saved", [])), "skipped": len(storage_result.get("skipped", []))}
            )
        except Exception as exc:  # pragma: no cover - persist defensive
            logger.exception("[capi_noticias] Error persistiendo resultados: %s", exc)
            segments = {name: 0 for name in self.config_manager.get_segment_config().keys()}
            storage_result = {
                "saved": [],
                "skipped": [],
                "errors": [{"reason": str(exc)}],
                "root": str(getattr(self.storage, "root", self.config_manager.runs_dir)),
                "segments": segments,
            }
        payload["storage"] = storage_result

        self.config_manager.record_run(
            trigger=trigger,
            success=True,
            result=payload,
            error_message=None,
            next_run=next_run,
        )

        return payload

    def _estimate_token_usage(self, articles: List[Dict[str, Any]]) -> Dict[str, float]:
        total_tokens = 0
        for article in articles or []:
            summary = article.get("summary") or ""
            snippet = article.get("snippet") or ""
            total_chars = len(summary) + len(snippet)
            if total_chars:
                total_tokens += max(1, total_chars // CHARS_PER_TOKEN)
        estimated_cost = round((total_tokens / 1000) * USD_PER_1K_TOKENS, 6) if total_tokens else 0.0
        return {"estimated_tokens": int(total_tokens), "estimated_cost_usd": estimated_cost}

    def _sanitize_urls(self, urls: Iterable[str]) -> List[str]:
        clean_urls = []
        for url in urls:
            if not isinstance(url, str):
                continue
            url = url.strip()
            if url.startswith("http") and _is_allowed_domain(url):
                clean_urls.append(url)
        return clean_urls
