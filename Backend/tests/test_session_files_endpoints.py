from pathlib import Path

from fastapi.testclient import TestClient

from src.api.main import app


def _find_entry(entries, name):
    for entry in entries:
        if entry["name"] == name:
            return entry
    return None


def test_session_files_tree_and_file(tmp_path, monkeypatch):
    workspace_root = tmp_path / "ia_workspace"
    data_root = workspace_root / "data"
    session_dir = data_root / "sessions" / "session_demo"
    session_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = session_dir / "session_demo.json"
    manifest_path.write_text("{\n  \"session_id\": \"demo\"\n}", encoding="utf-8")

    export_file = session_dir / "capi_DataB" / "result.json"
    export_file.parent.mkdir(parents=True, exist_ok=True)
    export_file.write_text("{\"rows\": []}", encoding="utf-8")

    log_dir = data_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "run.log"
    log_file.write_text("log entry", encoding="utf-8")

    monkeypatch.setenv("CAPI_IA_WORKSPACE", str(workspace_root))

    with TestClient(app) as client:
        tree_response = client.get("/api/session-files/tree")
        assert tree_response.status_code == 200
        payload = tree_response.json()

        assert payload["root"].endswith("ia_workspace/data")
        sessions_entry = _find_entry(payload["entries"], "sessions")
        assert sessions_entry is not None and sessions_entry["type"] == "directory"
        assert sessions_entry.get("has_children") is True

        sessions_tree = client.get(
            "/api/session-files/tree",
            params={"path": "sessions"},
        ).json()
        session_demo = _find_entry(sessions_tree["entries"], "session_demo")
        assert session_demo is not None and session_demo["type"] == "directory"

        session_demo_tree = client.get(
            "/api/session-files/tree",
            params={"path": "sessions/session_demo"},
        ).json()
        manifest_entry = _find_entry(session_demo_tree["entries"], "session_demo.json")
        assert manifest_entry is not None
        assert manifest_entry["type"] == "file"
        assert manifest_entry["size_bytes"] == manifest_path.stat().st_size

        export_entry = _find_entry(session_demo_tree["entries"], "capi_DataB")
        assert export_entry is not None and export_entry["type"] == "directory"
        data_b_tree = client.get(
            "/api/session-files/tree",
            params={"path": "sessions/session_demo/capi_DataB"},
        ).json()
        datab_file_entry = _find_entry(data_b_tree["entries"], "result.json")
        assert datab_file_entry is not None

        file_response = client.get(
            "/api/session-files/file",
            params={"path": "sessions/session_demo/session_demo.json"},
        )
        assert file_response.status_code == 200
        file_payload = file_response.json()
        assert file_payload["path"] == "sessions/session_demo/session_demo.json"
        assert "demo" in file_payload["content"]

        missing_response = client.get(
            "/api/session-files/file",
            params={"path": "sessions/session_demo/missing.json"},
        )
        assert missing_response.status_code == 404

        delete_response = client.delete(
            "/api/session-files/file",
            params={"path": "sessions/session_demo/capi_DataB/result.json"},
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["deleted"] is True
        assert not export_file.exists()

        session_demo_after = client.get(
            "/api/session-files/tree",
            params={"path": "sessions/session_demo"},
        ).json()
        capi_datab_after = _find_entry(session_demo_after["entries"], "capi_DataB")
        assert capi_datab_after is None or not capi_datab_after.get("has_children")
