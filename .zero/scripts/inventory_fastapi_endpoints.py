#!/usr/bin/env python3
"""Inventory FastAPI endpoints and dump metadata into /.zero/artifacts."""
from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent
while PROJECT_ROOT and not (PROJECT_ROOT / 'Backend' / 'src').exists():
    if PROJECT_ROOT.parent == PROJECT_ROOT:
        raise SystemExit('Unable to locate project root from ' + str(SCRIPT_PATH))
    PROJECT_ROOT = PROJECT_ROOT.parent
BACKEND_SRC = PROJECT_ROOT / 'Backend' / 'src'
ARTIFACT_PATH = PROJECT_ROOT / '.zero' / 'artifacts' / 'fastapi-endpoints.json'

@dataclass
class RouterInfo:
    name: str
    prefix: str


def _literal_to_str(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):  # f"/path"
        parts: List[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                return None
        return ''.join(parts)
    return None


def _extract_router_info(tree: ast.AST) -> Dict[str, RouterInfo]:
    routers: Dict[str, RouterInfo] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                call = node.value
                func = call.func
                if isinstance(func, ast.Name) and func.id == 'APIRouter':
                    prefix = ''
                    for kw in call.keywords:
                        if kw.arg == 'prefix':
                            value = _literal_to_str(kw.value)
                            if value is not None:
                                prefix = value
                    routers[target.id] = RouterInfo(name=target.id, prefix=prefix)
    return routers


def _extract_endpoints(path: Path) -> List[Dict[str, object]]:
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'))
    except Exception:
        return []

    routers = _extract_router_info(tree)
    endpoints: List[Dict[str, object]] = []

    class Visitor(ast.NodeVisitor):
        def _process(self, node) -> None:
            for decorator in getattr(node, 'decorator_list', []):
                if not isinstance(decorator, ast.Call):
                    continue
                func = decorator.func
                if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                    router_name = func.value.id
                    if router_name not in routers:
                        continue
                    method = func.attr.upper()
                    path_value: Optional[str] = None
                    if decorator.args:
                        path_value = _literal_to_str(decorator.args[0])
                    if path_value is None:
                        for kw in decorator.keywords:
                            if kw.arg in {'path', 'route'}:
                                path_value = _literal_to_str(kw.value)
                                break
                    if path_value is None:
                        path_value = ''
                    prefix = routers[router_name].prefix or ''
                    full_path = (prefix.rstrip('/') + '/' + path_value.lstrip('/')).replace('//', '/') if path_value else prefix or '/'
                    tags: List[str] = []
                    for kw in decorator.keywords:
                        if kw.arg == 'tags' and isinstance(kw.value, (ast.List, ast.Tuple)):
                            tag_values: List[str] = []
                            for elt in kw.value.elts:
                                tag = _literal_to_str(elt)
                                if tag:
                                    tag_values.append(tag)
                            tags.extend(tag_values)
                    endpoints.append({
                        'file': str(path.relative_to(PROJECT_ROOT)),
                        'router': router_name,
                        'method': method,
                        'path': full_path,
                        'tags': tags,
                        'handler': node.name,
                    })
            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._process(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._process(node)

    Visitor().visit(tree)
    return endpoints


def gather_endpoints() -> List[Dict[str, object]]:
    paths = list((BACKEND_SRC / 'api').rglob('*.py'))
    paths += list((BACKEND_SRC / 'graph_canva').rglob('*.py'))
    paths += list((BACKEND_SRC / 'presentation').rglob('*.py'))
    endpoints: List[Dict[str, object]] = []
    for path in sorted(paths):
        endpoints.extend(_extract_endpoints(path))
    endpoints.sort(key=lambda item: (item['path'], item['method'], item['file']))
    return endpoints


def main() -> None:
    endpoints = gather_endpoints()
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps({'endpoints': endpoints}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"[inventory-fastapi] wrote {len(endpoints)} endpoints to {ARTIFACT_PATH}")


if __name__ == '__main__':
    main()
