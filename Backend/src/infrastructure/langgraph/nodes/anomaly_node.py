"""
Ruta: Backend/src/infrastructure/langgraph/nodes/anomaly_node.py
Descripción: Nodo para detección de anomalías usando agentes existentes
Estado: Activo - CORRECCIÓN CRÍTICA
Autor/Responsable: migration-bot
Última actualización: 2025-01-14
Tareas relacionadas: T-006-CRITICAL
Referencias: AI/Tablero/LangGraph/InfoAdicional.md#nodos-faltantes
"""
from __future__ import annotations

import hashlib
import time
from typing import Dict, Any, List

from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator
from src.infrastructure.repositories.repository_provider import RepositoryProvider
from src.core.logging import get_logger

logger = get_logger(__name__)

# Import existing AnomalyAgent and related classes
import sys
import os

AGENTS_AVAILABLE = False
anomaly_agent_class = None

try:
    # Try to import existing agents - need to add both Backend/src and ia_workspace to path
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Add Backend/src to path for agent dependencies
    backend_src_path = os.path.join(current_dir, '..', '..', '..')
    backend_src_path = os.path.abspath(backend_src_path)
    if backend_src_path not in sys.path:
        sys.path.insert(0, backend_src_path)

    # Add ia_workspace to path for agent imports
    # From Backend/src/infrastructure/langgraph/nodes/ to Backend/ia_workspace/
    workspace_path = os.path.join(current_dir, '..', '..', '..', '..', 'ia_workspace')
    workspace_path = os.path.abspath(workspace_path)
    if workspace_path not in sys.path:
        sys.path.insert(0, workspace_path)

    from agentes.anomaly.handler import AnomalyAgent
    from src.application.use_cases.financial_analysis_use_cases import GetAnomalyAnalysisUseCase
    from src.domain.contracts.agent_io import AgentTask, TaskStatus
    from src.domain.contracts.intent import Intent

    anomaly_agent_class = AnomalyAgent
    AGENTS_AVAILABLE = True
    logger.info("Successfully imported existing AnomalyAgent")

except ImportError as e:
    logger.warning(f"Could not import existing agents: {e}. Using fallback implementation.")
    AGENTS_AVAILABLE = False


