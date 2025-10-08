"""Anomaly agent implementation for anomaly detection and analysis."""
import time
from typing import List

from ...domain.agents.agent_protocol import BaseAgent
from ...domain.contracts.intent import Intent
from ...domain.contracts.agent_io import AgentTask, AgentResult, TaskStatus
from ...application.use_cases.financial_analysis_use_cases import GetAnomalyAnalysisUseCase
from ...core.logging.tracing import get_traced_logger
from ...infrastructure.agents.progress_emitter import agent_progress

logger = get_traced_logger(__name__)


class AnomalyAgent(BaseAgent):
    """
    Agent responsible for anomaly detection and analysis.
    
    Delegates to the GetAnomalyAnalysisUseCase for actual anomaly detection.
    """
    
    def __init__(self, anomaly_use_case: GetAnomalyAnalysisUseCase):
        """
        Initialize the anomaly agent.
        
        Args:
            anomaly_use_case: Use case for anomaly analysis
        """
        super().__init__(name="AnomalyAgent")
        self.anomaly_use_case = anomaly_use_case
    
    @property
    def supported_intents(self) -> List[Intent]:
        """Return intents this agent can handle."""
        return [Intent.ANOMALY_QUERY]
    
    async def process(self, task: AgentTask) -> AgentResult:
        """
        Process an anomaly detection task.

        Args:
            task: Task to process

        Returns:
            AgentResult with anomaly detection data
        """
        start_time = time.time()

        agent_progress.start(
            self.agent_name,
            task.session_id,
            query=task.query,
            extra={'intent': getattr(task, 'intent', None)}
        )

        try:
            logger.info(f"Processing anomaly query: {task.task_id}")

            if task.intent != Intent.ANOMALY_QUERY:
                agent_progress.error(
                    self.agent_name,
                    task.session_id,
                    detail=f"Intento no soportado: {task.intent}",
                    extra={'intent': task.intent}
                )
                return AgentResult(
                    task_id=task.task_id,
                    agent_name=self.agent_name,
                    status=TaskStatus.FAILED,
                    message=f"Invalid intent '{task.intent}' for AnomalyAgent",
                    processing_time_ms=(time.time() - start_time) * 1000
                )

            detection_params = self._extract_detection_params(task.query, task.context)
            anomaly_data = await self.anomaly_use_case.execute()

            anomalies = anomaly_data.get("anomalies", [])
            response_data = {
                "detection_type": "financial_anomalies",
                "total_anomalies": len(anomalies),
                "anomalies": anomalies,
                "detection_params": detection_params,
                "severity_distribution": self._calculate_severity_distribution(anomalies),
                "time_range": anomaly_data.get("time_range", {}),
                "detection_summary": anomaly_data.get("summary", {})
            }

            severity_summary = self._format_severity_summary(response_data["severity_distribution"])
            message = f"Detección de anomalías completada: {len(anomalies)} anomalías encontradas"
            if severity_summary:
                message += f" ({severity_summary})"

            processing_time = (time.time() - start_time) * 1000

            agent_progress.success(
                self.agent_name,
                task.session_id,
                detail=message,
                extra={'anomalies': len(anomalies)}
            )

            return AgentResult(
                task_id=task.task_id,
                agent_name=self.agent_name,
                status=TaskStatus.COMPLETED,
                data=response_data,
                message=message,
                processing_time_ms=processing_time
            )

        except Exception as e:
            logger.error(f"Error processing anomaly task {task.task_id}: {str(e)}")
            processing_time = (time.time() - start_time) * 1000

            agent_progress.error(
                self.agent_name,
                task.session_id,
                detail=str(e),
                extra={'intent': getattr(task, 'intent', None)}
            )

            return AgentResult(
                task_id=task.task_id,
                agent_name=self.agent_name,
                status=TaskStatus.FAILED,
                message=f"Error detectando anomalías: {str(e)}",
                processing_time_ms=processing_time
            )
    def _extract_detection_params(self, query: str, context: dict) -> dict:
        """
        Extract anomaly detection parameters from query and context.
        
        Args:
            query: User query string
            context: Task context
            
        Returns:
            Dictionary with detection parameters
        """
        params = {}
        
        # Check context for explicit parameters
        if context:
            if "threshold" in context:
                params["threshold"] = context["threshold"]
            if "time_range" in context:
                params["time_range"] = context["time_range"]
            if "anomaly_type" in context:
                params["anomaly_type"] = context["anomaly_type"]
        
        # Extract parameters from query (simple keyword matching)
        query_lower = query.lower()
        
        # Detect severity keywords
        if any(word in query_lower for word in ["critico", "criticas", "critical", "grave", "severe"]):
            params["min_severity"] = "high"
        elif any(word in query_lower for word in ["menor", "menores", "minor", "leve", "light"]):
            params["min_severity"] = "low"
        else:
            params["min_severity"] = "medium"  # default
        
        # Detect time range keywords
        if any(word in query_lower for word in ["hoy", "today", "actual"]):
            params["time_period"] = "today"
        elif any(word in query_lower for word in ["semana", "week"]):
            params["time_period"] = "week"
        elif any(word in query_lower for word in ["mes", "month"]):
            params["time_period"] = "month"
        else:
            params["time_period"] = "all"  # default
        
        return params
    
    def _calculate_severity_distribution(self, anomalies: List[dict]) -> dict:
        """
        Calculate distribution of anomalies by severity.
        
        Args:
            anomalies: List of anomaly records
            
        Returns:
            Dictionary with severity counts
        """
        distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        
        for anomaly in anomalies:
            severity = anomaly.get("severity", "medium").lower()
            if severity in distribution:
                distribution[severity] += 1
            else:
                distribution["medium"] += 1  # default for unknown severities
        
        return distribution
    
    def _format_severity_summary(self, distribution: dict) -> str:
        """
        Format severity distribution as a readable summary.
        
        Args:
            distribution: Severity distribution dictionary
            
        Returns:
            Formatted string summary
        """
        summary_parts = []
        
        if distribution.get("critical", 0) > 0:
            summary_parts.append(f"{distribution['critical']} críticas")
        if distribution.get("high", 0) > 0:
            summary_parts.append(f"{distribution['high']} altas")
        if distribution.get("medium", 0) > 0:
            summary_parts.append(f"{distribution['medium']} medias")
        if distribution.get("low", 0) > 0:
            summary_parts.append(f"{distribution['low']} bajas")
        
        return ", ".join(summary_parts)