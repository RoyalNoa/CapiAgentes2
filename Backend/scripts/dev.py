#!/usr/bin/env python3
"""
Backend Development Script
Provides development utilities for the backend service
"""

import json

import sys
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Add src to Python path
backend_root = Path(__file__).parent.parent
repo_root = backend_root.parent
sys.path.insert(0, str(backend_root))


def run_server(port: int = 8000, reload: bool = True, log_level: str = "info") -> None:
    """Run the FastAPI development server."""
    cmd = [
        "uvicorn",
        "src.api.main:app",
        f"--port={port}",
        f"--log-level={log_level}",
        "--host=0.0.0.0",
    ]

    if reload:
        cmd.append("--reload")

    print(f"-> Starting backend server on port {port}")
    print(f"-> API docs: http://localhost:{port}/docs")
    print(f"-> Workspace: http://localhost:{port}/api/workspace/health")

    subprocess.run(cmd, cwd=backend_root, check=False)


def run_tests(verbose: bool = False, pattern: str = "test_*.py") -> bool:
    """Run backend tests."""
    cmd = ["python", "-m", "pytest"]

    if verbose:
        cmd.append("-v")

    cmd.extend(["tests/", "-k", pattern])

    print("-> Running backend tests")
    result = subprocess.run(cmd, cwd=backend_root, check=False)
    return result.returncode == 0


def check_workspace() -> bool:
    """Check AI Workspace health."""
    try:
        from src.agents.workspace_agent import WorkspaceAgent

        agent = WorkspaceAgent()
        summary = agent.get_workspace_summary()

        print("-> AI Workspace Status:")
        print(f"   Files: {summary['files']['total_files']}")
        print(f"   Knowledge: {summary['knowledge_base']['total_documents']} documents")
        print(f"   Memory: {summary['memory']['total_conversations']} conversations")
        print(f"   Workspace: {summary['workspace_root']}")

    except Exception as exc:
        print(f"Workspace check failed: {exc}")
        return False

    return True


def export_graph(
    *,
    output_dir: Optional[str] = None,
    basename: str = "mermaid_output",
    skip_png: bool = False,
    draw_method: Optional[str] = None,
    enable_dynamic: bool = True,
) -> Dict[str, Path]:
    """Export the LangGraph graph to Mermaid and optional PNG artifacts."""
    from src.infrastructure.langgraph.graph_runtime import LangGraphRuntime

    resolved_dir = Path(output_dir) if output_dir else repo_root
    resolved_dir.mkdir(parents=True, exist_ok=True)

    config = {"enable_dynamic_graph": enable_dynamic}
    runtime = LangGraphRuntime(config=config)
    graph = runtime.graph or runtime.static_graph
    if graph is None:
        runtime.close()
        raise RuntimeError("LangGraph runtime graph not initialized")

    graph_obj = graph.get_graph()
    mermaid_text = graph_obj.draw_mermaid()

    mmd_path = resolved_dir / f"{basename}.mmd"
    mmd_path.write_text(mermaid_text, encoding="utf-8")

    metadata: Dict[str, object] = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "output_dir": str(resolved_dir),
        "basename": basename,
        "dynamic_enabled": bool(runtime.dynamic_manager),
    }

    try:
        if runtime.dynamic_manager:
            metadata["graph_info"] = runtime.dynamic_manager.builder.get_graph_info()
        else:
            metadata["graph_info"] = runtime.builder.get_graph_metadata()
    except Exception as exc:  # pragma: no cover - best effort metadata
        metadata["graph_info_error"] = str(exc)

    meta_path = resolved_dir / f"{basename}.meta.json"
    meta_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

    exports: Dict[str, Path] = {"mermaid": mmd_path, "metadata": meta_path}

    if not skip_png:
        png_bytes = None
        method_enum = None
        if draw_method:
            try:
                from langchain_core.runnables.graph import MermaidDrawMethod

                method_enum = {
                    "api": MermaidDrawMethod.API,
                    "pyppeteer": MermaidDrawMethod.PYPPETEER,
                }.get(draw_method)
            except Exception as exc:  # pragma: no cover - optional dependency
                print(f"PNG render backend unavailable: {exc}")
                method_enum = None
        try:
            if method_enum is not None:
                png_bytes = graph_obj.draw_mermaid_png(draw_method=method_enum)
            else:
                png_bytes = graph_obj.draw_mermaid_png()
        except Exception as exc:
            if draw_method is None:
                try:
                    from langchain_core.runnables.graph import MermaidDrawMethod

                    png_bytes = graph_obj.draw_mermaid_png(draw_method=MermaidDrawMethod.PYPPETEER)
                except Exception as fallback_exc:
                    print(f"PNG export skipped: {exc} (fallback also failed: {fallback_exc})")
            else:
                print(f"PNG export skipped: {exc}")
        if png_bytes:
            png_path = resolved_dir / f"{basename}.png"
            png_path.write_bytes(png_bytes)
            exports["png"] = png_path

    runtime.close()
    return exports


def install_dependencies() -> None:
    """Install backend dependencies."""
    subprocess.run(["pip", "install", "-r", "requirements.txt"], cwd=backend_root, check=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backend Development Tools")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Server command
    server_parser = subparsers.add_parser("serve", help="Run development server")
    server_parser.add_argument("--port", type=int, default=8000, help="Server port")
    server_parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    server_parser.add_argument("--log-level", default="info", help="Log level")

    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    test_parser.add_argument("-k", "--pattern", default="test_*.py", help="Test pattern")

    # Workspace command
    subparsers.add_parser("workspace", help="Check AI Workspace status")

    # Install command
    subparsers.add_parser("install", help="Install dependencies")

    # Graph export command
    graph_parser = subparsers.add_parser("graph", help="Export LangGraph visuals")
    graph_parser.add_argument(
        "--output-dir",
        default=str(repo_root),
        help="Directory where graph artifacts will be written",
    )
    graph_parser.add_argument(
        "--basename",
        default="mermaid_output",
        help="Base filename for exported artifacts",
    )
    graph_parser.add_argument(
        "--skip-png",
        action="store_true",
        help="Do not render PNG output",
    )
    graph_parser.add_argument(
        "--draw-method",
        choices=["api", "pyppeteer"],
        help="PNG rendering backend to force",
    )
    graph_parser.add_argument(
        "--static",
        action="store_true",
        help="Export using the static graph instead of dynamic runtime",
    )

    args = parser.parse_args()

    if args.command == "serve":
        run_server(args.port, not args.no_reload, args.log_level)
    elif args.command == "test":
        success = run_tests(args.verbose, args.pattern)
        sys.exit(0 if success else 1)
    elif args.command == "workspace":
        success = check_workspace()
        sys.exit(0 if success else 1)
    elif args.command == "install":
        install_dependencies()
    elif args.command == "graph":
        try:
            exports = export_graph(
                output_dir=args.output_dir,
                basename=args.basename,
                skip_png=args.skip_png,
                draw_method=args.draw_method,
                enable_dynamic=not args.static,
            )
        except Exception as exc:
            print(f"Graph export failed: {exc}")
            sys.exit(1)
        print(f"Mermaid diagram written to: {exports['mermaid']}")
        print(f"Metadata written to: {exports['metadata']}")
        png_path = exports.get("png")
        if png_path:
            print(f"PNG diagram written to: {png_path}")
        else:
            print("PNG diagram skipped")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
