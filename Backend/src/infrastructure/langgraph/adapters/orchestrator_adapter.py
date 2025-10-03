"""
Async adapter that wraps LangGraphRuntime to match the LangGraph orchestrator interface
expected by the API: process_query(query=..., user_id=..., session_id=...).
"""
from __future__ import annotations

import time
import requests
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from contextlib import suppress

from src.observability.agent_metrics import record_turn_event, record_error_event
from src.infrastructure.langgraph.graph_runtime import LangGraphRuntime
from src.application.services.token_usage_service import TokenUsageService
from src.application.reasoning.llm_reasoner import LLMReasoner
from src.domain.agents.agent_models import ResponseEnvelope
from src.core.logging import get_logger
from src.core.file_config import get_available_data_files, get_default_data_file

logger = get_logger(__name__)
token_usage_service = TokenUsageService()


class LangGraphOrchestratorAdapter:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.runtime = LangGraphRuntime(config=config or {})
        self.agent_name = "langgraph_orchestrator"
        self._turn_counters: dict[str, int] = {}
        self.llm_reasoner = LLMReasoner(model=(config or {}).get('llm_model'))
        # Get port from config, environment, or default to 8000
        import os
        self.api_port = (config or {}).get('api_port',
                                         os.getenv('API_PORT', '8000'))
        logger.info({"event": "adapter_initialized", "agent": self.agent_name, "api_port": self.api_port})

    def _record_token_usage(self, agent_name: str, usage: Dict[str, Any]) -> None:
        """Persiste el uso de tokens del agente sin recurrir a llamadas HTTP."""
        total_tokens = int(usage.get("total_tokens", 0))
        if total_tokens <= 0:
            return
        cost_usd = float(usage.get("cost_usd", 0.0))
        try:
            result = token_usage_service.record_usage(
                agent_name,
                total_tokens,
                cost_usd,
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
                model=usage.get("model"),
                provider=usage.get("provider", "openai"),
                usage_timestamp=usage.get("timestamp"),
            )
            logger.info({
                "event": "token_usage_recorded",
                "agent": result["agent"],
                "tokens": result["tokens_recorded"],
                "prompt_tokens": result["prompt_tokens_recorded"],
                "completion_tokens": result["completion_tokens_recorded"],
                "total_tokens": result["total_tokens"],
                "cost_usd": result["cost_recorded"],
                "total_cost_usd": result["total_cost"],
            })
        except ValueError as exc:
            logger.warning({"event": "token_usage_skipped", "reason": str(exc), "agent": agent_name, "tokens": total_tokens})
        except Exception as exc:
            logger.error({"event": "token_recording_error", "error": str(exc)})
    def _estimate_tokens_and_cost(self, text: str, response_text: str = "") -> Dict[str, Any]:
        """Estimate input/output tokens and approximate cost as fallback."""
        input_tokens = max(len(text) // 4, 0)
        output_tokens = max(len(response_text) // 4, 0)
        total_tokens = input_tokens + output_tokens
        input_cost = (input_tokens / 1000) * 0.03
        output_cost = (output_tokens / 1000) * 0.06
        total_cost = input_cost + output_cost
        return {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": round(total_cost, 6),
            "provider": "heuristic",
            "timestamp": datetime.utcnow().isoformat(),
        }
    def _extract_usage_details(self, envelope: ResponseEnvelope, query: str, response_text: str) -> Dict[str, Any]:
        """Resolve real LLM usage from envelope metadata or fall back to heuristic."""
        meta_dict = envelope.meta if isinstance(getattr(envelope, "meta", None), dict) else {}
        candidates = []
        if isinstance(meta_dict.get("llm_usage"), dict):
            candidates.append(meta_dict.get("llm_usage"))
        processing_metrics = meta_dict.get("processing_metrics")
        if isinstance(processing_metrics, dict):
            for key in ("llm_usage", "usage"):
                candidate = processing_metrics.get(key)
                if isinstance(candidate, dict):
                    candidates.append(candidate)
        usage_metadata = getattr(envelope, "usage_metadata", None)
        if isinstance(usage_metadata, dict):
            candidates.append(usage_metadata)
        if isinstance(getattr(envelope, "data", None), dict):
            data_usage = envelope.data.get("llm_usage") or envelope.data.get("usage")
            if isinstance(data_usage, dict):
                candidates.append(data_usage)

        for raw_usage in candidates:
            usage = dict(raw_usage)
            prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
            completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
            total_tokens = int(usage.get("total_tokens") or (prompt_tokens + completion_tokens))
            if total_tokens <= 0:
                continue
            model = usage.get("model") or usage.get("llm_model")
            cost = usage.get("cost_usd")
            if cost is None:
                cost = LLMReasoner._estimate_cost(model or "", prompt_tokens, completion_tokens)
            usage.update({
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost_usd": float(cost or 0.0),
                "model": model,
                "provider": usage.get("provider", "openai"),
                "timestamp": usage.get("timestamp") or datetime.utcnow().isoformat(),
            })
            return usage

        fallback = self._estimate_tokens_and_cost(query, response_text)
        fallback.setdefault("model", meta_dict.get("llm_model") or meta_dict.get("model"))
        if not fallback.get("provider"):
            fallback["provider"] = "heuristic"
        return fallback

    def _extract_response_text(self, envelope: ResponseEnvelope) -> str:
        if hasattr(envelope, "data") and envelope.data:
            if isinstance(envelope.data, dict):
                return str(envelope.data.get("response", ""))
            return str(envelope.data)
        if hasattr(envelope, "response"):
            return str(envelope.response)
        return ""

    def _resolve_active_agent(self, envelope: ResponseEnvelope, response_text: str) -> str:
        meta = envelope.meta if isinstance(getattr(envelope, "meta", None), dict) else {}
        completed_nodes = meta.get("completed_nodes")
        if isinstance(completed_nodes, (list, tuple)):
            for agent_node in ("smalltalk", "summary", "branch", "anomaly"):
                if agent_node in completed_nodes:
                    return agent_node
        if hasattr(envelope, "data") and isinstance(envelope.data, dict):
            if envelope.data.get("agent"):
                return str(envelope.data["agent"])
            stage = envelope.data.get("workflow_stage")
            if isinstance(stage, str):
                lowered = stage.lower()
                if "summary" in lowered:
                    return "summary"
                if "branch" in lowered:
                    return "branch"
                if "anomaly" in lowered:
                    return "anomaly"
                if "smalltalk" in lowered:
                    return "smalltalk"
        return "unknown"

    async def _maybe_enhance_with_llm(
        self,
        *,
        envelope: ResponseEnvelope,
        query: str,
        response_text: str,
        active_agent: str,
        usage_details: Dict[str, Any],
        trace_id: Optional[str],
    ) -> Dict[str, Any]:
        client = getattr(self.llm_reasoner, "_client", None)
        if not client or usage_details.get("provider") != "heuristic":
            return usage_details

        try:
            prompt = self._build_llm_prompt(query, response_text, active_agent)
            context_data = {"agent": active_agent or "unknown", "response_preview": response_text[:600]}
            llm_result = await self.llm_reasoner.reason(
                query=prompt,
                context_data=context_data,
                trace_id=trace_id,
                max_output_tokens=512,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning({"event": "llm_enhancement_failed", "error": str(exc), "trace_id": trace_id})
            return usage_details

        if not llm_result.success:
            logger.info({"event": "llm_enhancement_skipped", "reason": llm_result.error, "trace_id": trace_id})
            return usage_details

        if llm_result.response:
            setattr(envelope, "message", llm_result.response)
        meta_dict = envelope.meta if isinstance(getattr(envelope, "meta", None), dict) else {}
        processing_metrics = meta_dict.setdefault("processing_metrics", {})
        processing_metrics["llm_model"] = llm_result.model
        processing_metrics["llm_latency_ms"] = int(llm_result.processing_time * 1000)
        processing_metrics["llm_confidence"] = llm_result.confidence_score
        meta_dict["llm_usage"] = llm_result.usage_metadata
        setattr(envelope, "meta", meta_dict)
        if isinstance(envelope.data, dict):
            envelope.data.setdefault("llm_usage", llm_result.usage_metadata)

        usage = dict(llm_result.usage_metadata)
        usage.setdefault("model", llm_result.model)
        usage.setdefault("provider", llm_result.provider)
        usage.setdefault("timestamp", usage_details.get("timestamp") or datetime.utcnow().isoformat())
        usage["cost_usd"] = llm_result.cost_usd
        usage["prompt_tokens"] = llm_result.prompt_tokens
        usage["completion_tokens"] = llm_result.completion_tokens
        usage["total_tokens"] = llm_result.total_tokens
        logger.info({
            "event": "llm_enhancement_completed",
            "trace_id": trace_id,
            "model": llm_result.model,
            "prompt_tokens": llm_result.prompt_tokens,
            "completion_tokens": llm_result.completion_tokens,
            "total_tokens": llm_result.total_tokens,
            "cost_usd": llm_result.cost_usd,
        })
        return usage

    @staticmethod
    def _build_llm_prompt(user_query: str, current_response: str, agent_name: str) -> str:
        query_excerpt = (user_query or "").strip()[:600]
        response_excerpt = (current_response or "").strip()[:1200]
        agent_label = agent_name or "general"
        return (
            "Eres un asistente financiero profesional.\n"
            f"Consulta original: {query_excerpt}\n"
            f"Borrador de respuesta del agente {agent_label}: {response_excerpt}\n"
            "Reescribe la mejor respuesta posible, céntrate en hechos y evita inventar datos."
        )

    def _next_turn_id(self, session_id: str) -> int:
        current = self._turn_counters.get(session_id, 0) + 1
        if current > 1_000_000:
            current = 1
        self._turn_counters[session_id] = current
        return current

    async def process_query(
        self,
        *,
        query: str,
        user_id: str,
        session_id: str,
        channel: str | None = None,
        trace_id: str | None = None,
    ) -> ResponseEnvelope:
        start = time.time()
        turn_id = self._next_turn_id(session_id)
        logger.info({
            "event": "adapter_process_query_start",
            "user_id": user_id,
            "session_id": session_id,
            "turn_id": turn_id,
            "trace_id": trace_id,
        })

        try:
            envelope = self.runtime.process_query(session_id=session_id, user_id=user_id, text=query)
        except Exception as exc:
            elapsed_ms = int((time.time() - start) * 1000)
            record_error_event(
                agent_name="unknown",
                session_id=session_id,
                turn_id=turn_id,
                error_code=exc.__class__.__name__,
                error_message=str(exc),
                latency_ms=elapsed_ms,
                user_id=user_id,
                channel=channel or "api",
                metadata={"query_preview": query[:120]},
                trace_id=trace_id,
            )
            logger.exception(
                "adapter_process_query_failed",
                extra={"session_id": session_id, "user_id": user_id, "turn_id": turn_id, "trace_id": trace_id},
            )
            raise

        if trace_id and not getattr(envelope, "trace_id", None):
            with suppress(Exception):
                setattr(envelope, "trace_id", trace_id)

        response_text = self._extract_response_text(envelope)
        active_agent = self._resolve_active_agent(envelope, response_text)

        effective_trace_id = getattr(envelope, "trace_id", None) or trace_id
        usage_details = self._extract_usage_details(envelope, query, response_text)
        usage_details = await self._maybe_enhance_with_llm(
            envelope=envelope,
            query=query,
            response_text=response_text,
            active_agent=active_agent,
            usage_details=usage_details,
            trace_id=effective_trace_id,
        )
        response_text = self._extract_response_text(envelope)
        input_tokens = int(usage_details.get("prompt_tokens", 0))
        output_tokens = int(usage_details.get("completion_tokens", 0))
        tokens_used = int(usage_details.get("total_tokens", input_tokens + output_tokens))
        cost_estimate = float(usage_details.get("cost_usd", 0.0))

        elapsed_ms = int((time.time() - start) * 1000)
        try:
            setattr(envelope, "agent_name", self.agent_name)
            setattr(envelope, "processing_time_ms", elapsed_ms)
            setattr(envelope, "tokens_used", tokens_used)
            setattr(envelope, "cost_estimate", cost_estimate)
        except Exception:
            pass

        meta_dict = envelope.meta if isinstance(envelope.meta, dict) else {}
        response_type_value = (
            envelope.response_type.value
            if hasattr(envelope.response_type, "value")
            else str(envelope.response_type)
        )
        intent_value = (
            envelope.intent.value if hasattr(envelope.intent, "value") else str(envelope.intent)
        )
        success = envelope.is_success() if hasattr(envelope, "is_success") else None
        channel_value = channel or "api"
        processing_metrics = meta_dict.get("processing_metrics")
        model_name = (
            meta_dict.get("model")
            or meta_dict.get("llm_model")
            or (processing_metrics or {}).get("llm_model")
            or usage_details.get("model")
        )

        if model_name and not usage_details.get("model"):
            usage_details["model"] = model_name
        self._record_token_usage(active_agent or self.agent_name, usage_details)

        metadata_payload: Dict[str, Any] = {}
        if active_agent:
            metadata_payload["active_agent"] = active_agent
        completed_nodes = meta_dict.get("completed_nodes")
        if completed_nodes:
            metadata_payload["completed_nodes"] = completed_nodes
        if isinstance(processing_metrics, dict) and processing_metrics:
            metadata_payload["processing_metrics"] = processing_metrics
        if usage_details:
            metadata_payload["llm_usage"] = usage_details
        intent_confidence = meta_dict.get("intent_confidence")
        if intent_confidence is not None:
            metadata_payload["intent_confidence"] = intent_confidence
        if query:
            metadata_payload["query_preview"] = query[:120]
        if response_text:
            metadata_payload["response_preview"] = response_text[:120]
        if envelope.errors:
            metadata_payload["errors"] = envelope.errors

        record_turn_event(
            agent_name=active_agent,
            session_id=session_id,
            turn_id=turn_id,
            latency_ms=elapsed_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_estimate,
            user_id=user_id,
            channel=channel_value,
            model=model_name,
            trace_id=effective_trace_id,
            intent=intent_value,
            response_type=response_type_value,
            success=success,
            metadata=metadata_payload or None,
        )

        if success is False:
            error_message = envelope.message if getattr(envelope, "message", None) else "Agent returned error"
            if envelope.errors:
                error_message = str(envelope.errors[0])
            failure_metadata = {
                "errors": envelope.errors if envelope.errors else None,
                "response_type": response_type_value,
            }
            failure_metadata = {key: value for key, value in failure_metadata.items() if value}
            record_error_event(
                agent_name=active_agent or "unknown",
                session_id=session_id,
                turn_id=turn_id,
                error_code="agent_response_error",
                error_message=error_message,
                latency_ms=elapsed_ms,
                user_id=user_id,
                channel=channel_value,
                trace_id=effective_trace_id,
                intent=intent_value,
                metadata=failure_metadata or None,
            )

        logger.info(
            {
                "event": "adapter_process_query_end",
                "elapsed_ms": elapsed_ms,
                "active_agent": active_agent,
                "tokens_used": tokens_used,
                "cost_estimate": round(cost_estimate, 6),
                "turn_id": turn_id,
                "trace_id": effective_trace_id,
            }
        )
        return envelope

    # ------------------------------------------------------------------
    # Session helpers for REST API compatibility
    # ------------------------------------------------------------------

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        return self.runtime.get_session_history(session_id)

    def get_active_sessions(self) -> List[str]:
        return self.runtime.get_active_sessions()

    def clear_session_history(self, session_id: str) -> None:
        self.runtime.clear_session_history(session_id)

    async def resume_human_gate(self, *, session_id: str, decision: Dict[str, Any]) -> ResponseEnvelope:
        """Resume a paused workflow after human approval."""
        return self.runtime.resume_human_gate(session_id=session_id, resume_payload=decision)

    async def load_data_use_case(self, file_path: str) -> Dict[str, Any]:
        """
        Load data from specified file for backwards compatibility with API.

        Args:
            file_path: Path to the data file to load

        Returns:
            Dictionary with success flag and data information
        """
        start = time.time()
        logger.info({"event": "load_data_start", "file_path": file_path})

        try:
            # Verify file exists and get file info
            available_files = get_available_data_files()
            if not available_files:
                logger.warning({"event": "load_data_no_files"})
                return {
                    "success": False,
                    "message": "No data files available in Backend/ia_workspace/data/",
                    "data": {}
                }

            # Find the specific file or use default
            target_file = None
            for file_info in available_files:
                if file_info["path"] == file_path or file_info["name"] in file_path:
                    target_file = file_info
                    break

            if not target_file:
                target_file = available_files[0]  # Use first available file
                logger.info({"event": "load_data_fallback", "using_file": target_file["name"]})

            # CRITICAL FIX: Load REAL data using existing repository infrastructure
            from src.infrastructure.repositories.repository_provider import RepositoryProvider
            from src.domain.services.financial_service import FinancialAnalysisService

            # Use existing repository to load real data
            repo_provider = RepositoryProvider()
            financial_repo = repo_provider.get_financial_repository()
            data_repo = repo_provider.get_data_file_repository()

            # Load real financial records from CSV file
            real_records = await data_repo.load_from_file(file_path)
            logger.info({"event": "real_data_loaded", "record_count": len(real_records)})

            # Save to financial repository for further processing
            if real_records:
                await financial_repo.save_many(real_records)

            # Use domain service to calculate real metrics
            financial_metrics = FinancialAnalysisService.calculate_financial_metrics(real_records)
            branch_summaries = FinancialAnalysisService.calculate_branch_summary(real_records)

            # Convert records to dict format for JSON serialization
            records_data = [record.to_dict() if hasattr(record, 'to_dict') else record.__dict__ for record in real_records]

            # Calculate real aggregates
            total_amount = sum(float(getattr(record, 'monto', 0) or 0) for record in real_records)
            income_records = [r for r in real_records if getattr(r, 'monto', 0) and float(getattr(r, 'monto')) > 0]
            expense_records = [r for r in real_records if getattr(r, 'monto', 0) and float(getattr(r, 'monto')) < 0]

            result = {
                "success": True,
                "message": f"Real data loaded from {target_file['name']} - {len(real_records)} records",
                "data": {
                    "json_data": records_data,  # REAL data from CSV
                    "financial_records": real_records,  # Domain objects
                    "financial_metrics": financial_metrics,  # Real calculated metrics
                    "branch_summaries": branch_summaries,  # Real branch analysis
                    "anomalies": [],  # Will be calculated by domain service
                    "summary": {
                        "total_records": len(real_records),  # REAL count
                        "file_name": target_file["name"],
                        "file_type": target_file["type"],
                        "file_size": target_file["size"],
                        "total_amount": total_amount,  # REAL amount
                        "income_count": len(income_records),  # REAL income count
                        "expense_count": len(expense_records)  # REAL expense count
                    },
                    "dashboard": {
                        "files_loaded": 1,
                        "total_files": len(available_files),
                        "last_modified": target_file["modified"].isoformat(),
                        "data_status": "loaded_with_real_data"  # Status updated
                    },
                    "records_count": len(real_records)  # REAL record count
                }
            }

            elapsed_ms = int((time.time() - start) * 1000)
            logger.info({
                "event": "load_data_success",
                "file": target_file["name"],
                "elapsed_ms": elapsed_ms
            })

            return result

        except Exception as e:
            logger.error({"event": "load_data_error", "error": str(e)})
            return {
                "success": False,
                "message": f"Error loading data: {str(e)}",
                "data": {}
            }
