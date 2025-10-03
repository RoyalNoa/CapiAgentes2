#!/usr/bin/env python3
"""
CapiAgentes Docker Manager - Interfaz profesional para controlar servicios Docker.
Rediseno con foco en consistencia visual, accesibilidad y control granular.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Literal, Optional, Sequence, Tuple

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
    SOURCE_ROOT = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
    LOG_DIR = PROJECT_ROOT / "logs"
else:
    SOURCE_ROOT = Path(__file__).resolve().parent.parent.parent
    PROJECT_ROOT = SOURCE_ROOT.parent
    LOG_DIR = SOURCE_ROOT / "logs"

DEBUG_LOG = LOG_DIR / "launcher_debug.log"
ASSETS_DIR = SOURCE_ROOT / "assets"



if LOG_DIR != PROJECT_ROOT / "logs":
    legacy_dir = PROJECT_ROOT / "logs"
    if legacy_dir.exists() and legacy_dir != LOG_DIR:
        for legacy_file in legacy_dir.glob("launcher_debug.log"):
            try:
                LOG_DIR.mkdir(parents=True, exist_ok=True)
                migrated = LOG_DIR / legacy_file.name
                if not migrated.exists():
                    legacy_file.replace(migrated)
            except OSError:
                pass
        try:
            next(legacy_dir.iterdir())
        except StopIteration:
            try:
                legacy_dir.rmdir()
            except OSError:
                pass

LOG_SCAN_DIRECTORIES: Tuple[Tuple[str, Path], ...] = (
    ("Backend", PROJECT_ROOT / "Backend" / "logs"),
    ("Servicios", LOG_DIR),
)

DEFAULT_LOG_SOURCES: Tuple[Tuple[str, Path], ...] = (
    ("Backend unificado", PROJECT_ROOT / "Backend" / "logs" / "capi.log"),
)

FILE_LOG_TAIL_LINES = 400


def _format_log_label(prefix: str, log_path: Path) -> str:
    stem = log_path.stem.replace("_", " ").strip()
    if not stem:
        stem = log_path.name
    display = stem.title()
    return f"{prefix} • {display}"


def discover_log_sources() -> List[Tuple[str, Path]]:
    sources: List[Tuple[str, Path]] = []
    seen: set[Path] = set()
    debug_log_resolved = DEBUG_LOG.resolve()
    for label, log_path in DEFAULT_LOG_SOURCES:
        try:
            resolved = log_path.resolve()
        except OSError:
            resolved = log_path
        if resolved == debug_log_resolved:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        sources.append((label, log_path))
    for prefix, directory in LOG_SCAN_DIRECTORIES:
        if not directory.exists():
            continue
        for log_path in sorted(directory.glob("*.log")):
            try:
                resolved = log_path.resolve()
            except OSError:
                resolved = log_path
            if resolved == debug_log_resolved or resolved in seen:
                continue
            seen.add(resolved)
            sources.append((_format_log_label(prefix, log_path), log_path))
    return sources



def tail_file(path: Path, max_lines: int = FILE_LOG_TAIL_LINES) -> str:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        if max_lines > 0:
            return "".join(deque(handle, maxlen=max_lines))
        return handle.read()


def resolve_asset(name: str) -> Path:
    candidates = [
        SOURCE_ROOT / "assets" / name,
        PROJECT_ROOT / "launcher" / "assets" / name,
        PROJECT_ROOT / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]



def log_debug(message: str) -> None:
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        with DEBUG_LOG.open("a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


TOKENS: Dict[str, str] = {
    "bg": "#0B0C0F",
    "surface": "#111317",
    "surface_alt": "#16181D",
    "border": "#1F232A",
    "border_strong": "#2A303A",
    "text": "#ECEFF4",
    "text_dim": "#8D929B",
    "accent": "#9AA0B6",
    "accent_alt": "#7F8598",
    "success": "#6F8F7A",
    "warn": "#A8956A",
    "danger": "#9A6F6B",
    "danger_bg": "#1E1919",
    "badge_bg": "#16181D",
    "glow": "#ADB3C8",
    "status_green": "#6F8F7A",
    "status_yellow": "#A8956A",
    "status_red": "#9A6F6B",
    "status_pulse": "#ADB3C8",
}

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
}

TRANSITION_MS = 140
CARD_MIN_WIDTH = 320
DEFAULT_WINDOW = (1200, 720)
REFRESH_INTERVAL_SECONDS = 30
LOG_TAIL_LINES = 200



class NeonPanel(tk.Frame):
    def __init__(
        self,
        master: tk.Widget,
        *,
        padding: Tuple[int, int] = (SPACING["md"], SPACING["md"]),
        border_color: Optional[str] = None,
        glow_color: Optional[str] = None,
        show_accent: bool = False,
    ) -> None:
        border = border_color or TOKENS["border"]
        glow = glow_color or TOKENS["accent"]
        super().__init__(
            master,
            bg=TOKENS["surface"],
            highlightbackground=border,
            highlightcolor=border,
            highlightthickness=1,
            bd=0,
        )
        self._accent_bar: Optional[tk.Frame] = None
        if show_accent:
            self._accent_bar = tk.Frame(self, bg=glow, height=2)
            self._accent_bar.pack(side="top", fill="x")
        padx, pady = padding
        self.container = tk.Frame(self, bg=TOKENS["surface"])
        self.container.pack(fill="both", expand=True, padx=padx, pady=pady)

    def clear(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()


SERVICE_STATUS_VARIANTS = {

    "UP": {

        "bg": "#1B221D",

        "fg": TOKENS["status_green"],

        "border": TOKENS["status_green"],

        "label": "EN LÍNEA",

        "light": TOKENS["status_green"],

    },

    "DETENIDO": {

        "bg": "#221B1B",

        "fg": TOKENS["status_red"],

        "border": TOKENS["status_red"],

        "label": "DETENIDO",

        "light": TOKENS["status_red"],

    },

    "EXITED": {

        "bg": "#221B1B",

        "fg": TOKENS["status_red"],

        "border": TOKENS["status_red"],

        "label": "ERROR",

        "light": TOKENS["status_red"],

    },

    "RESTARTING": {

        "bg": "#221F17",

        "fg": TOKENS["status_yellow"],

        "border": TOKENS["status_yellow"],

        "label": "INICIANDO...",

        "light": TOKENS["status_yellow"],

    },

    "DESCONOCIDO": {

        "bg": TOKENS["surface_alt"],

        "fg": TOKENS["text_dim"],

        "border": TOKENS["border"],

        "label": "DESCONOCIDO",

        "light": TOKENS["text_dim"],

    },

}





BUILDABLE_SERVICE_IDS = {"backend", "frontend"}





ACTION_STYLE = {
    "start": {
        "bg": TOKENS["surface_alt"],
        "fg": TOKENS["text"],
        "border": TOKENS["border"],
        "hover": TOKENS["status_green"],
        "hover_bg": "#1E2621",
    },
    "stop": {
        "bg": TOKENS["surface_alt"],
        "fg": TOKENS["text"],
        "border": TOKENS["border"],
        "hover": TOKENS["status_red"],
        "hover_bg": "#262021",
    },
    "restart": {
        "bg": TOKENS["surface_alt"],
        "fg": TOKENS["text"],
        "border": TOKENS["border"],
        "hover": TOKENS["accent"],
        "hover_bg": "#1E2229",
    },
    "build": {
        "bg": TOKENS["surface_alt"],
        "fg": TOKENS["text"],
        "border": TOKENS["border"],
        "hover": TOKENS["accent"],
        "hover_bg": "#1E2229",
    },
    "danger": {
        "bg": TOKENS["surface_alt"],
        "fg": TOKENS["text"],
        "border": TOKENS["border"],
        "hover": TOKENS["status_red"],
        "hover_bg": "#262021",
    },
    "accent": {
        "bg": TOKENS["surface_alt"],
        "fg": TOKENS["text"],
        "border": TOKENS["border"],
        "hover": TOKENS["accent"],
        "hover_bg": "#1E2229",
    },
    "ghost": {
        "bg": TOKENS["surface"],
        "fg": TOKENS["text_dim"],
        "border": TOKENS["border"],
        "hover": TOKENS["accent"],
        "hover_bg": TOKENS["surface_alt"],
    },
    "launch": {
        "bg": TOKENS["surface_alt"],
        "fg": TOKENS["text"],
        "border": TOKENS["border"],
        "hover": TOKENS["status_green"],
        "hover_bg": "#1E2621",
    },
}



ICON_GLYPHS = {
    "toggle_on": "■",
    "toggle_off": "▶",
    "restart": "↻",
    "logs": "🗒",
    "build": "🛠",
    "refresh": "↻",
    "trash": "🗑",
    "success": "✔",
    "warn": "⚠",
    "danger": "!",
}



def blend_hex(foreground: str, background: str, alpha: float) -> str:
    foreground = foreground.lstrip("#")
    background = background.lstrip("#")
    fr, fg_, fb = int(foreground[0:2], 16), int(foreground[2:4], 16), int(foreground[4:6], 16)
    br, bg_, bb = int(background[0:2], 16), int(background[2:4], 16), int(background[4:6], 16)
    rr = round(fr * alpha + br * (1 - alpha))
    gg = round(fg_ * alpha + bg_ * (1 - alpha))
    bb_ = round(fb * alpha + bb * (1 - alpha))
    return f"#{rr:02x}{gg:02x}{bb_:02x}".upper()


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def parse_iso_timestamp(value: str) -> Optional[datetime]:
    if not value:
        return None

    value = value.strip()
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        if "." in value:
            main, frac_part = value.split(".", 1)
            tz_offset = ""
            match = re.search(r"[+-]\d{2}:?\d{2}$", frac_part)
            if match:
                tz_offset = match.group(0)
                frac_part = frac_part[: -len(tz_offset)]
            if len(frac_part) > 6:
                frac_part = frac_part[:6]
            frac_part = frac_part.rstrip("Z")
            value = f"{main}.{frac_part}{tz_offset}" if frac_part else f"{main}{tz_offset}"
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class ServiceDefinition:
    service_id: str
    name: str
    role: str
    port: Optional[int] = None
    url: Optional[str] = None
    compose_name: Optional[str] = None
    compose_file: Optional[Path] = None
    kind: Optional[str] = None


@dataclass
class ServiceRuntime:
    status: str = "DETENIDO"
    uptime_seconds: int = 0
    restarts: int = 0
    container_id: Optional[str] = None
    last_seen: float = 0.0
    error: Optional[str] = None


@dataclass
class ServiceViewModel:
    definition: ServiceDefinition
    runtime: ServiceRuntime

    @property
    def status(self) -> str:
        return self.runtime.status

    @property
    def uptime_secs(self) -> int:
        return self.runtime.uptime_seconds

    @property
    def restarts(self) -> int:
        return self.runtime.restarts

    @property
    def url(self) -> Optional[str]:
        return self.definition.url

    @property
    def display_name(self) -> str:
        return self.definition.name

    @property
    def role(self) -> str:
        return self.definition.role

    @property
    def port(self) -> Optional[int]:
        return self.definition.port

    @property
    def compose_name(self) -> Optional[str]:
        return self.definition.compose_name


@dataclass
class DashboardState:
    services: List[ServiceViewModel] = field(default_factory=list)
    is_loading: bool = True
    error: Optional[str] = None
    last_updated: Optional[float] = None
    status_message: str = ""


def load_service_definitions(repo_root: Path) -> List[ServiceDefinition]:
    defaults = [
        ServiceDefinition(
            service_id="postgres",
            name="Base de Datos PostgreSQL",
            role="Base de datos",
            port=5432,
            compose_name="postgres",
        ),
        ServiceDefinition(
            service_id="backend",
            name="Backend API",
            role="Servicios REST",
            port=8000,
            url="http://localhost:8000/docs",
            compose_name="backend",
        ),
        ServiceDefinition(
            service_id="frontend",
            name="Frontend Web",
            role="Interfaz web",
            port=3000,
            url="http://localhost:3000",
            compose_name="frontend",
        ),
        ServiceDefinition(
            service_id="elastic_observability",
            name="Elastic Observability",
            role="Stack de logs y metricas",
            port=5601,
            url="http://localhost:5601",
            compose_name="kibana",
            compose_file=repo_root / "observability" / "docker-compose.elastic.yml",
            kind="elastic-stack",
        ),
    ]

    config_path = repo_root / "Backend" / "config" / "docker_services.json"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            for item in data:
                defaults.append(
                    ServiceDefinition(
                        service_id=item.get("service_id", item.get("name", "")),
                        name=item.get("name", "Servicio desconocido"),
                        role=item.get("role", item.get("type", "Agente")),
                        port=item.get("port"),
                        url=item.get("url"),
                        compose_name=item.get("compose_name"),
                        compose_file=(repo_root / Path(item["compose_file"])).resolve() if item.get("compose_file") else None,
                        kind=item.get("kind"),
                    )
                )
        except (json.JSONDecodeError, OSError):
            pass

    unique = {}
    for service in defaults:
        unique[service.service_id] = service
    return list(unique.values())


class DockerCommandError(RuntimeError):
    """Error personalizado para operaciones Docker."""



class DockerClient:
    def __init__(self, compose_file: Optional[Path], *, default_workdir: Optional[Path] = None) -> None:
        self.compose_file = compose_file if compose_file and compose_file.exists() else None
        self.workdir = self.compose_file.parent if self.compose_file else (default_workdir or Path.cwd())
        self._compose_cmd: List[str] = ["docker", "compose"]

    def _compose_base(self) -> List[str]:
        base = list(self._compose_cmd)
        if self.compose_file:
            base.extend(["-f", str(self.compose_file)])
        return base

    def _execute(
        self,
        args: List[str],
        *,
        compose: bool = True,
        check: bool = True,
        stream: bool = False,
    ) -> subprocess.CompletedProcess:
        cmd = self._compose_base() + args if compose else ["docker"] + args
        creationflags = 0
        if not stream and os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.workdir,
                capture_output=not stream,
                text=not stream,
                check=False,
                encoding="utf-8" if not stream else None,
                creationflags=creationflags,
            )
        except FileNotFoundError as exc:
            raise DockerCommandError("Docker no esta instalado o no se encuentra en PATH") from exc

        if compose and proc.returncode != 0:
            message = (proc.stderr or proc.stdout or "").strip().lower()
            unknown_compose = any(
                token in message
                for token in (
                    "unknown command","no such command","is not a docker command","no help topic for compose"
                )
            )
            if unknown_compose and self._compose_cmd != ["docker-compose"]:
                self._compose_cmd = ["docker-compose"]
                return self._execute(args, compose=True, check=check, stream=stream)

        if check and proc.returncode != 0:
            stderr = proc.stderr if not stream else ""
            stdout = proc.stdout if not stream else ""
            message = stderr.strip() or stdout.strip() or "Comando docker fallo"
            raise DockerCommandError(message)
        return proc

    def _collect_output(self, proc: subprocess.CompletedProcess) -> str:
        stdout = (proc.stdout or "").strip() if hasattr(proc, "stdout") else ""
        stderr = (proc.stderr or "").strip() if hasattr(proc, "stderr") else ""
        if stdout and stderr:
            return f"{stdout}\n{stderr}"
        return stdout or stderr

    def fetch_runtime(self, definitions: List[ServiceDefinition]) -> Tuple[Dict[str, Optional[ServiceRuntime]], Optional[str]]:
        errors: List[str] = []

        def parse_line_json(output: str) -> List[Dict[str, str]]:
            entries: List[Dict[str, str]] = []
            for raw in output.splitlines():
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(data, dict):
                    entries.append({k: (v or "") for k, v in data.items()})
            return entries

        def parse_compose_json(output: str) -> List[Dict[str, str]]:
            try:
                data = json.loads(output or "[]")
            except json.JSONDecodeError:
                return []
            if isinstance(data, dict):
                data = data.get("results") or data.get("services") or []
            if not isinstance(data, list):
                return []
            entries: List[Dict[str, str]] = []
            for item in data:
                if isinstance(item, dict):
                    entries.append({k: (v or "") for k, v in item.items()})
            return entries

        def normalise_candidates(raw: List[str]) -> List[str]:
            candidates: List[str] = []
            for value in raw:
                value = (value or "").strip()
                if not value:
                    continue
                primary = value.split(",")[0].strip()
                primary = primary.split("/")[-1]
                base = re.sub(r"([_-]\d+)$", "", primary)
                for option in {value, primary, base}:
                    option = option.strip()
                    if option:
                        candidates.append(option)
                if "_" in base:
                    pieces = [p for p in base.split("_") if p]
                    if len(pieces) >= 2:
                        candidates.append(pieces[-1])
                if "-" in base:
                    pieces = [p for p in base.split("-") if p]
                    if len(pieces) >= 2:
                        candidates.append(pieces[-1])
            ordered: List[str] = []
            seen: set[str] = set()
            for candidate in candidates:
                lowered = candidate.lower()
                if lowered not in seen:
                    ordered.append(lowered)
                    seen.add(lowered)
            return ordered

        def collect_entries() -> Tuple[List[Dict[str, str]], bool]:
            compose_attempts = [
                (["ps", "--format", "{{json .}}"], parse_line_json),
                (["ps", "--format", "json"], parse_compose_json),
            ]
            for args, parser in compose_attempts:
                proc = self._execute(args, compose=True, check=False)
                if proc.returncode != 0:
                    message = (proc.stderr or proc.stdout or "").strip()
                    if message:
                        errors.append(message)
                        log_debug(f"compose ps error: {message}")
                    continue
                entries = parser(proc.stdout or "")
                if entries:
                    return entries, False
            proc = self._execute(["ps", "--format", "{{json .}}"], compose=False, check=False)
            if proc.returncode != 0:
                message = (proc.stderr or proc.stdout or "").strip()
                if message:
                    errors.append(message)
                    log_debug(f"docker ps fallback error: {message}")
                return [], True
            log_debug(f"docker ps entries collected: {len(parse_line_json(proc.stdout or '') )}")
            return parse_line_json(proc.stdout or ""), True

        entries, used_fallback = collect_entries()
        log_debug(f"entries found: {len(entries)} fallback={used_fallback}")

        runtime_lookup: Dict[str, ServiceRuntime] = {}
        warning: Optional[str] = None

        for entry in entries:
            label_field = entry.get("Labels") or entry.get("Label") or ""
            label_candidates: List[str] = []
            for label in label_field.split(","):
                key, sep, value = label.partition("=")
                if not sep:
                    continue
                key = key.strip()
                value = value.strip()
                if key == "com.docker.compose.service":
                    label_candidates.append(value)
            raw_candidates = [
                entry.get("Service"),
                entry.get("Name"),
                entry.get("Names"),
                *label_candidates,
                entry.get("Image"),
            ]
            candidates = normalise_candidates(raw_candidates)
            if not candidates:
                continue

            container_id = (entry.get("ID") or entry.get("Id") or entry.get("ContainerID") or "").strip() or None
            status_text = (entry.get("Status") or "").strip().lower()
            state_text = (entry.get("State") or status_text).strip().lower()
            primary_state = state_text or status_text
            primary_state = primary_state.split()[0] if primary_state else ""
            for prefix in ("running", "up", "exited", "dead", "created", "restarting", "paused"):
                if primary_state.startswith(prefix):
                    primary_state = prefix
                    break
            if not primary_state and status_text.startswith("up"):
                primary_state = "up"
            status = {
                "running": "UP",
                "up": "UP",
                "exited": "EXITED",
                "dead": "EXITED",
                "created": "DETENIDO",
                "restarting": "RESTARTING",
                "paused": "DETENIDO",
            }.get(primary_state, "DETENIDO")

            uptime_seconds = 0
            restarts = 0
            error_message: Optional[str] = None

            if container_id:
                try:
                    inspect = self._execute(["inspect", container_id], compose=False)
                    payload = json.loads(inspect.stdout or "[]")
                    if payload:
                        state_block = payload[0].get("State", {})
                        started_at = parse_iso_timestamp(state_block.get("StartedAt"))
                        if started_at:
                            uptime_seconds = max(0, int((now_utc() - started_at).total_seconds()))
                        restarts = int(state_block.get("RestartCount", 0))
                        if status == "UP" and state_block.get("Status", "").lower() == "running" and uptime_seconds == 0:
                            status = "RESTARTING"
                except DockerCommandError as inspect_error:
                    error_message = str(inspect_error)
                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    error_message = "No se pudo interpretar docker inspect"

            runtime_info = ServiceRuntime(
                status=status,
                uptime_seconds=uptime_seconds,
                restarts=restarts,
                container_id=container_id,
                last_seen=time.time(),
                error=error_message,
            )

            for candidate in candidates:
                if candidate and candidate not in runtime_lookup:
                    runtime_lookup[candidate] = runtime_info

        if used_fallback and errors:
            warning = f"No se pudo consultar docker compose: {errors[-1]}. Se uso docker ps como respaldo."
        if used_fallback and not runtime_lookup:
            warning = (warning + " Se mantienen los ultimos datos conocidos." if warning else "Docker ps no reporto contenedores activos. Se mantienen los ultimos datos conocidos.")
        elif not entries and errors:
            warning = errors[-1]

        fatal = any("docker no esta" in err.lower() for err in errors)
        if fatal and not runtime_lookup:
            raise DockerCommandError(errors[-1])

        indexed: Dict[str, Optional[ServiceRuntime]] = {}
        for definition in definitions:
            candidates = [
                (definition.compose_name or "").lower(),
                definition.service_id.lower(),
                re.sub(r"[_-]service$", "", (definition.compose_name or "").lower()),
            ]
            runtime_entry: Optional[ServiceRuntime] = None
            for candidate in candidates:
                if candidate and candidate in runtime_lookup:
                    runtime_entry = runtime_lookup[candidate]
                    break
            if not runtime_entry:
                for candidate in candidates:
                    for key, value in runtime_lookup.items():
                        if candidate and (key.endswith(candidate) or candidate.endswith(key)):
                            runtime_entry = value
                            break
                    if runtime_entry:
                        break
            indexed[definition.service_id] = runtime_entry

        return indexed, warning

    def start_service(self, service: ServiceDefinition) -> None:
        if not service.compose_name:
            raise DockerCommandError("Servicio sin nombre de compose configurado")
        self._execute(["up", "-d", service.compose_name])

    def stop_service(self, service: ServiceDefinition) -> None:
        if not service.compose_name:
            raise DockerCommandError("Servicio sin nombre de compose configurado")
        self._execute(["stop", service.compose_name])

    def restart_service(self, service: ServiceDefinition) -> None:
        if not service.compose_name:
            raise DockerCommandError("Servicio sin nombre de compose configurado")
        self._execute(["restart", service.compose_name])

    def remove_service(self, service: ServiceDefinition) -> None:
        if not service.compose_name:
            raise DockerCommandError("Servicio sin nombre de compose configurado")
        self._execute(["rm", "-sf", service.compose_name])

    def start_all(self) -> None:
        self._execute(["up", "-d"])

    def stop_all(self) -> None:
        self._execute(["stop"])

    def restart_all(self) -> None:
        self._execute(["restart"])

    def build_service(self, service: ServiceDefinition) -> str:
        if not service.compose_name:
            raise DockerCommandError("Servicio sin nombre de compose configurado")
        proc = self._execute(["build", "--progress=plain", service.compose_name])
        return self._collect_output(proc)

    def build_all(self) -> str:
        proc = self._execute(["build", "--progress=plain"])
        return self._collect_output(proc)

    def down_all(self, remove_volumes: bool = False) -> str:
        args = ["down"]
        if remove_volumes:
            args.append("--volumes")
        proc = self._execute(args)
        return self._collect_output(proc)

    def fetch_logs(self, service: ServiceDefinition, tail: int = LOG_TAIL_LINES) -> str:
        if not service.compose_name:
            raise DockerCommandError("Servicio sin nombre de compose configurado")
        proc = self._execute(
            ["logs", service.compose_name, "--no-color", "--tail", str(tail)],
            compose=True,
        )
        return proc.stdout or ""
class FontRegistry:
    def __init__(self, root: tk.Tk) -> None:
        base_family = ("SF Pro Display", "Segoe UI Variable", "Inter", "Roboto", "Segoe UI", "Helvetica Neue", "Arial")
        primary_family = next((f for f in base_family if tkfont.families() and f in tkfont.families()), "Segoe UI")
        self.heading = tkfont.Font(root=root, family=primary_family, size=24, weight="normal")
        self.subheading = tkfont.Font(root=root, family=primary_family, size=12)
        self.card_title = tkfont.Font(root=root, family=primary_family, size=15, weight="normal")
        self.card_role = tkfont.Font(root=root, family=primary_family, size=11)
        self.meta_label = tkfont.Font(root=root, family=primary_family, size=9, weight="normal")
        self.meta_value = tkfont.Font(root=root, family=primary_family, size=10)
        self.badge = tkfont.Font(root=root, family=primary_family, size=9, weight="normal")
        self.button = tkfont.Font(root=root, family=primary_family, size=10, weight="normal")
        self.button_small = tkfont.Font(root=root, family=primary_family, size=9, weight="normal")
        self.button_compact = tkfont.Font(root=root, family=primary_family, size=8, weight="normal")
        self.button_icon = tkfont.Font(root=root, family=primary_family, size=18, weight="bold")
        self.button_icon_small = tkfont.Font(root=root, family=primary_family, size=12, weight="bold")
        self.button_large = tkfont.Font(root=root, family=primary_family, size=14, weight="bold")
        self.caption = tkfont.Font(root=root, family=primary_family, size=9)


class StatusBadge(tk.Frame):
    def __init__(self, master: tk.Widget, fonts: FontRegistry) -> None:
        super().__init__(master, bg=TOKENS["surface"], highlightthickness=0)
        self._fonts = fonts
        self._current = "DESCONOCIDO"

        # Container for the status indicator
        container = tk.Frame(self, bg=TOKENS["surface"])
        container.pack(fill="both", expand=True)

        # Status light (colored circle) - larger and more prominent
        self.light_canvas = tk.Canvas(container, width=14, height=14, bg=TOKENS["surface"], highlightthickness=0, bd=0)
        self.light_canvas.pack(side="left", padx=(0, SPACING["sm"]), anchor="center")

        # Status text
        self.label = tk.Label(
            container,
            text="DESCONOCIDO",
            font=fonts.badge,
            bg=TOKENS["surface"],
            fg=TOKENS["text_dim"],
            anchor="w"
        )
        self.label.pack(side="left", anchor="center")

        self.update_status("DESCONOCIDO")

    def update_status(self, status: str) -> None:
        status = status or "DESCONOCIDO"
        variant = SERVICE_STATUS_VARIANTS.get(status, SERVICE_STATUS_VARIANTS["DESCONOCIDO"])
        self._current = status

        # Update the status light - larger and more prominent
        self.light_canvas.delete("all")
        light_color = variant.get("light", TOKENS["text_dim"])
        self.light_canvas.create_oval(2, 2, 12, 12, fill=light_color, outline="", width=0)

        # Add subtle glow effect for active status
        if status == "UP":
            self.light_canvas.create_oval(1, 1, 13, 13, fill="", outline=light_color, width=1)
        elif status == "RESTARTING":
            # Pulsing effect for restarting
            self.light_canvas.create_oval(0, 0, 14, 14, fill="", outline=light_color, width=1)

        # Update text
        self.label.configure(text=variant["label"], fg=variant["fg"])

    @property
    def value(self) -> str:
        return self._current



class ActionButton(tk.Button):
    def __init__(
        self,
        master: tk.Widget,
        fonts: FontRegistry,
        *,
        text: str = "",
        command: Callable[[], None],
        variant: str,
        icon: Optional[str] = None,
        tooltip: Optional[str] = None,
        size: Literal["default", "compact"] = "default",
    ) -> None:
        self.fonts = fonts
        self._variant = variant
        self._style: Dict[str, str] = {}
        self._icon_key = icon or variant
        self._label = text
        self._tooltip_text = tooltip
        self._tooltip_window: Optional[tk.Toplevel] = None
        self._size = size
        if size == "compact":
            self._default_padx = SPACING["xs"]
            self._default_pady = max(2, SPACING["xs"] // 2)
            base_font = getattr(fonts, "button_compact", fonts.button_small)
        else:
            self._default_padx = SPACING["sm"]
            self._default_pady = SPACING["xs"]
            base_font = fonts.button_small
        self._base_font = base_font
        super().__init__(
            master,
            command=command,
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            font=base_font,
            padx=self._default_padx,
            pady=self._default_pady,
            cursor="hand2",
        )
        self.apply_variant(variant)
        self.set_content(label=text, icon=icon, tooltip=tooltip)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

    def apply_variant(self, variant: str) -> None:
        self._variant = variant
        style = ACTION_STYLE.get(variant, ACTION_STYLE["ghost"])
        self._style = style
        self.configure(
            bg=style["bg"],
            fg=style["fg"],
            activebackground=style["hover"],
            activeforeground=style.get("active_fg", style["fg"]),
            highlightbackground=style["border"],
            highlightcolor=style["border"],
            disabledforeground=TOKENS["text_dim"],
        )

    def set_content(
        self,
        *,
        label: Optional[str] = None,
        icon: Optional[str] = None,
        tooltip: Optional[str] = None,
    ) -> None:
        if label is not None:
            self._label = label
        if icon is not None:
            self._icon_key = icon
        glyph = ICON_GLYPHS.get(self._icon_key, "")
        has_icon = bool(glyph.strip())
        if self._label:
            display = f"{glyph} {self._label}".strip()
        else:
            display = glyph or ""
        self.configure(text=display)
        if has_icon:
            if self._size == "compact":
                icon_font = getattr(self.fonts, "button_icon_small", self._base_font)
                pad_x = self._default_padx
                pad_y = self._default_pady
            else:
                icon_font = getattr(self.fonts, "button_icon", getattr(self.fonts, "button_large", self._base_font))
                pad_x = SPACING["lg"]
                pad_y = SPACING["sm"]
            self.configure(font=icon_font, padx=pad_x, pady=pad_y)
        else:
            self.configure(font=self._base_font, padx=self._default_padx, pady=self._default_pady)
        if tooltip is not None:
            self._tooltip_text = tooltip

    def set_disabled(self, disabled: bool) -> None:
        if disabled:
            super().configure(state=tk.DISABLED, bg=self._style["bg"], fg=TOKENS["text_dim"], cursor="arrow")
            self._hide_tooltip()
        else:
            super().configure(state=tk.NORMAL, bg=self._style["bg"], fg=self._style["fg"], cursor="hand2")

    def _on_enter(self, _event) -> None:
        if self["state"] != tk.DISABLED:
            hover_bg = self._style.get("hover_bg", self._style["hover"])
            super().configure(bg=hover_bg, fg=self._style["hover"])
        if self._tooltip_text and self._tooltip_window is None and self["state"] != tk.DISABLED:
            self._show_tooltip()

    def _on_leave(self, _event) -> None:
        if self["state"] != tk.DISABLED:
            super().configure(bg=self._style["bg"], fg=self._style["fg"])
        self._hide_tooltip()

    def _on_focus_in(self, _event) -> None:
        self.configure(highlightthickness=2)

    def _on_focus_out(self, _event) -> None:
        self.configure(highlightthickness=1)
        self._hide_tooltip()

    def _show_tooltip(self) -> None:
        if not self._tooltip_text:
            return
        tooltip = tk.Toplevel(self)
        tooltip.wm_overrideredirect(True)
        tooltip.configure(
            bg=TOKENS["surface"],
            padx=SPACING["xs"],
            pady=SPACING["xs"],
            highlightthickness=1,
            highlightbackground=TOKENS["border"],
        )
        label = tk.Label(
            tooltip,
            text=self._tooltip_text,
            bg=TOKENS["surface"],
            fg=TOKENS["text_dim"],
            font=("Segoe UI", 9),
        )
        label.pack()
        x = self.winfo_rootx() + self.winfo_width() // 2
        y = self.winfo_rooty() - 28
        tooltip.wm_geometry(f"+{x}+{y}")
        self._tooltip_window = tooltip

    def _hide_tooltip(self) -> None:
        if self._tooltip_window:
            self._tooltip_window.destroy()
            self._tooltip_window = None
class ServiceCard(NeonPanel):
    def __init__(
        self,
        master: tk.Widget,
        fonts: FontRegistry,
        service: ServiceViewModel,
        on_action: Callable[[ServiceViewModel, str], None],
        on_focus: Callable[[str], None],
    ) -> None:
        super().__init__(master, padding=(SPACING["sm"], SPACING["sm"]), show_accent=False)
        self.fonts = fonts
        self._service = service
        self._on_action = on_action
        self._on_focus = on_focus
        self._is_processing = False
        self._toggle_action = "start"

        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(0, weight=1)

        content = tk.Frame(self.container, bg=TOKENS["surface"], padx=SPACING["md"], pady=SPACING["sm"])
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=0)

        info = tk.Frame(content, bg=TOKENS["surface"])
        info.grid(row=0, column=0, sticky="nsew")
        info.columnconfigure(0, weight=1)

        header = tk.Frame(info, bg=TOKENS["surface"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, SPACING["xs"]))
        header.columnconfigure(0, weight=1)

        self.name_label = tk.Label(
            header,
            text=service.display_name,
            font=fonts.card_title,
            bg=TOKENS["surface"],
            fg=TOKENS["text"],
            anchor="w",
        )
        self.name_label.grid(row=0, column=0, sticky="w")

        self.status_badge = StatusBadge(header, fonts)
        self.status_badge.grid(row=0, column=1, sticky="e", padx=(SPACING["sm"], 0))

        self.role_label = tk.Label(
            info,
            text=service.role,
            font=fonts.card_role,
            bg=TOKENS["surface"],
            fg=TOKENS["text_dim"],
            anchor="w",
        )
        self.role_label.grid(row=1, column=0, sticky="w")

        self.meta_line = tk.Label(
            info,
            text="",
            font=fonts.meta_value,
            bg=TOKENS["surface"],
            fg=TOKENS["text_dim"],
            anchor="w",
        )
        self.meta_line.grid(row=2, column=0, sticky="w", pady=(SPACING["xs"], 0))

        self.error_label = tk.Label(
            info,
            text="",
            bg=TOKENS["surface"],
            fg=TOKENS["danger"],
            font=fonts.caption,
            anchor="w",
            wraplength=240,
            justify="left",
        )
        self.error_label.grid(row=3, column=0, sticky="w", pady=(SPACING["xs"], 0))
        self.error_label.grid_remove()

        action_bar = tk.Frame(content, bg=TOKENS["surface"])
        action_bar.grid(row=0, column=1, sticky="ne", padx=(SPACING["md"], 0))

        self.buttons: Dict[str, ActionButton] = {}

        self.toggle_button = ActionButton(
            action_bar,
            fonts,
            text="",
            command=lambda: self._invoke("toggle"),
            variant="start",
            icon="toggle_off",
            tooltip="Iniciar servicio",
            size="compact",
        )
        self.toggle_button.grid(row=0, column=0, padx=(0, SPACING["xs"]))
        self.buttons["toggle"] = self.toggle_button

        self.restart_button = ActionButton(
            action_bar,
            fonts,
            text="",
            command=lambda: self._invoke("restart"),
            variant="restart",
            icon="restart",
            tooltip="Reiniciar servicio",
            size="compact",
        )
        self.restart_button.grid(row=0, column=1, padx=(0, SPACING["xs"]))
        self.buttons["restart"] = self.restart_button

        next_column = 2
        if service.definition.service_id in BUILDABLE_SERVICE_IDS and service.definition.compose_name:
            build_button = ActionButton(
                action_bar,
                fonts,
                text="",
                command=lambda: self._invoke("build"),
                variant="build",
                icon="build",
                tooltip="Reconstruir imagen",
                size="compact",
            )
            build_button.grid(row=0, column=next_column, padx=(0, SPACING["xs"]))
            self.buttons["build"] = build_button
            next_column += 1

        self.remove_button = ActionButton(
            action_bar,
            fonts,
            text="",
            command=lambda: self._invoke("remove"),
            variant="danger",
            icon="trash",
            tooltip="Eliminar contenedor",
            size="compact",
        )
        self.remove_button.grid(row=0, column=next_column, padx=(0, SPACING["xs"]))
        self.buttons["remove"] = self.remove_button

        self.update_view(service)

    def _handle_focus(self, _event) -> None:
        self.container.focus_set()
        self._on_focus(self._service.definition.service_id)

    def _on_focus_in(self, _event) -> None:
        self.config(highlightthickness=2)

    def _on_focus_out(self, _event) -> None:
        self.config(highlightthickness=1)

    def _invoke(self, action: str) -> None:
        if self._is_processing:
            return
        if action == "toggle":
            self._on_action(self._service, self._toggle_action)
            return
        self._on_action(self._service, action)

    def _set_button_state(self, key: str, *, disabled: bool) -> None:
        button = self.buttons.get(key)
        if button:
            button.set_disabled(disabled)

    def update_view(self, service: ServiceViewModel) -> None:
        self._service = service
        self.name_label.configure(text=service.display_name)
        self.role_label.configure(text=service.role)
        self.status_badge.update_status(service.status)
        meta_text = (
            f"Puerto {self._format_port(service.port)}  ·  "
            f"Uptime {format_duration(service.uptime_secs)}  ·  "
            f"Reinicios {service.restarts}"
        )
        self.meta_line.configure(text=meta_text)
        if service.runtime.error:
            self.error_label.configure(text=service.runtime.error)
            self.error_label.grid()
        else:
            self.error_label.configure(text="")
            self.error_label.grid_remove()

        is_up = service.status == "UP"
        self._toggle_action = "stop" if is_up else "start"
        if is_up:
            self.toggle_button.apply_variant("stop")
            self.toggle_button.set_content(icon="toggle_on", tooltip="Detener servicio")
        else:
            self.toggle_button.apply_variant("start")
            self.toggle_button.set_content(icon="toggle_off", tooltip="Iniciar servicio")

        self._set_button_state("restart", disabled=not is_up)
        if "build" in self.buttons:
            self._set_button_state("build", disabled=not service.definition.compose_name)
        self._set_button_state("remove", disabled=False)

    def _format_port(self, port: Optional[int]) -> str:
        return str(port) if port else "-"

    def set_processing(self, processing: bool) -> None:
        self._is_processing = processing
        for button in self.buttons.values():
            button.set_disabled(processing)
        if processing:
            self.config(highlightbackground=TOKENS["accent"], highlightcolor=TOKENS["accent"])
        else:
            self.config(highlightbackground=TOKENS["accent_alt"], highlightcolor=TOKENS["accent_alt"])


class ServicesGrid(tk.Frame):

    def __init__(
        self,
        master: tk.Widget,
        fonts: FontRegistry,
        on_action: Callable[[ServiceViewModel, str], None],
        on_focus: Callable[[str], None],
    ) -> None:
        super().__init__(master, bg=TOKENS["bg"])
        self.fonts = fonts
        self._on_action = on_action
        self._on_focus = on_focus
        self._cards: Dict[str, ServiceCard] = {}
        self._skeletons: List[SkeletonServiceCard] = []
        self._empty_label: Optional[tk.Label] = None
        self._services: List[ServiceViewModel] = []
        self._columns = 0

        self.canvas = tk.Canvas(
            self,
            bg=TOKENS["bg"],
            highlightthickness=0,
            bd=0,
            relief="flat",
        )
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview,
            style="Dark.Vertical.TScrollbar",
        )
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.inner = tk.Frame(self.canvas, bg=TOKENS["bg"])
        self._inner_window = self.canvas.create_window(
            (0, 0),
            window=self.inner,
            anchor="nw",
        )

        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.inner.bind("<Configure>", self._on_inner_configure)
        for widget in (self.canvas, self.inner):
            widget.bind("<MouseWheel>", self._on_mousewheel)
            widget.bind("<Button-4>", self._on_mousewheel_linux)
            widget.bind("<Button-5>", self._on_mousewheel_linux)

        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, _event) -> None:

        self.after_idle(self._relayout_cards)

    def _on_canvas_configure(self, event) -> None:

        if hasattr(self, "_inner_window"):

            self.canvas.itemconfigure(self._inner_window, width=event.width)

        self._update_scroll_region()

    def _on_inner_configure(self, _event) -> None:

        self._update_scroll_region()

    def _update_scroll_region(self) -> None:

        bbox = self.canvas.bbox("all")

        if bbox:

            self.canvas.configure(scrollregion=bbox)

    def _on_mousewheel(self, event) -> None:

        delta = event.delta

        if delta == 0:

            return

        if sys.platform == "darwin":

            step = int(-delta)

        else:

            step = int(-delta / 120)

        if step == 0:

            step = -1 if delta > 0 else 1

        self.canvas.yview_scroll(step, "units")

    def _on_mousewheel_linux(self, event) -> None:

        if event.num == 4:

            self.canvas.yview_scroll(-1, "units")

        elif event.num == 5:

            self.canvas.yview_scroll(1, "units")



    def show_skeleton(self, count: int = 3) -> None:

        self.clear()

        for _ in range(count):

            skeleton = SkeletonServiceCard(self.inner)

            skeleton.pack(fill="x", padx=SPACING["sm"], pady=SPACING["sm"])

            self._skeletons.append(skeleton)

        self.canvas.yview_moveto(0)

        self._update_scroll_region()



    def show_empty(self) -> None:

        self.clear()

        self._empty_label = tk.Label(

            self.inner,

            text="Sin servicios registrados",

            bg=TOKENS["bg"],

            fg=TOKENS["text_dim"],

            font=self.fonts.meta_value,

            pady=SPACING["lg"],

        )

        self._empty_label.pack(fill="both", expand=True)

        self.canvas.yview_moveto(0)

        self._update_scroll_region()



    def clear(self) -> None:

        for card in self._cards.values():

            card.destroy()

        self._cards.clear()

        for skeleton in self._skeletons:

            skeleton.destroy()

        self._skeletons.clear()

        if self._empty_label:

            self._empty_label.destroy()

            self._empty_label = None
        self.canvas.yview_moveto(0)
        self._update_scroll_region()




    def set_services(self, services: List[ServiceViewModel]) -> None:

        self._services = services

        self.clear()

        if not services:

            self.show_empty()

            return

        for service in services:

            card = ServiceCard(self.inner, self.fonts, service, self._on_action, self._on_focus)

            self._cards[service.definition.service_id] = card

        self._relayout_cards()

        self.canvas.yview_moveto(0)

        self._update_scroll_region()



    def _relayout_cards(self) -> None:
        for card in self._cards.values():
            card.grid_forget()
        if not self._cards:
            return
        self.inner.grid_columnconfigure(0, weight=1)
        self._columns = 1
        for idx, service in enumerate(self._services):
            card = self._cards.get(service.definition.service_id)
            if not card:
                continue
            card.grid(row=idx, column=0, padx=SPACING["sm"], pady=SPACING["sm"], sticky="ew")
        self._update_scroll_region()

    def set_processing(self, service_id: str, processing: bool) -> None:
        card = self._cards.get(service_id)
        if card:
            card.set_processing(processing)

    def set_all_processing(self, processing: bool) -> None:
        for card in self._cards.values():
            card.set_processing(processing)

    def get_service(self, service_id: str) -> Optional[ServiceViewModel]:
        for svc in self._services:
            if svc.definition.service_id == service_id:
                return svc
        return None






class LogPanel(NeonPanel):
    def __init__(
        self,
        master: tk.Widget,
        fonts: FontRegistry,
        *,
        max_lines: int = 500,
        on_open_log: Optional[Callable[[str, Path], None]] = None,
    ) -> None:
        super().__init__(master, padding=(SPACING["md"], SPACING["md"]))
        self._fonts = fonts
        self._max_lines = max_lines
        self._on_open_log = on_open_log or (lambda _label, _path: None)
        self._sources: list[Tuple[str, Path]] = []
        self._source_buttons: Dict[str, ActionButton] = {}

        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_columnconfigure(1, weight=0)
        self.container.grid_rowconfigure(1, weight=1)

        header = tk.Frame(self.container, bg=TOKENS["surface"])
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, SPACING["xs"]))

        self.actions_frame = tk.Frame(header, bg=TOKENS["surface"])
        self.actions_frame.pack(side="left", anchor="w")

        self.text = tk.Text(
            self.container,
            bg=TOKENS["surface_alt"],
            fg=TOKENS["text"],
            insertbackground=TOKENS["accent"],
            font=fonts.meta_value,
            wrap="word",
            relief="flat",
            height=10,
            padx=SPACING["sm"],
            pady=SPACING["sm"],
        )
        self.text.configure(state=tk.DISABLED)
        self.text.grid(row=1, column=0, sticky="nsew")

        self.scrollbar = ttk.Scrollbar(
            self.container,
            orient="vertical",
            command=self.text.yview,
            style="Dark.Vertical.TScrollbar",
        )
        self.scrollbar.grid(row=1, column=1, sticky="ns")
        self.text.configure(yscrollcommand=self.scrollbar.set)

    def set_sources(self, sources: Sequence[Tuple[str, Path]]) -> None:
        normalised = [(label, Path(path)) for label, path in sources]
        if normalised == self._sources:
            self._refresh_button_states()
            return

        for button in self._source_buttons.values():
            button.destroy()
        self._source_buttons.clear()
        self._sources = normalised

        for idx, (label, path) in enumerate(self._sources):
            button = ActionButton(
                self.actions_frame,
                self._fonts,
                text=label,
                command=lambda l=label, p=path: self._handle_source_click(l, p),
                variant="ghost",
                icon="logs",
                size="compact",
                tooltip=f"Abrir {path.name}",
            )
            button.pack(side="left", padx=(0 if idx == 0 else SPACING["xs"], 0))
            if not path.exists():
                button.set_disabled(True)
            self._source_buttons[label] = button

    def _refresh_button_states(self) -> None:
        for label, path in self._sources:
            button = self._source_buttons.get(label)
            if not button:
                continue
            button.set_disabled(not path.exists())

    def _handle_source_click(self, label: str, path: Path) -> None:
        if not path.exists():
            button = self._source_buttons.get(label)
            if button:
                button.set_disabled(True)
            return
        self._on_open_log(label, path)



    def append(self, message: str, *, annotate: bool = True) -> None:
        if message is None:
            return
        lines = message.splitlines() or [""]
        timestamp = time.strftime("%H:%M:%S")
        prefix = f"[{timestamp}] " if annotate else ""
        indent = " " * len(prefix)
        self.text.configure(state=tk.NORMAL)
        for idx, line in enumerate(lines):
            label = prefix if idx == 0 else (indent if annotate else "")
            self.text.insert(tk.END, f"{label}{line}\n")
        self._trim()
        self.text.configure(state=tk.DISABLED)
        self.text.yview_moveto(1.0)

    def append_raw(self, text: str) -> None:
        if not text:
            return
        self.text.configure(state=tk.NORMAL)
        for line in text.splitlines():
            self.text.insert(tk.END, f"{line}\n")
        self._trim()
        self.text.configure(state=tk.DISABLED)
        self.text.yview_moveto(1.0)

    def clear(self) -> None:
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.configure(state=tk.DISABLED)

    def _trim(self) -> None:
        total_lines = int(float(self.text.index("end-1c")))
        if total_lines <= self._max_lines:
            return
        excess = total_lines - self._max_lines
        self.text.delete("1.0", f"{excess + 1}.0")



class SkeletonServiceCard(tk.Frame):
    def __init__(self, master: tk.Widget) -> None:
        super().__init__(
            master,
            bg=TOKENS["surface"],
            highlightbackground=TOKENS["border"],
            highlightthickness=1,
            bd=0,
        )
        self.configure(height=200)
        self.pack_propagate(False)

        container = tk.Frame(self, bg=TOKENS["surface"], padx=SPACING["lg"], pady=SPACING["lg"])
        container.pack(fill="both", expand=True)

        self._placeholder(container, width=180, height=18).pack(pady=(0, SPACING["sm"]))
        self._placeholder(container, width=120, height=14).pack(pady=(0, SPACING["lg"]))

        meta = tk.Frame(container, bg=TOKENS["surface"])
        meta.pack(fill="x", pady=(0, SPACING["lg"]))
        for _ in range(3):
            self._placeholder(meta, width=90, height=28).pack(side="left", expand=True, fill="x", padx=(0, SPACING["md"]))

        actions = tk.Frame(container, bg=TOKENS["surface"])
        actions.pack(fill="x")
        for _ in range(3):
            self._placeholder(actions, width=80, height=28).pack(side="left", padx=(0, SPACING["sm"]))

    def _placeholder(self, parent: tk.Widget, *, width: int, height: int) -> tk.Frame:
        frame = tk.Frame(
            parent,
            bg=TOKENS["surface_alt"],
            width=width,
            height=height,
        )
        frame.pack_propagate(False)
        return frame


class ErrorPopup(tk.Frame):
    def __init__(self, master: tk.Widget, fonts: FontRegistry) -> None:
        super().__init__(master, bg=TOKENS["danger_bg"], highlightbackground=TOKENS["danger"], highlightthickness=1, bd=0)
        self._fonts = fonts
        self._visible = False
        self._after_id: Optional[str] = None

        self.label = tk.Label(
            self,
            text="",
            bg=TOKENS["danger_bg"],
            fg=TOKENS["danger"],
            font=fonts.meta_value,
            anchor="w",
            justify="left",
            padx=SPACING["sm"],
            pady=SPACING["xs"],
        )
        self.label.pack(fill="both", expand=True)

    def show(self, message: str, *, duration: Optional[int] = 4000) -> None:
        self.label.configure(text=message)
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        if not self._visible:
            self.place(relx=1.0, y=SPACING["sm"], anchor="ne", x=-SPACING["sm"])
            self._visible = True
        if duration:
            self._after_id = self.after(duration, self.hide)

    def hide(self) -> None:
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        if self._visible:
            self.place_forget()
            self._visible = False
class FooterStatus(tk.Frame):
    def __init__(
        self,
        master: tk.Widget,
        fonts: FontRegistry,
    ) -> None:
        super().__init__(master, bg=TOKENS["surface"], pady=SPACING["xs"], padx=SPACING["md"])

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)

        left = tk.Frame(self, bg=TOKENS["surface"])
        left.grid(row=0, column=0, sticky="w")

        self.summary_label = tk.Label(
            left,
            text="Servicios 0/0",
            bg=TOKENS["surface"],
            fg=TOKENS["text"],
            font=fonts.meta_value,
            anchor="w",
        )
        self.summary_label.pack(anchor="w")

        self.message_label = tk.Label(
            left,
            text="Listo",
            bg=TOKENS["surface"],
            fg=TOKENS["text_dim"],
            font=fonts.card_role,
            anchor="w",
        )
        self.message_label.pack(anchor="w")

        right = tk.Frame(self, bg=TOKENS["surface"])
        right.grid(row=0, column=1, sticky="e")

        self.last_updated_label = tk.Label(
            right,
            text="Actualizado: -",
            bg=TOKENS["surface"],
            fg=TOKENS["text_dim"],
            font=fonts.meta_label,
            anchor="e",
        )
        self.last_updated_label.pack(side="left", padx=(0, SPACING["sm"]))

    def update_summary(self, active: int, total: int) -> None:
        self.summary_label.configure(text=f"Servicios {active}/{total}")

    def update_message(self, message: str) -> None:
        self.message_label.configure(text=message)

    def update_last_updated(self, timestamp: Optional[float]) -> None:
        if not timestamp:
            self.last_updated_label.configure(text="Actualizado: -")
            return
        formatted = time.strftime("%H:%M:%S", time.localtime(timestamp))
        self.last_updated_label.configure(text=f"Actualizado: {formatted}")

    def set_processing(self, _processing: bool) -> None:
        return


class LaunchCard(NeonPanel):
    def __init__(
        self,
        master: tk.Widget,
        fonts: FontRegistry,
        on_launch: Callable[[], None],
    ) -> None:
        super().__init__(master, padding=(SPACING["lg"], SPACING["lg"]))
        content = tk.Frame(self.container, bg=TOKENS["surface"])
        content.pack(fill="both", expand=True)

        self.launch_button = ActionButton(
            content,
            fonts,
            text="Capi Agentes",
            command=on_launch,
            variant="launch",
            icon="toggle_off",
            tooltip="Abrir interfaz web",
        )
        self.launch_button.apply_variant("launch")
        self.launch_button.configure(font=fonts.button_large, padx=SPACING["xl"], pady=SPACING["sm"])
        self.launch_button.pack(expand=True)

    def set_disabled(self, disabled: bool) -> None:
        self.launch_button.set_disabled(disabled)


class ToolbarGroup(NeonPanel):
    def __init__(
        self,
        master: tk.Widget,
        fonts: FontRegistry,
        title: str,
        *,
        show_status: bool = False,
    ) -> None:
        super().__init__(master, padding=(SPACING["sm"], SPACING["sm"]), show_accent=False)
        self.fonts = fonts
        title_frame = tk.Frame(self.container, bg=TOKENS["surface"])
        title_frame.pack(fill="x", pady=(0, SPACING["xs"]))

        self.title_label = tk.Label(
            title_frame,
            text=title,
            bg=TOKENS["surface"],
            fg=TOKENS["text_dim"],
            font=fonts.meta_label,
        )
        self.title_label.pack(side="left", anchor="w")

        self.status_badge: Optional[StatusBadge] = None
        if show_status:
            self.status_badge = StatusBadge(title_frame, fonts)
            self.status_badge.pack(side="right", anchor="e")

        self.actions_frame = tk.Frame(self.container, bg=TOKENS["surface"])
        self.actions_frame.pack(fill="x")

    def add_button(
        self,
        *,
        text: str,
        command: Callable[[], None],
        variant: str,
        icon: Optional[str] = None,
        tooltip: Optional[str] = None,
    ) -> ActionButton:
        button = ActionButton(
            self.actions_frame,
            self.fonts,
            text=text,
            command=command,
            variant=variant,
            icon=icon,
            tooltip=tooltip,
        )
        button.pack(side="left", padx=(0, SPACING["xs"]))
        return button

    def update_status(self, status: Optional[str]) -> None:
        if self.status_badge and status:
            self.status_badge.update_status(status)

    def set_disabled(self, disabled: bool) -> None:
        for child in self.actions_frame.winfo_children():
            if isinstance(child, ActionButton):
                child.set_disabled(disabled)


class GlobalToolbar(tk.Frame):
    def __init__(
        self,
        master: tk.Widget,
        fonts: FontRegistry,
        *,
        on_bulk_action: Callable[[str], None],
    ) -> None:
        super().__init__(master, bg=TOKENS["bg"], pady=SPACING["sm"])
        self._on_bulk_action = on_bulk_action

        self.columnconfigure(0, weight=1)

        bar = tk.Frame(self, bg=TOKENS["bg"])
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(0, weight=1)

        self.buttons = {}

        group_frame = tk.Frame(bar, bg=TOKENS["bg"], pady=SPACING["xs"])
        group_frame.grid(row=0, column=0, sticky="w")

        self.buttons["start_all"] = ActionButton(
            group_frame,
            fonts,
            text="Iniciar todo",
            command=lambda: self._on_bulk_action("start"),
            variant="start",
            icon="toggle_off",
            tooltip="Inicia todos los servicios",
            size="compact",
        )
        self.buttons["start_all"].pack(side="left", padx=(0, SPACING["xs"]))

        self.buttons["stop_all"] = ActionButton(
            group_frame,
            fonts,
            text="Detener todo",
            command=lambda: self._on_bulk_action("stop"),
            variant="stop",
            icon="toggle_on",
            tooltip="Detiene todos los servicios",
            size="compact",
        )
        self.buttons["stop_all"].pack(side="left", padx=(0, SPACING["xs"]))

        self.buttons["restart_all"] = ActionButton(
            group_frame,
            fonts,
            text="Reiniciar todo",
            command=lambda: self._on_bulk_action("restart"),
            variant="restart",
            icon="restart",
            tooltip="Reinicia todos los servicios",
            size="compact",
        )
        self.buttons["restart_all"].pack(side="left", padx=(0, SPACING["xs"]))

    def set_processing(self, processing: bool) -> None:
        for button in self.buttons.values():
            button.set_disabled(processing)


class DashboardView(tk.Frame):
    def __init__(
        self,
        master: tk.Tk,
        fonts: FontRegistry,
        *,
        on_bulk_action: Callable[[str], None],
        on_service_action: Callable[[ServiceViewModel, str], None],
        on_open_log: Callable[[str, Path], None],
        on_open_frontend: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(master, bg=TOKENS["bg"], padx=SPACING["xl"], pady=SPACING["xl"])
        self.fonts = fonts
        self._on_service_action = on_service_action
        self._on_open_frontend = on_open_frontend or (lambda: None)
        self._focused_service: Optional[str] = None

        self.grid_columnconfigure(0, weight=3, uniform="layout")
        self.grid_columnconfigure(1, weight=1, uniform="layout")
        self.grid_rowconfigure(3, weight=1)

        header = tk.Frame(self, bg=TOKENS["bg"])
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, SPACING["xl"]))
        header.columnconfigure(1, weight=1)
        header.columnconfigure(2, weight=1)

        indicator_frame = tk.Frame(header, bg=TOKENS["bg"])
        indicator_frame.grid(row=0, column=0, rowspan=2, padx=(0, SPACING["lg"]), pady=(4, 0))

        indicator = tk.Canvas(indicator_frame, width=8, height=8, bg=TOKENS["bg"], highlightthickness=0)
        indicator.create_oval(1, 1, 7, 7, fill=TOKENS["accent"], outline="")
        indicator.pack(anchor="center")

        self.title_label = tk.Label(
            header,
            text="CapiAgentes",
            bg=TOKENS["bg"],
            fg=TOKENS["text"],
            font=fonts.heading,
            anchor="w",
        )
        self.title_label.grid(row=0, column=1, sticky="w")

        self.subtitle_label = tk.Label(
            header,
            text="Control y monitoreo de servicios Docker",
            bg=TOKENS["bg"],
            fg=TOKENS["text_dim"],
            font=fonts.subheading,
            anchor="w",
        )
        self.subtitle_label.grid(row=1, column=1, sticky="w", pady=(2, 0))

        status_area = tk.Frame(header, bg=TOKENS["bg"])
        status_area.grid(row=0, column=2, rowspan=2, sticky="ew")
        status_area.columnconfigure(0, weight=1)
        status_area.columnconfigure(1, weight=0)

        badge_wrapper = tk.Frame(status_area, bg=TOKENS["surface_alt"], highlightbackground=TOKENS["border"], highlightthickness=1)
        badge_wrapper.grid(row=0, column=0, sticky="w", padx=(0, SPACING["sm"]))

        badge_inner = tk.Frame(badge_wrapper, bg=TOKENS["surface_alt"], padx=SPACING["md"], pady=SPACING["xs"])
        badge_inner.pack(fill="x")
        badge_inner.columnconfigure(0, weight=1)
        badge_inner.columnconfigure(1, weight=0)

        self.count_title = tk.Label(
            badge_inner,
            text="Servicios",
            bg=TOKENS["surface_alt"],
            fg=TOKENS["text_dim"],
            font=fonts.meta_label,
            anchor="w",
        )
        self.count_title.grid(row=0, column=0, sticky="w")

        self.count_badge = tk.Label(
            badge_inner,
            text="0/0",
            bg=TOKENS["surface_alt"],
            fg=TOKENS["accent"],
            font=fonts.meta_value,
            anchor="e",
        )
        self.count_badge.grid(row=0, column=1, sticky="e")

        self.toolbar = GlobalToolbar(
            self,
            fonts,
            on_bulk_action=on_bulk_action,
        )
        self.toolbar.grid(row=1, column=0, columnspan=2, sticky="ew")

        self.error_popup = ErrorPopup(self, fonts)

        self.services_grid = ServicesGrid(self, fonts, on_action=on_service_action, on_focus=self._set_focused)
        self.services_grid.grid(row=3, column=0, sticky="nsew", pady=(SPACING["md"], SPACING["md"]), padx=(0, SPACING["lg"]))

        self.log_panel = LogPanel(self, fonts, on_open_log=on_open_log)
        self.log_panel.grid(row=3, column=1, sticky="nsew")
        self.log_panel.append("Registro de eventos inicializado")

        bottom_frame = tk.Frame(self, bg=TOKENS["bg"])
        bottom_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(SPACING["md"], 0))
        bottom_frame.columnconfigure(0, weight=3, uniform="bottom")
        bottom_frame.columnconfigure(1, weight=1, uniform="bottom")

        footer_panel = NeonPanel(bottom_frame, padding=(SPACING["lg"], SPACING["md"]))
        footer_panel.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["md"]))
        self.footer = FooterStatus(footer_panel.container, fonts)
        self.footer.pack(fill="x")

        self.launch_card = LaunchCard(bottom_frame, fonts, on_launch=self._handle_open_frontend)
        self.launch_card.grid(row=0, column=1, sticky="ew")

    def _handle_open_frontend(self) -> None:
        self._on_open_frontend()
        self._log_event("Frontend solicitado desde la tarjeta dedicada")

    def _set_focused(self, service_id: str) -> None:
        self._focused_service = service_id

    @property
    def focused_service(self) -> Optional[str]:
        return self._focused_service

    def show_loading(self) -> None:
        self.error_popup.hide()
        self.services_grid.show_skeleton()

    def show_error(self, message: Optional[str]) -> None:
        if message:
            self.error_popup.show(message, duration=5000)
        else:
            self.error_popup.hide()

    def set_services(self, services: List[ServiceViewModel]) -> None:
        self.services_grid.set_services(services)

    def set_log_sources(self, sources: Sequence[Tuple[str, Path]]) -> None:
        self.log_panel.set_sources(sources)

    def update_counts(self, active: int, total: int) -> None:
        self.count_badge.configure(text=f"{active} ACTIVOS / {total}")
        self.footer.update_summary(active, total)

    def update_last_updated(self, timestamp: Optional[float]) -> None:
        self.footer.update_last_updated(timestamp)

    def update_message(self, message: str) -> None:
        self.footer.update_message(message)

    def set_processing(self, service_id: Optional[str], processing: bool) -> None:
        if service_id:
            self.services_grid.set_processing(service_id, processing)
        else:
            self.services_grid.set_all_processing(processing)
            self.toolbar.set_processing(processing)
            self.footer.set_processing(processing)
            self.launch_card.set_disabled(processing)


    def _log_event(self, message: str) -> None:
        if not message:
            return
        self.append_log(message)

    def append_log(self, message: str, *, annotate: bool = True) -> None:
        self.log_panel.append(message, annotate=annotate)

    def append_log_raw(self, text: str) -> None:
        self.log_panel.append_raw(text)

    def clear_log(self) -> None:
        self.log_panel.clear()
class ConfirmDialog(tk.Toplevel):
    def __init__(self, master: tk.Tk, fonts: FontRegistry) -> None:
        super().__init__(master)
        self.withdraw()
        self.transient(master)
        self.title("Confirmar eliminacion")
        self.configure(bg=TOKENS["surface_alt"], padx=SPACING["lg"], pady=SPACING["lg"], highlightthickness=1, highlightbackground=TOKENS["accent"])
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self._fonts = fonts
        self._on_confirm: Optional[Callable[[], None]] = None

        self.label_title = tk.Label(
            self,
            text="Eliminar servicio",
            bg=TOKENS["surface_alt"],
            fg=TOKENS["text"],
            font=fonts.card_title,
            anchor="w",
        )
        self.label_title.pack(fill="x")

        self.label_description = tk.Label(
            self,
            text="",
            bg=TOKENS["surface_alt"],
            fg=TOKENS["text_dim"],
            font=fonts.card_role,
            wraplength=360,
            justify="left",
        )
        self.label_description.pack(fill="x", pady=(SPACING["sm"], SPACING["lg"]))

        actions = tk.Frame(self, bg=TOKENS["surface_alt"])
        actions.pack(fill="x")

        self.cancel_button = ActionButton(
            actions,
            fonts,
            text="Cancelar",
            command=self._on_cancel,
            variant="ghost",
        )
        self.cancel_button.pack(side="right", padx=(SPACING["sm"], 0))

        self.confirm_button = ActionButton(
            actions,
            fonts,
            text="Eliminar",
            command=self._on_confirm_click,
            variant="danger",
        )
        self.confirm_button.pack(side="right")

    def open(self, service_name: str, on_confirm: Callable[[], None]) -> None:
        self._on_confirm = on_confirm
        self.label_title.configure(text=f"Eliminar {service_name}")
        self.label_description.configure(
            text=(
                f"¿Eliminar contenedor {service_name}? Esta accion detendra y eliminara el contenedor. "
                "No se borrara la imagen asociada."
            )
        )
        self.deiconify()
        self.wait_visibility()
        self.grab_set()
        self.focus_force()
        self.confirm_button.focus_set()

    def _on_confirm_click(self) -> None:
        if self._on_confirm:
            callback = self._on_confirm
            self._on_confirm = None
            self.grab_release()
            self.withdraw()
            callback()
        else:
            self.grab_release()
            self.withdraw()

    def _on_cancel(self) -> None:
        self._on_confirm = None
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.withdraw()


class LogsWindow(tk.Toplevel):
    def __init__(self, master: tk.Tk, fonts: FontRegistry) -> None:
        super().__init__(master)
        self.withdraw()
        self.configure(bg=TOKENS["surface"], padx=SPACING["lg"], pady=SPACING["sm"], highlightthickness=1, highlightbackground=TOKENS["accent"])
        self.title("Visor de logs")
        self.geometry("720x480")

        header = tk.Frame(self, bg=TOKENS["surface"])
        header.pack(fill="x", pady=(0, SPACING["sm"]))

        self.title_label = tk.Label(
            header,
            text="Logs",
            bg=TOKENS["surface"],
            fg=TOKENS["text"],
            font=fonts.card_title,
        )
        self.title_label.pack(side="left", anchor="w")

        self.copy_button = ActionButton(
            header,
            fonts,
            text="Copiar",
            command=self._copy_logs,
            variant="accent",
        )
        self.copy_button.pack(side="right")

        body = tk.Frame(self, bg=TOKENS["surface"])
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.text = tk.Text(
            body,
            bg=TOKENS["surface_alt"],
            fg=TOKENS["text"],
            insertbackground=TOKENS["accent"],
            font=fonts.meta_value,
            wrap="word",
            relief="flat",
            padx=SPACING["md"],
            pady=SPACING["sm"],
        )
        self.text.configure(state=tk.DISABLED)
        self.text.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = ttk.Scrollbar(
            body,
            orient="vertical",
            command=self.text.yview,
            style="Dark.Vertical.TScrollbar",
        )
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.text.configure(yscrollcommand=self.scrollbar.set)

    def open(self, service_name: str, logs: str) -> None:
        self.title_label.configure(text=f"Logs • {service_name}")
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, logs or "Sin registros disponibles.")
        self.text.configure(state=tk.DISABLED)
        self.text.yview_moveto(1.0)
        self.deiconify()
        self.focus_set()

    def _copy_logs(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.text.get("1.0", tk.END))
class DockerManagerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CapiAgentes Docker Manager")
        self.configure(bg=TOKENS["bg"])
        width, height = DEFAULT_WINDOW
        self.geometry(f"{width}x{height}")
        self.minsize(900, 580)

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.style.configure(
            "Dark.Vertical.TScrollbar",
            troughcolor=TOKENS["surface"],
            bordercolor=TOKENS["border"],
            background=TOKENS["border_strong"],
            arrowcolor=TOKENS["accent"],
            gripcount=0,
        )
        self.style.map(
            "Dark.Vertical.TScrollbar",
            background=[("active", TOKENS["accent"])],
            arrowcolor=[("active", TOKENS["text"])],
        )

        icon_path = resolve_asset("cocoCapi.ico")
        if icon_path.exists():
            try:
                self.iconbitmap(default=str(icon_path))
            except tk.TclError:
                png_path = resolve_asset("cocoCapi.png")
                if png_path.exists():
                    try:
                        self._icon_image = tk.PhotoImage(file=str(png_path))
                        self.iconphoto(False, self._icon_image)
                    except tk.TclError:
                        self._icon_image = None

        self.fonts = FontRegistry(self)
        self.service_definitions = load_service_definitions(PROJECT_ROOT)
        default_compose_path = PROJECT_ROOT / "docker-compose.yml"
        self.default_compose_path = default_compose_path if default_compose_path.exists() else None
        self._docker_clients: Dict[str, DockerClient] = {}
        self.docker = self._get_or_create_client(self.default_compose_path)

        self.state = DashboardState()
        self._service_states: Dict[str, ServiceRuntime] = {}
        self._operations: set[Tuple[Optional[str], str]] = set()
        self._loading_thread: Optional[threading.Thread] = None

        self.view = DashboardView(
            self,
            self.fonts,
            on_bulk_action=self.execute_bulk_action,
            on_service_action=self.execute_service_action,
            on_open_log=self.open_log_source,
            on_open_frontend=self.open_frontend,
        )
        self.view.pack(fill="both", expand=True)

        self.confirm_dialog = ConfirmDialog(self, self.fonts)
        self.logs_window = LogsWindow(self, self.fonts)

        self.view.set_log_sources(discover_log_sources())

        self.after(250, self._apply_window_theme)

        self.bind_all("<KeyPress-r>", lambda _e: self.refresh_services(show_loading=False))
        self.bind_all("<KeyPress-R>", lambda _e: self.refresh_services(show_loading=False))

        self.after(200, lambda: self.refresh_services(show_loading=True))
        self.after(REFRESH_INTERVAL_SECONDS * 1000, self._auto_refresh)

    def _apply_window_theme(self) -> None:
        if sys.platform != "win32":
            return
        try:
            import ctypes

            self.update_idletasks()
            raw_hwnd = int(self.winfo_id())
            hwnd = ctypes.windll.user32.GetParent(raw_hwnd) or raw_hwnd
            dwmapi = ctypes.windll.dwmapi
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36

            def to_colorref(value: str) -> int:
                value = value.lstrip("#")
                r = int(value[0:2], 16)
                g = int(value[2:4], 16)
                b = int(value[4:6], 16)
                return (b << 16) | (g << 8) | r

            enable = ctypes.c_int(1)
            dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(enable),
                ctypes.sizeof(enable),
            )

            caption = ctypes.c_int(to_colorref(TOKENS["surface_alt"]))
            text_color = ctypes.c_int(to_colorref(TOKENS["text"]))
            dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                DWMWA_CAPTION_COLOR,
                ctypes.byref(caption),
                ctypes.sizeof(caption),
            )
            dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                DWMWA_TEXT_COLOR,
                ctypes.byref(text_color),
                ctypes.sizeof(text_color),
            )
        except Exception:
            pass

    def _client_key(self, compose_path: Optional[Path]) -> str:
        if compose_path:
            try:
                return compose_path.resolve().as_posix()
            except OSError:
                return str(compose_path)
        return "__default__"

    def _normalise_compose_path(self, compose_path: Optional[Path]) -> Optional[Path]:
        if compose_path is None:
            return self.default_compose_path
        if not compose_path.is_absolute():
            return (PROJECT_ROOT / compose_path).resolve()
        return compose_path

    def _get_or_create_client(self, compose_path: Optional[Path]) -> DockerClient:
        normalised = self._normalise_compose_path(compose_path)
        key = self._client_key(normalised)
        if key not in self._docker_clients:
            workdir = normalised.parent if normalised else PROJECT_ROOT
            if normalised and not normalised.exists():
                log_debug(f"Compose file no encontrado: {normalised}")
            self._docker_clients[key] = DockerClient(
                normalised if normalised and normalised.exists() else normalised,
                default_workdir=workdir,
            )
        return self._docker_clients[key]

    def _docker_client_for(self, definition: ServiceDefinition) -> DockerClient:
        return self._get_or_create_client(definition.compose_file)

    def _group_definitions_by_compose(self) -> Dict[str, Tuple[Optional[Path], List[ServiceDefinition]]]:
        grouped: Dict[str, List[ServiceDefinition]] = {}
        paths: Dict[str, Optional[Path]] = {}
        for definition in self.service_definitions:
            compose_path = self._normalise_compose_path(definition.compose_file)
            key = self._client_key(compose_path)
            paths[key] = compose_path
            grouped.setdefault(key, []).append(definition)
        return {key: (paths[key], grouped[key]) for key in grouped}

    def _handle_stack_action(
        self,
        client: DockerClient,
        service: ServiceViewModel,
        action: str,
    ) -> Tuple[str, Optional[str], Optional[str]]:
        name = service.display_name
        details: Optional[str] = None
        error: Optional[str] = None
        if action == "start":
            client.start_all()
            message = f"{name} iniciado"
        elif action == "stop":
            client.stop_all()
            message = f"{name} detenido"
        elif action == "restart":
            client.restart_all()
            message = f"{name} reiniciado"
        elif action == "remove":
            details = client.down_all()
            message = f"{name} eliminado"
        elif action == "build":
            details = client.build_all()
            try:
                client.start_all()
                message = f"{name} reconstruido e iniciado"
            except DockerCommandError as start_exc:
                message = ""
                error = f"Build completado pero fallo al iniciar: {start_exc}"
        else:
            message = f"Accion {action} completada"
        return message, details, error



    def _auto_refresh(self) -> None:
        self.refresh_services(show_loading=False)
        self.after(REFRESH_INTERVAL_SECONDS * 1000, self._auto_refresh)

    def refresh_services(self, *, show_loading: bool) -> None:
        if self._loading_thread and self._loading_thread.is_alive():
            return

        if show_loading or not self.state.services:
            self.view.show_loading()

        def worker() -> None:
            log_debug("refresh worker start")
            runtime: Dict[str, Optional[ServiceRuntime]] = {}
            warnings: List[str] = []
            errors: List[str] = []
            for key, (compose_path, definitions) in self._group_definitions_by_compose().items():
                try:
                    client = self._get_or_create_client(compose_path)
                    subset_runtime, warn = client.fetch_runtime(definitions)
                    runtime.update(subset_runtime)
                    if warn:
                        warnings.append(warn)
                except DockerCommandError as exc:
                    errors.append(str(exc))
                    log_debug(f"refresh worker error ({key}): {exc}")
            warning = "\n".join(warnings) if warnings else None
            error = "\n".join(errors) if errors else None
            timestamp = time.time()
            self.after(0, lambda: self._apply_refresh(runtime, error, warning, timestamp))

        self._loading_thread = threading.Thread(target=worker, daemon=True)
        self._loading_thread.start()

    def _apply_refresh(
        self,
        runtime_map: Dict[str, Optional[ServiceRuntime]],
        error: Optional[str],
        warning: Optional[str],
        timestamp: float,
    ) -> None:
        services: List[ServiceViewModel] = []
        for definition in self.service_definitions:
            runtime = runtime_map.get(definition.service_id)
            if runtime:
                self._service_states[definition.service_id] = runtime
            else:
                previous = self._service_states.get(definition.service_id)
                runtime = ServiceRuntime(
                    status="DETENIDO",
                    uptime_seconds=0,
                    restarts=previous.restarts if previous else 0,
                    container_id=None,
                    last_seen=time.time(),
                    error=previous.error if previous else None,
                )
                self._service_states[definition.service_id] = runtime
            services.append(ServiceViewModel(definition=definition, runtime=runtime))

        log_debug(f"apply_refresh -> error={error} warning={warning} services={len(services)}")
        for svc in services:
            log_debug(f"service {svc.definition.service_id} status {svc.status} container {svc.runtime.container_id}")
        self.state.services = services
        if error:
            self.view.show_error(error)
            self.view.update_message(f"Error al sincronizar: {error}")
        else:
            self.state.last_updated = timestamp
            self.view.show_error(None)
            if warning:
                self.view.update_message(f"Estado sincronizado con advertencia: {warning}")
            else:
                self.view.update_message("Estado sincronizado con Docker")

        active = sum(1 for svc in services if svc.status == "UP")
        total = len(services)

        self.view.set_services(services)
        self.view.update_counts(active, total)
        self.view.update_last_updated(self.state.last_updated)
        self.view.set_log_sources(discover_log_sources())

    def execute_service_action(self, service: ServiceViewModel, action: str) -> None:
        service_id = service.definition.service_id
        if action == "remove":
            self._log_event(f"Confirmar eliminacion de {service.display_name}")
            self.confirm_dialog.open(service.display_name, lambda: self._dispatch_service_command(service, action))
            return
        if action == "open":
            if service.url:
                webbrowser.open(service.url)
                self.view.update_message(f"Abriendo {service.url}")
                self.view.show_error(None)
                self._log_event(f"{service.display_name}: abriendo {service.url}")
            else:
                message = "El servicio no tiene URL configurada"
                self.view.show_error(message, duration=5000)
                self.view.update_message(message)
                self._log_event(f"[ERROR] {service.display_name}: {message}")
            return
        self._dispatch_service_command(service, action)


    def _dispatch_service_command(self, service: ServiceViewModel, action: str) -> None:

        service_id = service.definition.service_id

        if (service_id, action) in self._operations:

            return

        self._operations.add((service_id, action))

        self.view.set_processing(service_id, True)

        self.view.update_message(f"Ejecutando {action} en {service.display_name}")

        self._log_event(f"{service.display_name}: {action.upper()} en progreso")



        def worker() -> None:

            message = ""

            details: Optional[str] = None

            error: Optional[str] = None

            client = self._docker_client_for(service.definition)

            service_kind = (service.definition.kind or "").lower()

            try:

                if service_kind in {"elastic-stack", "stack"}:

                    message, details, stack_error = self._handle_stack_action(client, service, action)

                    if stack_error:

                        error = stack_error

                elif action == "start":

                    client.start_service(service.definition)

                    message = f"{service.display_name} iniciado"

                elif action == "stop":

                    client.stop_service(service.definition)

                    message = f"{service.display_name} detenido"

                elif action == "restart":

                    client.restart_service(service.definition)

                    message = f"{service.display_name} reiniciado"

                elif action == "remove":

                    client.remove_service(service.definition)

                    message = f"{service.display_name} eliminado"

                elif action == "build":

                    details = client.build_service(service.definition)

                    if error is None:

                        try:

                            client.start_service(service.definition)

                            message = f"{service.display_name} reconstruido e iniciado"

                        except DockerCommandError as start_exc:

                            error = f"Build completado pero fallo al iniciar: {start_exc}"

                            message = ""

                else:

                    message = f"Accion {action} completada"

            except DockerCommandError as exc:

                error = str(exc)

                message = ""

            self.after(0, lambda: self._complete_operation(service_id, action, message, error, details))



        threading.Thread(target=worker, daemon=True).start()



    def execute_bulk_action(self, action: str) -> None:
        key = (None, action)
        if key in self._operations:
            return
        self._operations.add(key)
        self.view.set_processing(None, True)
        self.view.update_message(f"Ejecutando accion global: {action}")
        self._log_event(f"Accion global en progreso: {action}")

        def worker() -> None:
            details: Optional[str] = None
            try:
                groups = list(self._group_definitions_by_compose().items())
                if not groups:
                    groups = [(self._client_key(self.default_compose_path), (self.default_compose_path, []))]
                for key, (compose_path, _) in groups:
                    client = self._get_or_create_client(compose_path)
                    log_debug(f"bulk action {action} -> {key}")
                    if action == "start":
                        client.start_all()
                    elif action == "stop":
                        client.stop_all()
                    elif action == "restart":
                        client.restart_all()
                if action == "start":
                    message = "Se iniciaron todos los servicios"
                elif action == "stop":
                    message = "Se detuvieron todos los servicios"
                elif action == "restart":
                    message = "Se reiniciaron todos los servicios"
                else:
                    message = "Accion completada"
                error: Optional[str] = None
            except DockerCommandError as exc:
                error = str(exc)
                message = ""
            self.after(0, lambda: self._complete_operation(None, action, message, error, details))

        threading.Thread(target=worker, daemon=True).start()


    def _complete_operation(
        self,
        service_id: Optional[str],
        action: str,
        message: str,
        error: Optional[str],
        details: Optional[str] = None,
    ) -> None:
        self._operations.discard((service_id, action))
        self.view.set_processing(service_id, False)
        if error:
            self.view.show_error(error, duration=6000)
            self.view.update_message(f"Error: {error}")
            self._log_event(f"[ERROR] {error}")
            if details:
                self._log_raw(details, header=f"Salida Docker ({action})")
        else:
            self.view.show_error(None)
            if message:
                self.view.update_message(message)
                self._log_event(message)
            if details:
                self._log_raw(details, header=f"Salida Docker ({action})")

        self.after(150, lambda: self.refresh_services(show_loading=False))




    def open_log_source(self, label: str, path: Path) -> None:
        resolved_key = str(path.resolve())
        key: Tuple[str, str] = (resolved_key, "log_source")
        if key in self._operations:
            return
        self._operations.add(key)
        self._log_event(f"Lectura de log solicitada: {label}")
        self.view.update_message(f"Abrir log: {label}")
        self.view.show_error(None)

        def worker() -> None:
            try:
                content = tail_file(path, FILE_LOG_TAIL_LINES)
                error: Optional[str] = None
            except FileNotFoundError:
                content = ""
                error = f"No se encontró el log en {path}"
            except OSError as exc:
                content = ""
                error = f"No se pudo leer el log ({exc})"
            self.after(0, lambda: self._complete_open_log_source(key, label, content, error))

        threading.Thread(target=worker, daemon=True).start()

    def _complete_open_log_source(
        self,
        key: Tuple[str, str],
        label: str,
        content: str,
        error: Optional[str],
    ) -> None:
        self._operations.discard(key)
        if error:
            self.view.show_error(error, duration=6000)
            self.view.update_message(error)
            self._log_event(f"[ERROR] {error}")
            return
        self.view.show_error(None)
        self.logs_window.open(label, content)
        self.view.update_message(f"Mostrando {label}")
        self._log_event(f"Log visualizado: {label}")


    def open_frontend(self) -> None:
        frontend = next((svc for svc in self.state.services if svc.definition.service_id == "frontend" and svc.url), None)
        url = frontend.url if frontend and frontend.url else "http://localhost:3000"
        try:
            webbrowser.open(url)
            self.view.update_message(f"Abriendo {url}")
            self.view.show_error(None)
            self._log_event(f"Frontend abierto en {url}")
        except Exception as exc:
            message = f"No se pudo abrir el frontend: {exc}"
            self.view.show_error(message)
            self._log_event(f"[ERROR] {message}")

    def _log_event(self, message: str) -> None:
        if not message:
            return
        log_debug(message)
        self.view.append_log(message, annotate=True)

    def _log_raw(self, text: str, *, header: str = "Salida Docker") -> None:
        if not text:
            return
        self.view.append_log(header, annotate=True)
        self.view.append_log_raw(text)


def main() -> None:
    app = DockerManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()




















