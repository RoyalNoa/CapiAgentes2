"""
Nodo LangGraph para Capi Desktop.

MIGRATED: Now uses semantic NLP system for intelligent file operation detection.
Eliminates all hardcoded patterns and uses centralized semantic classification.
"""
from __future__ import annotations

import os
import sys
import asyncio
import re
from typing import Any, Dict, Optional

from .base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator
from src.core.logging import get_logger
from src.core.semantics import SemanticIntentService, get_global_context_manager
from src.infrastructure.langgraph.algorithms.professional_error_recovery import (
    EnhancedOperationExecutor, ErrorContext, ErrorSeverity
)

logger = get_logger(__name__)


def _ensure_paths() -> None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_src_path = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
    # Fixed: ia_workspace is in Backend/ia_workspace (same level as src)
    backend_root_path = os.path.abspath(os.path.join(backend_src_path, '..'))  # Backend directory
    ia_ws_path = os.path.abspath(os.path.join(backend_root_path, 'ia_workspace'))
    if backend_src_path not in sys.path:
        sys.path.insert(0, backend_src_path)
    if ia_ws_path not in sys.path:
        sys.path.insert(0, ia_ws_path)
    # Production logging for path verification
    logger.info({
        "event": "path_setup",
        "backend_src": backend_src_path,
        "backend_root": backend_root_path,
        "ia_workspace": ia_ws_path,
        "ia_ws_exists": os.path.exists(ia_ws_path)
    })


_ensure_paths()

from src.domain.agents.agent_protocol import AgentRequest  # noqa: E402
import importlib  # noqa: E402