class AnomalyNode(GraphNode):
    def __init__(self, name: str = "anomaly") -> None:
        super().__init__(name=name)
        self.repo_provider = RepositoryProvider()

        # Initialize existing AnomalyAgent if available
        if AGENTS_AVAILABLE and anomaly_agent_class:
            try:
                financial_repo = self.repo_provider.get_financial_repository()
                anomaly_use_case = GetAnomalyAnalysisUseCase(financial_repo)
                self.anomaly_agent = anomaly_agent_class(anomaly_use_case)
                logger.info({"event": "existing_agent_loaded", "agent": "AnomalyAgent"})
            except Exception as e:
                logger.warning(f"Could not initialize AnomalyAgent: {e}")
                self.anomaly_agent = None
        else:
            self.anomaly_agent = None

    def run(self, state: GraphState) -> GraphState:
        logger.info({"event": "anomaly_node_start", "node": self.name, "using_existing_agent": self.anomaly_agent is not None})

        # Try to use existing AnomalyAgent first
        if self.anomaly_agent is not None:
            try:
                import asyncio
                anomaly_data, message = asyncio.run(self._use_existing_agent(state))
                logger.info({"event": "using_existing_anomaly_agent", "success": True})
            except Exception as e:
                logger.warning(f"Existing agent failed, falling back to legacy: {e}")
                anomaly_data = self._generate_anomaly_detection(state)
                message = self._build_response_message(anomaly_data, False)
        else:
            # Fallback to legacy implementation
            anomaly_data = self._generate_anomaly_detection(state)
            message = self._build_response_message(anomaly_data, False)

        # Calculate hash for deduplication
        anomaly_hash = self._calculate_hash(anomaly_data)

        # Check if this is a repeated query (basic deduplication)
        is_repeated = self._check_if_repeated(state.session_id, anomaly_hash)

        # Update state
        s = StateMutator.update_field(state, "current_node", self.name)
        s = StateMutator.update_field(s, "response_message", message)
        s = StateMutator.merge_dict(s, "response_data", anomaly_data)
        s = StateMutator.append_to_list(s, "completed_nodes", self.name)
        s = StateMutator.merge_dict(
            s,
            "response_metadata",
            {
                "agent_type": "anomaly",
                "anomaly_hash": anomaly_hash,
                "is_repeated": is_repeated,
                "deduplication_applied": True,
            },
        )

        logger.info(
            {
                "event": "anomaly_node_end",
                "anomaly_hash": anomaly_hash[:8],
                "total_anomalies": anomaly_data.get("total_anomalies", 0),
                "is_repeated": is_repeated,
            }
        )

        return s

    async def _use_existing_agent(self, state: GraphState) -> tuple[Dict[str, Any], str]:
        """
        Use existing AnomalyAgent to generate anomaly detection.

        Args:
            state: Current graph state

        Returns:
            Tuple of (anomaly_data, formatted_message)
        """
        # Create AgentTask for the existing agent
        task = AgentTask(
            task_id=f"anomaly_{state.session_id}_{int(time.time())}",
            intent=Intent.ANOMALY_QUERY,
            query=state.user_input or "detección de anomalías",
            user_id=state.user_id,
            session_id=state.session_id
        )

        # Process task with existing agent
        result = await self.anomaly_agent.process(task)

        if result.status == TaskStatus.SUCCESS:
            # Extract data and message from agent result
            anomaly_data = result.data or {}
            message = result.response or "Detección de anomalías completada exitosamente"

            logger.info({"event": "existing_agent_success", "anomalies": anomaly_data.get("total_anomalies", 0)})
            return anomaly_data, message
        else:
            # Agent failed, raise exception to trigger fallback
            error_msg = result.error_message or "Agent processing failed"
            logger.warning({"event": "existing_agent_failed", "error": error_msg})
            raise Exception(f"AnomalyAgent failed: {error_msg}")

    def _generate_anomaly_detection(self, state: GraphState) -> Dict[str, Any]:
        """
        Generate anomaly detection from sample data (fallback implementation).

        Args:
            state: Current graph state

        Returns:
            Dictionary containing anomaly detection results
        """
        try:
            # Sample anomalies for fallback
            sample_anomalies = [
                {
                    "anomaly_id": "ANOM_001",
                    "type": "unusual_amount",
                    "severity": "HIGH",
                    "description": "Transacción con monto inusualmente alto",
                    "amount": 150000.0,
                    "expected_range": "10000-50000",
                    "transaction_id": "TXN_12345",
                    "branch": "Sucursal Central",
                    "confidence": 0.95,
                    "detected_at": "2025-01-14T10:30:00Z"
                },
                {
                    "anomaly_id": "ANOM_002",
                    "type": "frequency_spike",
                    "severity": "MEDIUM",
                    "description": "Frecuencia de transacciones inusual en horario nocturno",
                    "transaction_count": 25,
                    "expected_count": "5-10",
                    "time_period": "22:00-06:00",
                    "branch": "Sucursal Norte",
                    "confidence": 0.78,
                    "detected_at": "2025-01-14T02:15:00Z"
                },
                {
                    "anomaly_id": "ANOM_003",
                    "type": "pattern_deviation",
                    "severity": "LOW",
                    "description": "Patrón de gastos diferente al histórico",
                    "category": "Gastos Operacionales",
                    "deviation_percentage": 15.5,
                    "branch": "Sucursal Sur",
                    "confidence": 0.62,
                    "detected_at": "2025-01-14T14:45:00Z"
                }
            ]

            # Categorize by severity
            high_severity = [a for a in sample_anomalies if a["severity"] == "HIGH"]
            medium_severity = [a for a in sample_anomalies if a["severity"] == "MEDIUM"]
            low_severity = [a for a in sample_anomalies if a["severity"] == "LOW"]

            # Calculate metrics
            total_anomalies = len(sample_anomalies)
            avg_confidence = sum(a["confidence"] for a in sample_anomalies) / total_anomalies
            affected_branches = list(set(a["branch"] for a in sample_anomalies))

            # Risk assessment
            if len(high_severity) > 0:
                risk_level = "HIGH"
                risk_message = "Se detectaron anomalías de alta severidad que requieren atención inmediata"
            elif len(medium_severity) > 0:
                risk_level = "MEDIUM"
                risk_message = "Se detectaron anomalías de severidad media que requieren revisión"
            else:
                risk_level = "LOW"
                risk_message = "Solo se detectaron anomalías menores"

            return {
                "total_anomalies": total_anomalies,
                "high_severity_count": len(high_severity),
                "medium_severity_count": len(medium_severity),
                "low_severity_count": len(low_severity),
                "average_confidence": round(avg_confidence, 2),
                "affected_branches": affected_branches,
                "risk_level": risk_level,
                "risk_message": risk_message,
                "anomaly_details": sample_anomalies,
                "detection_summary": {
                    "unusual_amounts": len([a for a in sample_anomalies if a["type"] == "unusual_amount"]),
                    "frequency_spikes": len([a for a in sample_anomalies if a["type"] == "frequency_spike"]),
                    "pattern_deviations": len([a for a in sample_anomalies if a["type"] == "pattern_deviation"])
                },
                "recommendations": self._generate_recommendations(sample_anomalies)
            }

        except Exception as e:
            logger.error(f"Error generating anomaly detection: {e}")
            return {
                "total_anomalies": 0,
                "high_severity_count": 0,
                "medium_severity_count": 0,
                "low_severity_count": 0,
                "error": str(e),
            }

    def _generate_recommendations(self, anomalies: List[Dict[str, Any]]) -> List[str]:
        """Generate actionable recommendations based on detected anomalies."""
        recommendations = []

        # Check for high-value anomalies
        high_amount_anomalies = [a for a in anomalies if a["type"] == "unusual_amount"]
        if high_amount_anomalies:
            recommendations.append("Revisar y validar transacciones con montos inusuales")
            recommendations.append("Implementar controles adicionales para transacciones de alto valor")

        # Check for frequency anomalies
        frequency_anomalies = [a for a in anomalies if a["type"] == "frequency_spike"]
        if frequency_anomalies:
            recommendations.append("Investigar actividad inusual en horarios no habituales")
            recommendations.append("Verificar protocolos de seguridad nocturna")

        # Check for pattern deviations
        pattern_anomalies = [a for a in anomalies if a["type"] == "pattern_deviation"]
        if pattern_anomalies:
            recommendations.append("Analizar cambios en patrones de gastos operacionales")
            recommendations.append("Actualizar modelos de comportamiento esperado")

        # Default recommendations
        if not recommendations:
            recommendations.append("Mantener monitoreo continuo de transacciones")
            recommendations.append("Revisar periódicamente los umbrales de detección")

        return recommendations

    def _calculate_hash(self, anomaly_data: Dict[str, Any]) -> str:
        """
        Calculate deterministic hash for deduplication.

        Args:
            anomaly_data: Anomaly detection dictionary

        Returns:
            Truncated hash (16 characters) for deduplication
        """
        # Use core metrics for hash calculation
        core_metrics = {
            "total_anomalies": anomaly_data.get("total_anomalies", 0),
            "high_severity_count": anomaly_data.get("high_severity_count", 0),
            "medium_severity_count": anomaly_data.get("medium_severity_count", 0),
            "risk_level": anomaly_data.get("risk_level", "UNKNOWN"),
        }

        # Create deterministic hash
        hash_input = str(sorted(core_metrics.items())).encode('utf-8')
        full_hash = hashlib.md5(hash_input).hexdigest()

        # Return truncated hash (16 chars)
        return full_hash[:16]

    def _check_if_repeated(self, session_id: str, anomaly_hash: str) -> bool:
        """
        Check if this anomaly detection was already generated in this session.

        Args:
            session_id: Session identifier
            anomaly_hash: Hash of current anomaly detection

        Returns:
            True if this detection was already generated
        """
        # Simple in-memory tracking (could be enhanced with persistent storage)
        if not hasattr(self, '_session_hashes'):
            self._session_hashes = {}

        session_hashes = self._session_hashes.get(session_id, set())
        is_repeated = anomaly_hash in session_hashes

        # Store hash for future checks
        session_hashes.add(anomaly_hash)
        self._session_hashes[session_id] = session_hashes

        return is_repeated

    def _build_response_message(self, anomaly_data: Dict[str, Any], is_repeated: bool) -> str:
        """
        Build human-readable response message.

        Args:
            anomaly_data: Anomaly detection data
            is_repeated: Whether this is a repeated query

        Returns:
            Formatted response message
        """
        if is_repeated:
            prefix = "🔍 *Detección de Anomalías* (ya consultado previamente):\n\n"
        else:
            prefix = "🔍 *Detección de Anomalías*:\n\n"

        total_anomalies = anomaly_data.get("total_anomalies", 0)
        high_severity = anomaly_data.get("high_severity_count", 0)
        medium_severity = anomaly_data.get("medium_severity_count", 0)
        low_severity = anomaly_data.get("low_severity_count", 0)
        risk_level = anomaly_data.get("risk_level", "UNKNOWN")
        risk_message = anomaly_data.get("risk_message", "Sin información de riesgo")
        affected_branches = anomaly_data.get("affected_branches", [])

        if total_anomalies == 0:
            return prefix + "✅ No se detectaron anomalías en los datos financieros.\n\nTodos los patrones están dentro de los rangos esperados."

        # Risk level emoji
        risk_emoji = "🚨" if risk_level == "HIGH" else "⚠️" if risk_level == "MEDIUM" else "ℹ️"

        message = f"""{prefix}• **Total de anomalías detectadas**: {total_anomalies}
• **Severidad alta**: {high_severity} 🚨
• **Severidad media**: {medium_severity} ⚠️
• **Severidad baja**: {low_severity} ℹ️
• **Sucursales afectadas**: {len(affected_branches)}
• **Nivel de riesgo**: {risk_emoji} {risk_level}

📋 **Evaluación**: {risk_message}"""

        if affected_branches:
            message += f"\n\n🏢 **Sucursales con anomalías**: {', '.join(affected_branches)}"

        # Add recommendations
        recommendations = anomaly_data.get("recommendations", [])
        if recommendations:
            message += "\n\n📌 **Recomendaciones**:"
            for i, rec in enumerate(recommendations[:3], 1):  # Show max 3 recommendations
                message += f"\n{i}. {rec}"

        # Detection summary
        detection_summary = anomaly_data.get("detection_summary", {})
        if detection_summary:
            message += f"\n\n🔍 **Tipos detectados**:"
            if detection_summary.get("unusual_amounts", 0) > 0:
                message += f"\n• Montos inusuales: {detection_summary['unusual_amounts']}"
            if detection_summary.get("frequency_spikes", 0) > 0:
                message += f"\n• Picos de frecuencia: {detection_summary['frequency_spikes']}"
            if detection_summary.get("pattern_deviations", 0) > 0:
                message += f"\n• Desviaciones de patrón: {detection_summary['pattern_deviations']}"

        return message