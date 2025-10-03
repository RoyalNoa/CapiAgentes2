"""Endpoints para inspeccionar archivos de sesiones en ia_workspace/data."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from src.infrastructure.workspace.session_storage import resolve_workspace_root

router = APIRouter(prefix="/api/session-files", tags=["session-files"])

_DATA_SUBDIR = "data"


def _get_data_root() -> Path:
    root = resolve_workspace_root()
    data_root = root / _DATA_SUBDIR
    data_root.mkdir(parents=True, exist_ok=True)
    return data_root


def _list_directory(directory: Path, relative_to: Path) -> List[Dict[str, Any]]:
    """Return immediate children metadata for the requested directory."""

    entries: List[Dict[str, Any]] = []
    try:
        iterator = sorted(
            directory.iterdir(),
            key=lambda item: (item.is_file(), item.name.lower()),
        )
    except FileNotFoundError:
        return []

    for entry in iterator:
        stat_result = entry.stat()
        node: Dict[str, Any] = {
            "name": entry.name,
            "path": entry.relative_to(relative_to).as_posix(),
            "type": "directory" if entry.is_dir() else "file",
            "modified_at": datetime.fromtimestamp(stat_result.st_mtime).isoformat(),
        }
        if entry.is_dir():
            try:
                has_children = next(entry.iterdir(), None) is not None
            except OSError:
                has_children = False
            node["has_children"] = has_children
        else:
            node["size_bytes"] = stat_result.st_size
        entries.append(node)
    return entries


@router.get("/tree")
async def get_session_files_tree(
    path: str | None = Query(
        default=None,
        description="Ruta relativa dentro de ia_workspace/data para listar",
    ),
) -> Dict[str, Any]:
    """Retorna el listado inmediato del directorio solicitado bajo ia_workspace/data."""

    data_root = _get_data_root().resolve()

    target_dir = data_root
    if path:
        candidate = (data_root / path).resolve()
        try:
            candidate.relative_to(data_root)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Ruta fuera del directorio permitido.") from exc
        if not candidate.exists() or not candidate.is_dir():
            raise HTTPException(status_code=404, detail="Directorio no encontrado.")
        target_dir = candidate

    entries = _list_directory(target_dir, data_root)
    relative_path = "" if target_dir == data_root else target_dir.relative_to(data_root).as_posix()
    return {
        "root": data_root.as_posix(),
        "path": relative_path,
        "entries": entries,
    }


def _resolve_requested_file(path: str) -> Path:
    if not path:
        raise HTTPException(status_code=400, detail="Se requiere el parámetro 'path'.")

    data_root = _get_data_root().resolve()
    candidate = (data_root / path).resolve()

    try:
        candidate.relative_to(data_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Ruta fuera del directorio permitido.") from exc

    if not candidate.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    if candidate.is_dir():
        raise HTTPException(status_code=400, detail="La ruta indicada es un directorio.")
    return candidate


@router.get("/file")
async def read_session_file(path: str = Query(..., description="Ruta relativa dentro de ia_workspace/data")) -> Dict[str, Any]:
    """Lee el contenido textual de un archivo dentro de ia_workspace/data."""
    file_path = _resolve_requested_file(path)

    size_bytes = file_path.stat().st_size
    if size_bytes > 512_000:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande para previsualizar.")

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = file_path.read_text(encoding="utf-8", errors="replace")

    return {
        "path": file_path.relative_to(_get_data_root()).as_posix(),
        "size_bytes": size_bytes,
        "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
        "content": content,
    }


def _prune_empty_parents(path: Path, stop: Path) -> None:
    current = path
    while current.parent != current and current.parent != stop:
        current = current.parent
        if current == stop:
            break
        try:
            current.rmdir()
        except OSError:
            break


@router.delete("/file")
async def delete_session_file(path: str = Query(..., description="Ruta relativa dentro de ia_workspace/data")) -> Dict[str, Any]:
    """Elimina un archivo dentro de ia_workspace/data."""
    file_path = _resolve_requested_file(path)

    try:
        file_path.unlink()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    except PermissionError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=423, detail=f"No se pudo borrar el archivo: {exc}") from exc

    data_root = _get_data_root().resolve()
    _prune_empty_parents(file_path, data_root)

    return {
        "deleted": True,
        "path": file_path.relative_to(data_root).as_posix(),
    }
