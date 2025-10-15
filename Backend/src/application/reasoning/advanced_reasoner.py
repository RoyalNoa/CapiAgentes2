"""Advanced multi-step reasoning service for the LangGraph orchestrator."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

from src.core.logging import get_logger
from src.core.semantics import SemanticIntentService, get_global_context_manager
from src.domain.contracts.intent import Intent
from src.application.services.agent_config_service import AgentConfigService
from src.shared.agent_config_repository import FileAgentConfigRepository

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from src.infrastructure.langgraph.state_schema import GraphState

logger = get_logger(__name__)


@dataclass
class ReasoningStep:
    """Single deliberate action inside a reasoning plan."""

    step_id: str
    title: str
    description: str
    agent: Optional[str] = None
    inputs: List[str] = field(default_factory=list)
    expected_output: str = ""
    depends_on: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.step_id,
            "title": self.title,
            "description": self.description,
            "agent": self.agent,
            "inputs": self.inputs,
            "expected_output": self.expected_output,
            "depends_on": self.depends_on,
        }


@dataclass
class ReasoningPlan:
    """Structured reasoning plan shared across nodes."""

    plan_id: str
    version: int
    intent: str
    goal: str
    confidence: float
    recommended_agent: Optional[str]
    fallback_agent: str
    rationale: str
    steps: List[ReasoningStep] = field(default_factory=list)
    cooperative_agents: List[str] = field(default_factory=list)
    supporting_evidence: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    intent_alignment: bool = True
    requires_replan: bool = False
    history: List[Dict[str, Any]] = field(default_factory=list)
    progress_percent: float = 0.0
    remaining_steps: int = 0
    complexity: str = "medium"
    estimated_effort_seconds: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "version": self.version,
            "intent": self.intent,
            "goal": self.goal,
            "confidence": round(self.confidence, 3),
            "recommended_agent": self.recommended_agent,
            "fallback_agent": self.fallback_agent,
            "rationale": self.rationale,
            "steps": [step.to_dict() for step in self.steps],
            "cooperative_agents": self.cooperative_agents,
            "supporting_evidence": self.supporting_evidence,
            "generated_at": self.generated_at,
            "intent_alignment": self.intent_alignment,
            "requires_replan": self.requires_replan,
            "history": self.history,
            "progress_percent": round(self.progress_percent, 1),
            "remaining_steps": self.remaining_steps,
            "complexity": self.complexity,
            "estimated_effort_seconds": self.estimated_effort_seconds,
        }

    def to_trace_entry(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "version": self.version,
            "intent": self.intent,
            "confidence": round(self.confidence, 3),
            "recommended_agent": self.recommended_agent,
            "step_count": len(self.steps),
            "progress_percent": round(self.progress_percent, 1),
            "complexity": self.complexity,
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReasoningPlan":
        steps = []
        for step in data.get("steps", []):
            step_payload = {
                "step_id": step.get("step_id") or step.get("id") or "",
                "title": step.get("title", ""),
                "description": step.get("description", ""),
                "agent": step.get("agent"),
                "inputs": step.get("inputs", []),
                "expected_output": step.get("expected_output", ""),
                "depends_on": step.get("depends_on", []),
            }
            steps.append(ReasoningStep(**step_payload))
        return cls(
            plan_id=data.get("plan_id", str(uuid.uuid4())),
            version=int(data.get("version", 1)),
            intent=data.get("intent", "unknown"),
            goal=data.get("goal", ""),
            confidence=float(data.get("confidence", 0.0)),
            recommended_agent=data.get("recommended_agent"),
            fallback_agent=data.get("fallback_agent", "assemble"),
            rationale=data.get("rationale", ""),
            steps=steps,
            cooperative_agents=data.get("cooperative_agents", []),
            supporting_evidence=data.get("supporting_evidence", {}),
            generated_at=data.get("generated_at", datetime.utcnow().isoformat()),
            intent_alignment=bool(data.get("intent_alignment", True)),
            requires_replan=bool(data.get("requires_replan", False)),
            history=data.get("history", []),
            progress_percent=float(data.get("progress_percent", data.get("progress", 0.0))),
            remaining_steps=int(data.get("remaining_steps", len(steps))),
            complexity=data.get("complexity", "medium"),
            estimated_effort_seconds=int(data.get("estimated_effort_seconds", 0)),
        )

    def new_revision(self) -> "ReasoningPlan":
        snapshot = self.to_dict()
        snapshot.pop("history", None)
        return ReasoningPlan(
            plan_id=self.plan_id,
            version=self.version + 1,
            intent=self.intent,
            goal=self.goal,
            confidence=self.confidence,
            recommended_agent=self.recommended_agent,
            fallback_agent=self.fallback_agent,
            rationale=self.rationale,
            steps=[ReasoningStep(**step.to_dict()) for step in self.steps],
            cooperative_agents=list(self.cooperative_agents),
            supporting_evidence=dict(self.supporting_evidence),
            generated_at=datetime.utcnow().isoformat(),
            intent_alignment=self.intent_alignment,
            requires_replan=False,
            history=self.history + [snapshot],
            progress_percent=self.progress_percent,
            remaining_steps=self.remaining_steps,
            complexity=self.complexity,
            estimated_effort_seconds=self.estimated_effort_seconds,
        )


class AdvancedReasoner:
    """Combines semantic analysis and heuristics to build execution plans."""

    def __init__(
        self,
        semantic_service: Optional[SemanticIntentService] = None,
        config_service: Optional[AgentConfigService] = None,
    ) -> None:
        self.semantic_service = semantic_service or SemanticIntentService()
        self.config_service = config_service or AgentConfigService(FileAgentConfigRepository())
        self.context_manager = get_global_context_manager()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_plan(
        self,
        *,
        query: str,
        session_id: str,
        user_id: str,
        intent_hint: Optional[Intent] = None,
    ) -> ReasoningPlan:
        context = self.context_manager.get_context_summary(session_id)
        semantic_result = self.semantic_service.classify_intent(query, context)
        primary_intent = intent_hint or semantic_result.intent or Intent.UNKNOWN
        enabled_agents = self._enabled_agents()

        plan = self._build_plan(
            query=query,
            primary_intent=primary_intent,
            semantic_result=semantic_result,
            enabled_agents=enabled_agents,
        )
        self._augment_with_cooperation(plan, enabled_agents)
        self._finalize_plan(plan)
        plan.supporting_evidence.update(
            {
                "entities": semantic_result.entities,
                "context_used": bool(context),
                "semantic_confidence": round(semantic_result.confidence, 3),
                "available_agents": sorted(a for a, enabled in enabled_agents.items() if enabled),
                "user_id": user_id,
                "session_id": session_id,
            }
        )

        logger.info(
            {
                "event": "advanced_reasoning_plan",
                "plan_id": plan.plan_id,
                "intent": plan.intent,
                "recommended_agent": plan.recommended_agent,
                "confidence": round(plan.confidence, 3),
                "steps": len(plan.steps),
            }
        )
        return plan

    def needs_replan(self, plan: ReasoningPlan, state: "GraphState" | None = None) -> bool:
        if plan.requires_replan:
            return True

        enabled_agents = self._enabled_agents()
        if plan.recommended_agent and not enabled_agents.get(plan.recommended_agent, True):
            return True

        if state is not None:
            errors = getattr(state, "errors", []) or []
            if errors:
                return True
            metadata = getattr(state, "response_metadata", {}) or {}
            dispatched_agent = metadata.get("routing_decision")
            if dispatched_agent and plan.recommended_agent and dispatched_agent != plan.recommended_agent:
                return True
            latest_error = metadata.get("latest_agent_error")
            if latest_error:
                return True
        return False

    def replan_from_state(
        self,
        previous_plan: ReasoningPlan,
        *,
        query: str,
        session_id: str,
        user_id: str,
        state: "GraphState" | None = None,
    ) -> ReasoningPlan:
        context = self.context_manager.get_context_summary(session_id)
        semantic_result = self.semantic_service.classify_intent(query, context)
        hint_intent = getattr(state, "detected_intent", None)
        primary_intent = hint_intent or semantic_result.intent or Intent.UNKNOWN
        enabled_agents = self._enabled_agents()

        new_plan = self._build_plan(
            query=query,
            primary_intent=primary_intent,
            semantic_result=semantic_result,
            enabled_agents=enabled_agents,
            plan_id=previous_plan.plan_id,
        )
        new_plan.history = previous_plan.history + [previous_plan.to_dict()]
        new_plan.version = previous_plan.version + 1
        new_plan.supporting_evidence.update(previous_plan.supporting_evidence)
        self._augment_with_cooperation(new_plan, enabled_agents)
        self._finalize_plan(new_plan)

        logger.info(
            {
                "event": "advanced_reasoning_replan",
                "plan_id": new_plan.plan_id,
                "previous_version": previous_plan.version,
                "new_version": new_plan.version,
                "recommended_agent": new_plan.recommended_agent,
            }
        )
        return new_plan

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _enabled_agents(self) -> Dict[str, bool]:
        statuses = self.config_service.list_status()
        return {status.name: status.enabled for status in statuses}

    def _build_plan(
        self,
        *,
        query: str,
        primary_intent: Intent,
        semantic_result,
        enabled_agents: Dict[str, bool],
        plan_id: Optional[str] = None,
    ) -> ReasoningPlan:
        intent_value = getattr(primary_intent, "value", str(primary_intent))
        base_confidence = float(max(semantic_result.confidence, 0.35))
        steps: List[ReasoningStep] = []
        recommended_agent: Optional[str] = None
        fallback_agent = "assemble"
        rationale = ""
        intent_alignment = True

        enabled_set = {agent for agent, enabled in enabled_agents.items() if enabled}

        if primary_intent == Intent.FILE_OPERATION:
            recommended_agent = self._select_enabled_agent(["capi_desktop"], enabled_set)
            steps = self._file_operation_steps(recommended_agent)
            rationale = (
                "La consulta requiere operar con archivos; se prioriza el agente "
                "de escritorio con validaciones de contenido y verificación de salida."
            )
            base_confidence = max(base_confidence, 0.72)
        elif primary_intent == Intent.DB_OPERATION:
            recommended_agent = self._select_enabled_agent(["capi_datab"], enabled_set)
            steps = self._db_operation_steps(recommended_agent)
            rationale = (
                "La consulta requiere operaciones sobre bases de datos; se utiliza el agente "
                "especialista con controles de validación y exportes auditables."
            )
            fallback_agent = recommended_agent or fallback_agent
            base_confidence = max(base_confidence, 0.73)
        elif primary_intent == Intent.SUMMARY_REQUEST:
            recommended_agent = self._select_enabled_agent(["summary"], enabled_set)
            if recommended_agent is None:
                recommended_agent = self._select_enabled_agent(["capi_gus"], enabled_set)
            steps = self._summary_steps(recommended_agent, enabled_set)
            rationale = (
                "La intención es generar un resumen financiero. Se planifica cargar datos, "
                "calcular métricas críticas, validar anomalías y narrar resultados."
            )
            base_confidence = max(base_confidence, 0.75)
        elif primary_intent == Intent.BRANCH_QUERY:
            recommended_agent = self._select_enabled_agent(["branch", "summary"], enabled_set)
            steps = self._branch_steps(recommended_agent, enabled_set)
            rationale = (
                "La consulta apunta a rendimiento por sucursal, se coordinan comparativas "
                "y generación de insights segmentados."
            )
            base_confidence = max(base_confidence, 0.7)
        elif primary_intent == Intent.ANOMALY_QUERY:
            recommended_agent = self._select_enabled_agent(["anomaly", "summary"], enabled_set)
            steps = self._anomaly_steps(recommended_agent, enabled_set)
            rationale = (
                "Se requieren detecciones de anomalías con priorización por severidad y "
                "contraste con métricas globales."
            )
            base_confidence = max(base_confidence, 0.68)
        elif primary_intent in {Intent.GOOGLE_WORKSPACE, Intent.GOOGLE_GMAIL, Intent.GOOGLE_DRIVE, Intent.GOOGLE_CALENDAR}:
            preferred = ["agente_g"]
            recommended_agent = self._select_enabled_agent(preferred, enabled_set)
            steps = self._google_workspace_steps(recommended_agent)
            rationale = (
                "La consulta solicita acciones sobre Google Workspace; se delega en Agente G "
                "para validar credenciales y ejecutar Gmail, Drive o Calendar."
            )
            fallback_agent = recommended_agent or fallback_agent
            base_confidence = max(base_confidence, 0.65)
        elif primary_intent in {Intent.GREETING, Intent.SMALL_TALK}:
            preferred_capi_gus = self._select_enabled_agent(["capi_gus"], enabled_set)
            if preferred_capi_gus:
                recommended_agent = preferred_capi_gus
                intent_alignment = True
            else:
                recommended_agent = self._select_enabled_agent(["summary"], enabled_set)
                intent_alignment = False
            steps = self._conversation_steps(recommended_agent)
            rationale = (
                "Se identificó interacción social; se prepara una respuesta cordial con "
                "monitor de intención latente para escalar si aparecen necesidades de negocio."
            )
            base_confidence = max(base_confidence, 0.6)
        else:
            recommended_agent = self._select_enabled_agent(
                ["summary", "capi_gus", "capi_desktop", "capi_datab"], enabled_set
            )
            steps = self._exploratory_steps(recommended_agent, enabled_set)
            rationale = (
                "Consulta ambigua: se elabora estrategia de clarificación y recopilación "
                "de señales antes de seleccionar agente definitivo."
            )
            intent_alignment = False
            base_confidence = max(base_confidence, 0.55)

        confidence = min(base_confidence + 0.1 * len(steps), 0.95)

        return ReasoningPlan(
            plan_id=plan_id or str(uuid.uuid4()),
            version=1,
            intent=intent_value,
            goal=self._goal_from_intent(primary_intent, query),
            confidence=confidence,
            recommended_agent=recommended_agent,
            fallback_agent=fallback_agent,
            rationale=rationale,
            steps=steps,
            intent_alignment=intent_alignment,
        )

    def _augment_with_cooperation(
        self, plan: ReasoningPlan, enabled_agents: Dict[str, bool]
    ) -> None:
        cooperating: Set[str] = {
            step.agent for step in plan.steps if step.agent and step.agent != plan.recommended_agent
        }
        plan.cooperative_agents = sorted(
            agent for agent in cooperating if enabled_agents.get(agent, True)
        )

        if plan.recommended_agent and not enabled_agents.get(plan.recommended_agent, True):
            plan.requires_replan = True
            plan.supporting_evidence["disabled_recommended_agent"] = plan.recommended_agent

    def _finalize_plan(self, plan: ReasoningPlan) -> None:
        step_count = len(plan.steps)
        cooperating_count = len(plan.cooperative_agents)
        plan.remaining_steps = step_count
        plan.estimated_effort_seconds = self._estimate_effort_seconds(step_count, cooperating_count)
        plan.complexity = self._compute_complexity(step_count, cooperating_count, plan.intent_alignment)
        plan.progress_percent = self._estimate_progress(plan)
        plan.supporting_evidence.setdefault("progress_percent", plan.progress_percent)
        plan.supporting_evidence.setdefault("remaining_steps", plan.remaining_steps)
        plan.supporting_evidence.setdefault("estimated_effort_seconds", plan.estimated_effort_seconds)
        plan.supporting_evidence.setdefault("complexity", plan.complexity)

        logger.info({
            "event": "reasoning_plan_metrics",
            "plan_id": plan.plan_id,
            "version": plan.version,
            "intent": plan.intent,
            "recommended_agent": plan.recommended_agent,
            "progress_percent": plan.progress_percent,
            "remaining_steps": plan.remaining_steps,
            "estimated_effort_seconds": plan.estimated_effort_seconds,
            "complexity": plan.complexity,
        })

    def _estimate_effort_seconds(self, step_count: int, cooperating_count: int) -> int:
        base = 18 + step_count * 9 + cooperating_count * 5
        return int(base)

    def _compute_complexity(self, step_count: int, cooperating_count: int, aligned: bool) -> str:
        score = step_count + cooperating_count
        if not aligned:
            score += 1
        if score <= 3:
            return "low"
        if score <= 6:
            return "medium"
        return "high"

    def _estimate_progress(self, plan: ReasoningPlan) -> float:
        base_score = max(12.0, plan.confidence * 100)
        if plan.intent_alignment:
            base_score += 5.0
        base_score += min(12.0, len(plan.cooperative_agents) * 2.5)
        return round(min(base_score, 98.0), 1)

    def _select_enabled_agent(
        self, preferred_order: List[str], enabled_agents: Set[str]
    ) -> Optional[str]:
        for agent in preferred_order:
            if agent and agent in enabled_agents:
                return agent
        return None

    def _goal_from_intent(self, intent: Intent, query: str) -> str:
        lookup = {
            Intent.FILE_OPERATION: "Resolver solicitud de archivos del usuario con seguridad",
            Intent.SUMMARY_REQUEST: "Entregar resumen financiero estratégico",
            Intent.BRANCH_QUERY: "Evaluar desempeño por sucursal",
            Intent.ANOMALY_QUERY: "Detectar y explicar anomalías financieras",
            Intent.GREETING: "Mantener interacción cordial y guiar a capacidades",
            Intent.SMALL_TALK: "Mantener conversación ligera sin perder contexto",
            Intent.GOOGLE_WORKSPACE: "Atender una solicitud de Google Workspace (Gmail, Drive o Calendar)",
            Intent.GOOGLE_GMAIL: "Gestionar una operación de Gmail solicitada por el usuario",
            Intent.GOOGLE_DRIVE: "Ejecutar una operación en Google Drive solicitada por el usuario",
            Intent.GOOGLE_CALENDAR: "Gestionar un evento en Google Calendar solicitado por el usuario",
        }
        return lookup.get(intent, f"Clarificar y asistir consulta ambigua: {query[:60]}")

    # ------------------------------------------------------------------
    # Step factories per intent
    # ------------------------------------------------------------------

    def _file_operation_steps(self, agent: Optional[str]) -> List[ReasoningStep]:
        return [
            ReasoningStep(
                step_id="F1",
                title="Verificar permisos y contexto de archivo",
                description="Confirmar ruta, formato y nivel de autorización para evitar operaciones inseguras.",
                agent=agent or "capi_desktop",
                expected_output="Archivo identificado con permisos validados",
            ),
            ReasoningStep(
                step_id="F2",
                title="Ejecutar operación solicitada",
                description="Realizar acción solicitada (leer, convertir, listar) sobre el archivo de manera atómica.",
                agent=agent or "capi_desktop",
                inputs=["archivo_usuario"],
                expected_output="Resultado bruto de la operación",
                depends_on=["F1"],
            ),
            ReasoningStep(
                step_id="F3",
                title="Sintetizar hallazgos",
                description="Extraer resumen entendible para el usuario y anticipar acciones posteriores.",
                agent="summary",
                expected_output="Explicación en lenguaje natural",
                depends_on=["F2"],
            ),
        ]
    def _db_operation_steps(self, agent: Optional[str]) -> List[ReasoningStep]:
        agent_name = agent or "capi_datab"
        return [
            ReasoningStep(
                step_id="D1",
                title="Analizar requerimiento y sanitizar sentencia",
                description="Interpretar la instrucción (JSON, SQL o lenguaje natural), validar tablas y evitar comandos restringidos (DROP/TRUNCATE).",
                agent=agent_name,
                inputs=["instruccion_usuario"],
                expected_output="Sentencia SQL validada con parámetros normalizados",
            ),
            ReasoningStep(
                step_id="D2",
                title="Ejecutar operación transaccional en PostgreSQL",
                description="Abrir conexión controlada, ejecutar la sentencia y capturar filas afectadas o resultados.",
                agent=agent_name,
                depends_on=["D1"],
                expected_output="Resultado de la operación (filas, datos o confirmación)",
            ),
            ReasoningStep(
                step_id="D3",
                title="Exportar evidencia al workspace",
                description="Serializar los resultados en el formato solicitado y guardar el archivo en ia_workspace/data/capi_DataB/.",
                agent=agent_name,
                depends_on=["D2"],
                expected_output="Archivo DataB_YYYY_MM_DD_*.ext disponible para el usuario",
            ),
        ]



    def _summary_steps(
        self, agent: Optional[str], enabled_agents: Set[str]
    ) -> List[ReasoningStep]:
        steps = [
            ReasoningStep(
                step_id="S1",
                title="Cargar datos financieros vigentes",
                description="Garantizar que la base de datos esté sincronizada antes de calcular métricas.",
                agent="capi_desktop" if "capi_desktop" in enabled_agents else agent,
                expected_output="Dataset consolidado para análisis",
            ),
            ReasoningStep(
                step_id="S2",
                title="Calcular métricas clave",
                description="Obtener totales, variaciones y ratios relevantes para la gerencia.",
                agent=agent or "summary",
                expected_output="Paquete de métricas financieras",
                depends_on=["S1"],
            ),
            ReasoningStep(
                step_id="S3",
                title="Escanear anomalías críticas",
                description="Complementar el resumen con detección de anomalías para alertas tempranas.",
                agent="anomaly" if "anomaly" in enabled_agents else agent,
                expected_output="Listado de anomalías priorizadas",
                depends_on=["S2"],
            ),
            ReasoningStep(
                step_id="S4",
                title="Construir narrativa ejecutiva",
                description="Traducir métricas y anomalías en un relato ejecutivo con próximos pasos.",
                agent=agent or "summary",
                expected_output="Resumen narrado listo para el usuario",
                depends_on=["S2", "S3"],
            ),
        ]
        return steps

    def _branch_steps(
        self, agent: Optional[str], enabled_agents: Set[str]
    ) -> List[ReasoningStep]:
        return [
            ReasoningStep(
                step_id="B1",
                title="Identificar sucursales relevantes",
                description="Determinar si el usuario apunta a una sucursal específica o comparación global.",
                agent=agent or "branch",
                expected_output="Lista de sucursales objetivo",
            ),
            ReasoningStep(
                step_id="B2",
                title="Calcular KPIs por sucursal",
                description="Obtener ventas, gastos, márgenes y variaciones para cada sucursal target.",
                agent=agent or "branch",
                depends_on=["B1"],
                expected_output="KPIs comparables",
            ),
            ReasoningStep(
                step_id="B3",
                title="Detectar anomalías locales",
                description="Cruzar resultados con detector de anomalías para resaltar riesgos.",
                agent="anomaly" if "anomaly" in enabled_agents else agent,
                depends_on=["B2"],
                expected_output="Alertas específicas por sucursal",
            ),
            ReasoningStep(
                step_id="B4",
                title="Generar narrativa y recomendaciones",
                description="Construir historia por sucursal con insights accionables.",
                agent="summary",
                depends_on=["B2", "B3"],
                expected_output="Informe comparativo",
            ),
        ]

    def _anomaly_steps(
        self, agent: Optional[str], enabled_agents: Set[str]
    ) -> List[ReasoningStep]:
        reviewer = "summary" if "summary" in enabled_agents else agent
        return [
            ReasoningStep(
                step_id="A1",
                title="Configurar umbrales de riesgo",
                description="Adaptar sensibilidad del detector según contexto reciente y tolerancia.",
                agent=agent or "anomaly",
                expected_output="Parámetros calibrados",
            ),
            ReasoningStep(
                step_id="A2",
                title="Ejecutar detección de anomalías",
                description="Identificar transacciones o ramas con comportamientos atípicos.",
                agent=agent or "anomaly",
                expected_output="Listado de anomalías con severidad",
                depends_on=["A1"],
            ),
            ReasoningStep(
                step_id="A3",
                title="Evaluar impacto financiero",
                description="Cuantificar impacto y priorizar acciones correctivas.",
                agent=reviewer,
                expected_output="Resumen del impacto",
                depends_on=["A2"],
            ),
            ReasoningStep(
                step_id="A4",
                title="Proponer mitigaciones",
                description="Generar recomendaciones basadas en políticas internas y comportamiento histórico.",
                agent=reviewer,
                expected_output="Plan de acción recomendado",
                depends_on=["A3"],
            ),
        ]

    def _google_workspace_steps(self, agent: Optional[str]) -> List[ReasoningStep]:
        agent_name = agent or "agente_g"
        return [
            ReasoningStep(
                step_id="G1",
                title="Interpretar instrucción de Google Workspace",
                description="Clasificar si la operación requerida corresponde a Gmail, Drive o Calendar y validar parámetros sensibles.",
                agent=agent_name,
                expected_output="Operación y parámetros normalizados",
            ),
            ReasoningStep(
                step_id="G2",
                title="Ejecutar operación solicitada",
                description="Invocar la API correspondiente (Gmail, Drive o Calendar) respetando scopes autorizados.",
                agent=agent_name,
                depends_on=["G1"],
                expected_output="Resultado bruto de la operación de Google Workspace",
            ),
            ReasoningStep(
                step_id="G3",
                title="Registrar métricas y artefactos",
                description="Guardar métricas de Google Workspace, adjuntar artefactos relevantes y preparar mensaje para el usuario.",
                agent=agent_name,
                depends_on=["G2"],
                expected_output="Resumen auditable de la operación",
            ),
        ]

    def _conversation_steps(self, agent: Optional[str]) -> List[ReasoningStep]:
        return [
            ReasoningStep(
                step_id="T1",
                title="Responder cordialmente",
                description="Ofrecer una respuesta amable y mantener tono profesional.",
                agent=agent or "capi_gus",
                expected_output="Respuesta en lenguaje natural",
            ),
            ReasoningStep(
                step_id="T2",
                title="Detectar intención latente",
                description="Evaluar si el usuario esconde una necesidad de negocio tras el saludo.",
                agent="intent",
                expected_output="Posible intención secundaria",
                depends_on=["T1"],
            ),
            ReasoningStep(
                step_id="T3",
                title="Redirigir a capacidades clave",
                description="Sugerir análisis o acciones disponibles según el contexto.",
                agent="summary",
                expected_output="Sugerencias contextualizadas",
                depends_on=["T2"],
            ),
        ]

    def _exploratory_steps(
        self, agent: Optional[str], enabled_agents: Set[str]
    ) -> List[ReasoningStep]:
        clarifier = agent or "capi_gus"
        analyst = "summary" if "summary" in enabled_agents else agent
        return [
            ReasoningStep(
                step_id="E1",
                title="Solicitar clarificación",
                description="Pedir más detalles al usuario para reducir ambigüedad.",
                agent=clarifier,
                expected_output="Detalle adicional de la consulta",
            ),
            ReasoningStep(
                step_id="E2",
                title="Identificar señales financieras",
                description="Buscar palabras clave que alineen la consulta con agentes especializados.",
                agent="intent",
                expected_output="Intentos candidatos",
                depends_on=["E1"],
            ),
            ReasoningStep(
                step_id="E3",
                title="Preparar respuesta inicial",
                description="Ofrecer orientación y sugerir capacidades relevantes mientras se espera aclaración.",
                agent=analyst,
                expected_output="Guía introductoria",
                depends_on=["E1", "E2"],
            ),
        ]

__all__ = [
    "AdvancedReasoner",
    "ReasoningPlan",
    "ReasoningStep",
]