class CapiDesktopNode(GraphNode):
    """
    Semantic-powered file operations node.

    Uses SemanticIntentService for intelligent operation detection
    and context management for conversation continuity.
    """

    def __init__(self, name: str = "capi_desktop") -> None:
        super().__init__(name=name)
        self._is_agent_node = True

        # Initialize semantic services
        self.semantic_service = SemanticIntentService()
        self.context_manager = get_global_context_manager()
        self.operation_executor = EnhancedOperationExecutor()

        # Lazy import to avoid static analysis import errors
        try:
            mod = importlib.import_module('agentes.capi_desktop.handler')
            AgentCls = getattr(mod, 'CapiDesktop')
            self.agent = AgentCls()

            logger.info({"event": "desktop_node_initialized",
                        "mode": "semantic_nlp",
                        "agent_loaded": True})
        except Exception as e:
            logger.error({"event": "agent_import_error", "error": str(e)})
            raise

    def run(self, state: GraphState) -> GraphState:
        """
        Execute semantic file operation detection and agent invocation.

        SEMANTIC INTEGRATION: Uses SemanticIntentService for intelligent
        operation detection and context management for conversation continuity.
        """
        import asyncio
        import time

        start_time = time.time()
        self._emit_agent_start(state)

        try:
            metadata = dict(state.response_metadata or {})
            manual_instruction = metadata.get("desktop_instruction")
            if isinstance(manual_instruction, dict):
                operation_result = self._manual_instruction_operation(manual_instruction)
            else:
                # SEMANTIC OPERATION DETECTION
                operation_result = self._semantic_operation_detection(state)
            op = operation_result['operation']
            params = operation_result['parameters']

            # DEBUG: Log the operation being executed
            logger.info({
                "event": "DEBUG_operation_execution",
                "operation": op,
                "parameters": params,
                "action": operation_result.get('action'),
                "query": state.original_query,
                "source": "manual" if isinstance(manual_instruction, dict) else "semantic"
            })

            # Track context for future queries
            if params.get('filename'):
                self.context_manager.track_file_access(
                    state.session_id,
                    params['filename'],
                    operation_result.get('action', 'unknown')
                )

            # Execute agent with professional error recovery using sync wrapper
            execution_context = {
                "agent": self.agent,
                "user_query": state.original_query,
                "user_id": state.user_id,
                "session_id": state.session_id,
                "trace_id": state.trace_id
            }

            # Execute agent directly with professional error recovery fallback
            try:
                # Create agent request and execute directly
                from src.domain.agents.agent_protocol import AgentRequest
                request = AgentRequest(
                    intent=op,
                    query=state.original_query,
                    parameters=params,
                    user_id=state.user_id,
                    session_id=state.session_id,
                    context={"trace_id": state.trace_id}
                )

                # FORCE REAL AGENT EXECUTION - NO MORE FALLBACKS
                if hasattr(self.agent, 'execute'):
                    try:
                        # Force synchronous execution
                        result = self.agent.execute(request)
                    except Exception as exec_error:
                        # If async, run it properly
                        import inspect
                        if inspect.iscoroutinefunction(self.agent.execute):
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                result = loop.run_until_complete(self.agent.execute(request))
                            finally:
                                loop.close()
                        else:
                            raise exec_error
                else:
                    # If no execute method, call handler directly
                    if hasattr(self.agent, op):
                        method = getattr(self.agent, op)
                        result = method(**params)
                    else:
                        # Direct file access as last resort
                        from pathlib import Path
                        # Check both OneDrive Desktop and regular Desktop
                        onedrive_desktop = Path.home() / "OneDrive" / "Desktop"
                        regular_desktop = Path.home() / "Desktop"

                        docker_desktop = Path('/app/user_desktop')
                        desktop_candidates = [p for p in [docker_desktop, onedrive_desktop, regular_desktop] if p.exists()]
                        desktop_path = desktop_candidates[0] if desktop_candidates else regular_desktop
                        filename = params.get('filename', '')
                        possible_files = []
                        search_paths = desktop_candidates or [desktop_path]
                        for candidate_path in search_paths:
                            possible_files.extend(list(candidate_path.glob('*' + filename + '*')))

                        if possible_files:
                            file_path = possible_files[0]
                            if file_path.suffix.lower() in ['.xlsx', '.xls']:
                                import pandas as pd
                                try:
                                    df = pd.read_excel(file_path)
                                    content = df.to_string(max_rows=10)
                                    from src.domain.agents.agent_protocol import AgentResponse
                                    result = AgentResponse(
                                        success=True,
                                        data={"content": content, "file": str(file_path)},
                                        message=f"Contenido del archivo {file_path.name}:\n{content[:500]}..."
                                    )
                                except Exception as e:
                                    from src.domain.agents.agent_protocol import AgentResponse
                                    result = AgentResponse(
                                        success=False,
                                        data={"error": str(e)},
                                        message=f"Error leyendo {file_path}: {e}"
                                    )
                            else:
                                from src.domain.agents.agent_protocol import AgentResponse
                                result = AgentResponse(
                                    success=True,
                                    data={"files_found": [str(f) for f in possible_files]},
                                    message=f"Encontré estos archivos: {[f.name for f in possible_files]}"
                                )
                        else:
                            from src.domain.agents.agent_protocol import AgentResponse
                            created_path = None
                            payload_rows = params.get('data') if isinstance(params, dict) else None
                            try:
                                if payload_rows:
                                    import pandas as pd
                                    df = pd.DataFrame(payload_rows) if isinstance(payload_rows, list) else pd.DataFrame([payload_rows])
                                    candidate_path = desktop_path / filename if filename else desktop_path / 'capi_desktop_output.xlsx'
                                    candidate_path.parent.mkdir(parents=True, exist_ok=True)
                                    df.to_excel(candidate_path, index=False)
                                    created_path = candidate_path
                            except Exception as write_error:  # pragma: no cover - defensive logging
                                logger.warning({"event": "capi_desktop_manual_write_failed", "error": str(write_error)})

                            if created_path and created_path.exists():
                                result = AgentResponse(
                                    success=True,
                                    data={"files_created": [str(created_path)]},
                                    message=f"Generé el archivo {created_path.name} en {created_path.parent}"
                                )
                            else:
                                result = AgentResponse(
                                    success=False,
                                    data={"searched_in": str(desktop_path)},
                                    message=f"No encontré ningún archivo con '{filename}' en {desktop_path}"
                                )

                execution_result = {
                    "success": True,
                    "result": result,
                    "strategy_used": "direct_execution",
                    "user_message": None
                }
            except Exception as direct_error:
                logger.warning(f"Direct execution failed: {direct_error}, using professional recovery")
                # Fallback to professional recovery with simplified approach
                execution_result = {
                    "success": False,
                    "error": str(direct_error),
                    "strategy_used": "error_recovery",
                    "user_message": f"Hubo un problema al {op}. Error: {str(direct_error)}"
                }

            if execution_result["success"]:
                result = execution_result["result"]
                # Log recovery strategy used for monitoring
                if execution_result["strategy_used"] != "direct_execution":
                    logger.info({
                        "event": "operation_recovery_success",
                        "operation": op,
                        "strategy": execution_result["strategy_used"],
                        "user_message": execution_result.get("user_message")
                    })
            else:
                # Create failure response with professional user communication
                from src.domain.agents.agent_protocol import AgentResponse
                result = AgentResponse(
                    success=False,
                    data={"error": execution_result["error"]},
                    message=execution_result["user_message"],
                    agent_name=self.name
                )

            # Performance timing
            duration = (time.time() - start_time) * 1000
            logger.info({"event": "agent_performance",
                        "agent": "capi_desktop",
                        "duration_ms": round(duration, 2),
                        "operation": op,
                        "semantic_confidence": operation_result.get('confidence', 0)})

            # Update state with results
            s = StateMutator.update_field(state, "current_node", self.name)
            s = StateMutator.append_to_list(s, "completed_nodes", self.name)
            if result.data:
                s = StateMutator.merge_dict(s, "response_data", result.data)
            if result.message:
                s = StateMutator.update_field(s, "response_message", result.message)

            # Enhanced metadata with semantic info
            action = operation_result.get('action')
            requires_approval = action in {'WRITE_FILE', 'MODIFY_FILE', 'DELETE'}
            metadata = {
                "agent": self.name,
                "semantic_operation": op,
                "semantic_confidence": operation_result.get('confidence', 0),
                "entities_detected": len(operation_result.get('entities', {})),
                "semantic_action": action,
                "requires_human_approval": requires_approval,
                "approval_reason": "Operaciones de escritura requieren validacion" if requires_approval else None,
                **(result.metadata or {})
            }
            metadata = {k: v for k, v in metadata.items() if v is not None}
            s = StateMutator.merge_dict(s, "response_metadata", metadata)

            self._emit_agent_end(state, success=bool(result.success))
            return s

        except Exception as e:
            logger.error({"event": "capi_desktop_error",
                         "error": str(e),
                         "trace_id": state.trace_id})
            s = StateMutator.update_field(state, "current_node", self.name)
            s = StateMutator.add_error(s, "agent_error", str(e), {"agent": self.name})
            self._emit_agent_end(state, success=False)
            return s


    def _manual_instruction_operation(self, instruction: Dict[str, Any]) -> Dict[str, Any]:
        """Build an operation payload from a metadata-provided instruction."""
        intent = str(instruction.get("operation") or instruction.get("intent") or "escribir_archivo_txt")
        params = instruction.get("parameters")
        if not isinstance(params, dict):
            params = {}
        action = instruction.get("action") or "manual"
        return {
            "operation": intent,
            "parameters": params,
            "action": action,
            "confidence": 1.0,
            "entities": {"source": "metadata"},
        }


    def _semantic_operation_detection(self, state: GraphState) -> Dict[str, Any]:
        """
        SEMANTIC OPERATION DETECTION: Replace all legacy hardcoded patterns
        with intelligent semantic analysis.
        """
        query = state.original_query or ""

        # Get conversation context for resolution
        context = self.context_manager.get_context_summary(state.session_id)

        # Classify intent using semantic service
        semantic_result = self.semantic_service.classify_intent(query, context)

        logger.info({
            "event": "semantic_operation_detection",
            "query": query,
            "intent": str(semantic_result.intent),
            "confidence": semantic_result.confidence,
            "entities": semantic_result.entities,
            "context_resolved": semantic_result.context_resolved
        })

        # Map semantic result to agent operation
        operation_result = self._map_semantic_to_agent_operation(semantic_result)

        # Track context for future queries
        if operation_result.get('parameters', {}).get('filename'):
            self.context_manager.track_file_access(
                state.session_id,
                operation_result['parameters']['filename'],
                operation_result.get('action', 'unknown')
            )

        return operation_result

    def _map_semantic_to_agent_operation(self, semantic_result) -> Dict[str, Any]:
        """Map semantic classification to agent-specific operations"""
        entities = semantic_result.entities or {}

        actions_detected = entities.get('actions_detected') or []
        formats_detected = entities.get('formats_detected') or []
        filenames_detected = entities.get('filenames_detected') or []

        action = entities.get('action', 'READ_FILE')
        filename = entities.get('filename')
        if not filename and filenames_detected:
            filename = filenames_detected[0]

        raw_format = entities.get('format')
        file_format = raw_format
        if file_format == 'text':
            inferred = self._infer_format_from_extension(entities.get('file_extension'))
            if inferred and inferred != 'text':
                file_format = inferred
        if not file_format:
            file_format = self._infer_format_from_extension(entities.get('file_extension')) or 'excel'

        logger.info({'event': 'desktop_semantic_entities',
                     'action': action,
                     'filename': filename,
                     'secondary_filename': entities.get('secondary_filename'),
                     'file_format': file_format,
                     'actions_detected': actions_detected,
                     'formats_detected': formats_detected})

        params: Dict[str, Any] = {}
        if filename:
            params['filename'] = filename

        if self._should_create_txt_copy(action, actions_detected, formats_detected):
            params['create_txt_copy'] = True
            txt_candidate = entities.get('secondary_filename') or self._pick_secondary_filename(filenames_detected, filename)
            params['txt_filename'] = self._build_txt_filename(txt_candidate or filename or 'output')
            params['txt_extension'] = '.txt'

        action_mapping = {
            'READ_CONTENT': self._get_read_operation_by_format,
            'READ_FILE': self._get_read_operation_by_format,
            'READ_WRITE': self._get_read_operation_by_format,
            'LIST_FILES': lambda fmt: ("listar_archivos_desktop", {"pattern": "*"}),
            'WRITE_FILE': self._get_write_operation_by_format,
            'MODIFY_FILE': self._get_modify_operation_by_format,
            'ANALYZE': lambda fmt: ("analizar_estructura_archivo", params),
            'SUMMARIZE': lambda fmt: ("analizar_estructura_archivo", params)
        }

        if action in action_mapping:
            operation, operation_params = action_mapping[action](file_format)
            if operation_params:
                params.update(operation_params)
        else:
            operation, fallback_params = self._get_read_operation_by_format(file_format)
            if fallback_params:
                params.update(fallback_params)

        return {
            'operation': operation,
            'parameters': params,
            'action': action,
            'confidence': semantic_result.confidence,
            'entities': entities
        }

    def _should_create_txt_copy(self, action: str, actions_detected: list[str], formats_detected: list[str]) -> bool:
        """Determina si se debe generar una copia en texto del contenido leído"""
        if 'text' not in formats_detected:
            return False

        if action == 'READ_WRITE':
            return True

        if 'WRITE_FILE' in actions_detected and any(a in {'READ_CONTENT', 'READ_FILE'} for a in actions_detected):
            return True

        return False

    @staticmethod
    def _pick_secondary_filename(filenames_detected: list[str], primary: str | None) -> str | None:
        """Elige un nombre alternativo si el usuario mencionó múltiples archivos"""
        for candidate in filenames_detected:
            if candidate and candidate != primary:
                return candidate
        return None

    @staticmethod
    def _build_txt_filename(base_name: str) -> str:
        """Normaliza el nombre del archivo de texto a generar"""
        import re as _re

        if not base_name:
            base_name = 'output'

        sanitized = _re.sub(r'[^A-Za-z0-9_-]+', '_', base_name.strip())
        if not sanitized:
            sanitized = 'output'

        if not sanitized.lower().endswith('_resumen'):
            sanitized = f"{sanitized}_resumen"

        return sanitized

    @staticmethod
    def _infer_format_from_extension(file_extension: Optional[str]) -> Optional[str]:
        """Deriva el formato a partir de la extensión del archivo"""
        if not file_extension:
            return None

        mapping = {
            '.xlsx': 'excel',
            '.xls': 'excel',
            '.csv': 'csv',
            '.docx': 'word',
            '.doc': 'word',
            '.pdf': 'pdf',
            '.txt': 'text'
        }

        return mapping.get(file_extension.lower())


    def _get_read_operation_by_format(self, file_format: str) -> tuple[str, dict]:
        """Get read operation based on file format"""
        format_mapping = {
            'excel': 'leer_archivo_excel',
            'csv': 'leer_archivo_csv',
            'word': 'leer_archivo_word',
            'pdf': 'leer_archivo_pdf',
            'text': 'leer_archivo_txt'
        }

        operation = format_mapping.get(file_format, 'leer_archivo_excel')
        return operation, {}

    def _get_write_operation_by_format(self, file_format: str) -> tuple[str, dict]:
        """Get write operation based on file format"""
        format_mapping = {
            'excel': 'escribir_archivo_excel',
            'csv': 'escribir_archivo_csv',
            'word': 'escribir_archivo_word',
            'text': 'escribir_archivo_txt'
        }

        operation = format_mapping.get(file_format, 'escribir_archivo_excel')
        return operation, {}

    def _get_modify_operation_by_format(self, file_format: str) -> tuple[str, dict]:
        """Get modify operation based on file format"""
        format_mapping = {
            'excel': 'modificar_archivo_excel',
            'csv': 'modificar_archivo_csv',
            'word': 'modificar_archivo_word',
            'text': 'modificar_archivo_txt'
        }

        operation = format_mapping.get(file_format, 'modificar_archivo_excel')
        return operation, {}

