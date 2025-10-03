#!/usr/bin/env python3
"""Inspect frontend source files to detect API/WS usage and dump to /.zero/artifacts."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Dict

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent
while PROJECT_ROOT and not (PROJECT_ROOT / 'Frontend' / 'src').exists():
    if PROJECT_ROOT.parent == PROJECT_ROOT:
        raise SystemExit('Unable to locate project root from ' + str(SCRIPT_PATH))
    PROJECT_ROOT = PROJECT_ROOT.parent
FRONTEND_SRC = PROJECT_ROOT / 'Frontend' / 'src'
ARTIFACT_PATH = PROJECT_ROOT / '.zero' / 'artifacts' / 'frontend-api-usage.json'

API_PATTERN = re.compile(r'(/api/[A-Za-z0-9_\-./{}?=&]+)')
WS_PATTERN = re.compile(r'(ws[s]?://[^"\s]+|/api/[A-Za-z0-9_\-./{}?=&]+)')


def _scan_file(path: Path) -> List[Dict[str, object]]:
    try:
        text = path.read_text(encoding='utf-8')
    except Exception:
        return []

    entries: List[Dict[str, object]] = []
    lines = text.splitlines()
    for idx, line in enumerate(lines, 1):
        if '/api/' not in line and 'WebSocket' not in line and 'ws://' not in line and 'wss://' not in line:
            continue
        line_lower = line.lower()
        kind = 'other'
        if 'fetch' in line_lower:
            kind = 'fetch'
        elif 'axios' in line_lower:
            kind = 'axios'
        elif 'websocket' in line_lower:
            kind = 'websocket'
        api_matches = API_PATTERN.findall(line)
        ws_matches = []
        if kind == 'websocket':
            ws_matches = WS_PATTERN.findall(line)
        entries.append({
            'file': str(path.relative_to(PROJECT_ROOT)),
            'line': idx,
            'kind': kind,
            'api_paths': api_matches,
            'ws_targets': ws_matches,
            'snippet': line.strip(),
        })
    return entries


def gather_usage() -> List[Dict[str, object]]:
    entries: List[Dict[str, object]] = []
    for path in sorted(FRONTEND_SRC.rglob('*.ts*')):
        entries.extend(_scan_file(path))
    entries.sort(key=lambda item: (item['file'], item['line']))
    return entries


def main() -> None:
    usage = gather_usage()
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps({'usage': usage}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"[inventory-frontend] wrote {len(usage)} usage records to {ARTIFACT_PATH}")


if __name__ == '__main__':
    main()
