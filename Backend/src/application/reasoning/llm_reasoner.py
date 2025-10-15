"""Asynchronous OpenAI-powered LLM reasoner with usage accounting."""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from openai import OpenAI, OpenAIError

from src.core.config import get_settings
from src.core.logging import get_logger

LOGGER = get_logger(__name__)


@dataclass
class LLMReasoningResult:
    """Container for LLM reasoning responses."""

    success: bool
    response: Optional[str]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    model: str = ""
    provider: str = "openai"
    processing_time: float = 0.0
    confidence_score: float = 0.0
    finish_reason: Optional[str] = None
    error: Optional[str] = None
    usage_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def token_usage(self) -> int:
        """Backwards compatible accessor used by legacy callers."""
        return self.total_tokens


class LLMReasoner:
    """OpenAI chat wrapper that exposes usage metrics for downstream services."""

    _DEFAULT_MODEL = "gpt-4o-mini"
    _RESPONSES_PREFIXES = ("gpt-4.1", "gpt-4.1-mini", "o4", "o4-mini", "gpt-5")
    _PRICING_TABLE: Dict[str, Dict[str, float]] = {
        # Prices expressed in USD per 1K tokens (prompt/completion)
        "gpt-4o": {"prompt": 0.005, "completion": 0.015},
        "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
        "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
        "gpt-4.1": {"prompt": 0.005, "completion": 0.015},
        "gpt-4.1-mini": {"prompt": 0.002, "completion": 0.008},
        "gpt-5": {"prompt": 0.005, "completion": 0.015},
    }

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 800,
        timeout: float = 30.0,
        organization: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.DEFAULT_MODEL or self._DEFAULT_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.organization = organization
        self._client_options: Dict[str, Any] = {
            'api_key': self.api_key,
            'organization': self.organization,
            'timeout': timeout,
        }
        model_key = (self.model or "").lower()
        self._use_responses_endpoint = any(
            model_key.startswith(prefix) for prefix in self._RESPONSES_PREFIXES
        )

        if not self.api_key:
            LOGGER.warning("LLMReasoner initialized without OPENAI_API_KEY; calls will fail")

    async def reason(
        self,
        *,
        query: str,
        context_data: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[Iterable[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        trace_id: Optional[str] = None,
        response_format: Optional[str] = None,
        max_output_tokens: Optional[int] = None,
    ) -> LLMReasoningResult:
        """Execute an OpenAI chat completion and capture usage metrics."""

        if not self.api_key:
            message = "OpenAI API key not configured"
            LOGGER.error({"event": "llm_reasoner_missing_key", "trace_id": trace_id})
            return LLMReasoningResult(
                success=False,
                response=None,
                model=self.model,
                error=message,
            )

        model_key = (self.model or "").lower()
        use_responses_endpoint = any(
            model_key.startswith(prefix) for prefix in self._RESPONSES_PREFIXES
        )
        self._use_responses_endpoint = use_responses_endpoint

        max_tokens = max_output_tokens or self.max_tokens
        start = time.perf_counter()
        messages = self._build_messages(
            query=query,
            context_data=context_data,
            conversation_history=conversation_history,
            system_prompt=system_prompt,
        )

        client_kwargs = {k: v for k, v in self._client_options.items() if v is not None}

        chat_response_format = self._normalize_chat_response_format(response_format)
        responses_text_config = self._normalize_responses_text_config(response_format)

        def _invoke_chat():
            client = OpenAI(**client_kwargs)
            request_kwargs: Dict[str, Any] = {
                "model": self.model,
                "max_tokens": max(1, max_tokens),
                "messages": messages,
            }
            if self.temperature is not None:
                request_kwargs["temperature"] = self.temperature
            if chat_response_format is not None:
                request_kwargs["response_format"] = chat_response_format
            return client.chat.completions.create(**request_kwargs)

        def _invoke_responses():
            client = OpenAI(**client_kwargs)
            input_payload = [{"role": item["role"], "content": item["content"]} for item in messages]
            request_kwargs: Dict[str, Any] = {
                "model": self.model,
                "input": input_payload,
                "max_output_tokens": max(1, max_tokens),
            }
            if responses_text_config is not None:
                request_kwargs["text"] = responses_text_config
            return client.responses.create(**request_kwargs)

        try:
            if use_responses_endpoint:
                response = await asyncio.to_thread(_invoke_responses)
            else:
                response = await asyncio.to_thread(_invoke_chat)
        except OpenAIError as exc:
            duration = time.perf_counter() - start
            LOGGER.error({"event": "llm_reasoner_request_failed", "trace_id": trace_id, "error": str(exc), "model": self.model, "duration_ms": int(duration * 1000)})
            return LLMReasoningResult(
                success=False,
                response=None,
                model=self.model,
                processing_time=duration,
                error=str(exc),
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            duration = time.perf_counter() - start
            LOGGER.exception("llm_reasoner_unexpected_error", extra={"trace_id": trace_id, "model": self.model})
            return LLMReasoningResult(
                success=False,
                response=None,
                model=self.model,
                processing_time=duration,
                error=str(exc),
            )

        duration = time.perf_counter() - start
        if use_responses_endpoint:
            message = getattr(response, "output_text", None)
            if not message:
                parts: List[str] = []
                for output in getattr(response, "output", []) or []:
                    for content in getattr(output, "content", []) or []:
                        if getattr(content, "type", None) == "output_text":
                            parts.append(getattr(content, "text", ""))
                message = "".join(parts) if parts else None
            usage = getattr(response, "usage", {}) or {}
            prompt_tokens = getattr(usage, "input_tokens", 0) or usage.get("prompt_tokens", 0) or 0
            completion_tokens = getattr(usage, "output_tokens", 0) or usage.get("completion_tokens", 0) or 0
            total_tokens = getattr(usage, "total_tokens", 0) or prompt_tokens + completion_tokens
            finish_reason = None
            for output in getattr(response, "output", []) or []:
                finish_reason = getattr(output, "finish_reason", None)
                if finish_reason:
                    break
        else:
            choice = response.choices[0] if response.choices else None
            message = choice.message.content if choice and choice.message else None
            finish_reason = choice.finish_reason if choice else None
            usage = getattr(response, "usage", None) or {}
            prompt_tokens = getattr(usage, "prompt_tokens", 0) or usage.get("prompt_tokens", 0) or 0
            completion_tokens = getattr(usage, "completion_tokens", 0) or usage.get("completion_tokens", 0) or 0
            total_tokens = getattr(usage, "total_tokens", 0) or usage.get("total_tokens", prompt_tokens + completion_tokens)
        cost_usd = self._estimate_cost(self.model, prompt_tokens, completion_tokens)
        confidence = 0.0
        if not use_responses_endpoint:
            choice = response.choices[0] if response.choices else None
            confidence = self._estimate_confidence(choice)

        usage_metadata = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "model": self.model,
            "provider": "openai",
            "finish_reason": finish_reason,
        }

        LOGGER.info({"event": "llm_reasoner_completed", "trace_id": trace_id, "model": self.model, "duration_ms": int(duration * 1000), "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "total_tokens": total_tokens, "cost_usd": round(cost_usd, 6), "finish_reason": finish_reason})

        return LLMReasoningResult(
            success=True,
            response=message,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            model=self.model,
            processing_time=duration,
            confidence_score=confidence,
            finish_reason=finish_reason,
            usage_metadata=usage_metadata,
        )

    @staticmethod
    def _normalize_chat_response_format(response_format: Optional[Any]) -> Optional[Dict[str, Any]]:
        if response_format is None:
            return None
        if isinstance(response_format, dict):
            if "type" in response_format:
                return response_format
            inner = response_format.get("format")
            if isinstance(inner, dict) and "type" in inner:
                return inner
            return response_format
        if isinstance(response_format, str) and response_format:
            return {"type": response_format}
        return None

    @staticmethod
    def _normalize_responses_text_config(response_format: Optional[Any]) -> Optional[Dict[str, Any]]:
        if response_format is None:
            return None
        if isinstance(response_format, dict):
            if "format" in response_format:
                return response_format
            return {"format": response_format}
        if isinstance(response_format, str) and response_format:
            return {"format": {"type": response_format}}
        return None

    def _build_messages(
        self,
        *,
        query: str,
        context_data: Optional[Dict[str, Any]],
        conversation_history: Optional[Iterable[Dict[str, str]]],
        system_prompt: Optional[str],
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if context_data:
            context_payload = json.dumps(context_data, ensure_ascii=False, indent=2)
            context_block = (
                "Contexto auxiliar para la consulta. Considera estos datos al razonar.\n"
                f"{context_payload}"
            )
            messages.append({"role": "system", "content": context_block})

        if conversation_history:
            for entry in conversation_history:
                role = entry.get("role", "user")
                content = entry.get("content")
                if content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": query})
        return messages

    @classmethod
    def _estimate_cost(cls, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = cls._PRICING_TABLE.get(model)
        if not pricing:
            for key, value in cls._PRICING_TABLE.items():
                if model.startswith(key):
                    pricing = value
                    break
        if not pricing:
            return 0.0
        prompt_cost = pricing["prompt"] * (prompt_tokens / 1000)
        completion_cost = pricing["completion"] * (completion_tokens / 1000)
        return round(prompt_cost + completion_cost, 6)

    @staticmethod
    def _estimate_confidence(choice: Any) -> float:
        """Heuristic confidence score using finish reason."""
        if not choice:
            return 0.0
        finish = getattr(choice, "finish_reason", "") or ""
        if finish == "stop":
            return 0.9
        if finish in {"length", "content_filter"}:
            return 0.6
        if finish in {"tool_calls", "function_call"}:
            return 0.8
        return 0.5


__all__ = ["LLMReasoner", "LLMReasoningResult"]
