"""Tests for /api/metrics voice snapshot."""
import json
import os
import sys
import tempfile
import types
from pathlib import Path
from typing import Dict, List

from fastapi.testclient import TestClient
from prometheus_client.core import Metric

# ---------------------------------------------------------------------------
# Stub Google modules so that importing src.api.main does not require SDKs
# ---------------------------------------------------------------------------

def _ensure_module(name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__path__ = []  # Mark as package
    sys.modules[name] = module
    return module

if "google" not in sys.modules:
    google_pkg = _ensure_module("google")
else:
    google_pkg = sys.modules["google"]
    if not hasattr(google_pkg, "__path__"):
        google_pkg.__path__ = []

auth_pkg = _ensure_module("google.auth")
setattr(google_pkg, "auth", auth_pkg)
transport_pkg = _ensure_module("google.auth.transport")
setattr(auth_pkg, "transport", transport_pkg)
requests_pkg = _ensure_module("google.auth.transport.requests")
setattr(transport_pkg, "requests", requests_pkg)


class _DummyRequest:
    def __call__(self, *args, **kwargs):
        return None


setattr(requests_pkg, "Request", _DummyRequest)

oauth_pkg = _ensure_module("google.oauth2")
setattr(google_pkg, "oauth2", oauth_pkg)
credentials_pkg = _ensure_module("google.oauth2.credentials")
setattr(oauth_pkg, "credentials", credentials_pkg)


class _DummyCredentials:
    def __init__(
        self,
        token: str | None = None,
        refresh_token: str | None = None,
        token_uri: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        scopes: List[str] | None = None,
        expiry=None,
        **_: object,
    ) -> None:
        self.token = token or "token"
        self.refresh_token = refresh_token or "refresh"
        self.token_uri = token_uri
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = list(scopes or [])
        self.expired = False
        self.valid = True
        self._expiry = expiry.isoformat() if hasattr(expiry, "isoformat") else expiry

    def refresh(self, request: object) -> None:  # noqa: ARG002
        self.expired = False
        self.valid = True

    def to_json(self) -> str:
        return json.dumps(
            {
                "token": self.token,
                "refresh_token": self.refresh_token,
                "expiry": self._expiry,
                "scopes": self.scopes,
            }
        )


setattr(credentials_pkg, "Credentials", _DummyCredentials)

api_client_pkg = _ensure_module("googleapiclient")
_discovery_pkg = _ensure_module("googleapiclient.discovery")
setattr(api_client_pkg, "discovery", _discovery_pkg)


def _dummy_build(service_name: str, version: str, credentials=None, cache_discovery=False):  # noqa: D401, ARG002
    return {
        "service": service_name,
        "version": version,
        "credentials": credentials,
        "cache": cache_discovery,
    }


setattr(_discovery_pkg, "build", _dummy_build)
_errors_pkg = _ensure_module("googleapiclient.errors")
setattr(api_client_pkg, "errors", _errors_pkg)


class _DummyHttpError(Exception):
    pass


setattr(_errors_pkg, "HttpError", _DummyHttpError)
_http_pkg = _ensure_module("googleapiclient.http")
setattr(api_client_pkg, "http", _http_pkg)


class _DummyMediaIoBaseUpload:
    def __init__(self, *args, **kwargs):  # noqa: D401, ARG002
        self.args = args
        self.kwargs = kwargs


setattr(_http_pkg, "MediaIoBaseUpload", _DummyMediaIoBaseUpload)

# Stub internal google STT/TTS clients to avoid cloud dependencies
voice_google_stt = types.ModuleType("src.voice.google_stt")


class _StubSpeechClient:
    def __init__(self, settings):  # noqa: D401, ARG002
        self.settings = settings

    async def stream_transcribe(self, audio_chunks, **_: object):  # noqa: D401, ARG002
        if False:
            yield None


setattr(voice_google_stt, "GoogleSpeechClient", _StubSpeechClient)
sys.modules["src.voice.google_stt"] = voice_google_stt

voice_google_tts = types.ModuleType("src.voice.google_tts")


class _StubTTSClient:
    def __init__(self, settings):  # noqa: D401, ARG002
        self.settings = settings

    async def synthesize(self, **_: object):  # noqa: D401, ARG002
        return "", "audio/mpeg"


setattr(voice_google_tts, "GoogleTextToSpeechClient", _StubTTSClient)
sys.modules["src.voice.google_tts"] = voice_google_tts

# ---------------------------------------------------------------------------
# Minimal Google OAuth env + token store for main app import
# ---------------------------------------------------------------------------
_token_dir = tempfile.mkdtemp(prefix="voice-metrics-test-")
_token_path = Path(_token_dir) / "google_token.json"
_token_path.write_text(
    json.dumps(
        {
            "refresh_token": "refresh",
            "access_token": "access",
            "expiry": None,
        }
    ),
    encoding="utf-8",
)

os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-secret")
os.environ.setdefault(
    "GOOGLE_OAUTH_SCOPES",
    "https://www.googleapis.com/auth/gmail.modify,https://www.googleapis.com/auth/drive.file",
)
os.environ.setdefault("GOOGLE_TOKEN_STORE", str(_token_path))
os.environ.setdefault("GOOGLE_AGENT_EMAIL", "agente.g@test")

# ---------------------------------------------------------------------------
# After stubs/env are ready we can import the app and voice metrics
# ---------------------------------------------------------------------------
from src.api.main import app
from src.voice import metrics as voice_metrics


class DummyMetric:
    def __init__(self, metric_name: str, metric_type: str, samples: List[Dict]):
        self.metric_name = metric_name
        self.metric_type = metric_type
        self.samples = samples

    def collect(self):
        metric = Metric(self.metric_name, f"dummy {self.metric_type}", self.metric_type)
        for sample in self.samples:
            metric.add_sample(
                sample.get("name", self.metric_name),
                sample.get("labels", {}),
                sample.get("value", 0.0),
            )
        return [metric]


def test_metrics_endpoint_includes_voice_snapshot(monkeypatch):
    monkeypatch.setattr(
        voice_metrics,
        "VOICE_ACTIVE_STREAMS",
        DummyMetric(
            "voice_active_streams",
            "gauge",
            samples=[{"name": "voice_active_streams", "labels": {}, "value": 2.0}],
        ),
    )
    monkeypatch.setattr(
        voice_metrics,
        "VOICE_STREAM_BYTES",
        DummyMetric(
            "voice_stream_bytes_total",
            "counter",
            samples=[{"name": "voice_stream_bytes_total", "labels": {}, "value": 1234.0}],
        ),
    )
    monkeypatch.setattr(
        voice_metrics,
        "VOICE_STREAM_WARNINGS",
        DummyMetric(
            "voice_stream_warnings_total",
            "counter",
            samples=[
                {
                    "name": "voice_stream_warnings_total",
                    "labels": {"reason": "duration_exceeded"},
                    "value": 1.0,
                }
            ],
        ),
    )
    monkeypatch.setattr(
        voice_metrics,
        "VOICE_TURNS",
        DummyMetric(
            "voice_turns_total",
            "counter",
            samples=[
                {
                    "name": "voice_turns_total",
                    "labels": {"result": "success"},
                    "value": 3.0,
                }
            ],
        ),
    )
    monkeypatch.setattr(
        voice_metrics,
        "VOICE_TURN_LATENCY",
        DummyMetric(
            "voice_turn_latency_milliseconds",
            "histogram",
            samples=[
                {
                    "name": "voice_turn_latency_milliseconds_count",
                    "labels": {},
                    "value": 3.0,
                },
                {
                    "name": "voice_turn_latency_milliseconds_sum",
                    "labels": {},
                    "value": 1500.0,
                },
            ],
        ),
    )
    monkeypatch.setattr(
        voice_metrics,
        "VOICE_STREAM_DURATION",
        DummyMetric(
            "voice_stream_duration_seconds",
            "histogram",
            samples=[
                {
                    "name": "voice_stream_duration_seconds_count",
                    "labels": {},
                    "value": 4.0,
                },
                {
                    "name": "voice_stream_duration_seconds_sum",
                    "labels": {},
                    "value": 10.0,
                },
            ],
        ),
    )

    client = TestClient(app)
    response = client.get("/api/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert "voice" in payload

    voice = payload["voice"]
    assert voice["active_streams"] == 2.0
    assert voice["stream_bytes_total"] == 1234.0
    assert voice["stream_warnings"]["duration_exceeded"] == 1.0
    assert voice["turns"]["success"] == 3.0
    assert voice["turn_latency_ms"]["count"] == 3.0
    assert voice["turn_latency_ms"]["sum"] == 1500.0
    assert voice["stream_duration_seconds"]["count"] == 4.0
    assert voice["stream_duration_seconds"]["sum"] == 10.0
