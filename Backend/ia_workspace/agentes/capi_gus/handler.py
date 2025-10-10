#!/usr/bin/env python3
"""
CAPI - Capi Gus Agent (Agente de Respuestas Amigables)
=====================================================
Ruta: /ia_workspace/agentes/capi_gus/handler.py
Descripción: Agente especializado en entregar conclusiones claras basadas en los datos
             generados por Capi DataB y Capi El Cajas.
Estado: ✅ AGENTE CORE ACTIVO - Respuesta ejecutiva
Dependencias: BaseAgent, AgentTask, FinancialSummaryUseCase
Intenciones: summary, summary_request
Salidas: total_records, métricas, branch_summaries, anomalies_summary
Propósito: Proporcionar vista general de datos financieros procesados
"""
import time
from typing import List

from ...domain.agents.agent_protocol import BaseAgent
from ...domain.contracts.intent import Intent
from ...domain.contracts.agent_io import AgentTask, AgentResult, TaskStatus
from ...application.use_cases.financial_analysis_use_cases import GetFinancialSummaryUseCase
from ...core.logging.tracing import get_traced_logger
from ...infrastructure.agents.progress_emitter import agent_progress

logger = get_traced_logger(__name__)


class CapiGusAgent(BaseAgent):
    """
    Agent responsible for generating financial data summaries.
    
    Delegates to the GetFinancialSummaryUseCase for actual summary generation.
    """
    
    def __init__(self, summary_use_case: GetFinancialSummaryUseCase):
        """
        Initialize the summary agent.
        
        Args:
            summary_use_case: Use case for generating summaries
        """
        super().__init__(name="CapiGusAgent")
        self.summary_use_case = summary_use_case
    
    @property
    def supported_intents(self) -> List[Intent]:
        """Return intents this agent can handle."""
        return [Intent.SUMMARY_REQUEST, Intent.SUMMARY]  # Soportar ambos para compatibilidad
    
    async def process(self, task: AgentTask) -> AgentResult:
        """
        Process a summary request task.

        Args:
            task: Task to process

        Returns:
            AgentResult with summary data
        """
        start_time = time.time()

        agent_progress.start(
            self.agent_name,
            task.session_id,
            query=task.query,
            extra={'intent': getattr(task, 'intent', None)}
        )

        try:
            logger.info(f"Processing summary request: {task.task_id}")

            if task.intent not in [Intent.SUMMARY_REQUEST, Intent.SUMMARY]:
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
                    message=f"Invalid intent '{task.intent}' for CapiGusAgent",
                    processing_time_ms=(time.time() - start_time) * 1000
                )

            summary_data = await self.summary_use_case.execute()

            data_dict = summary_data.get("data", {})
            metrics = data_dict.get("metrics", {})
            anomalies_summary = data_dict.get("anomalies_summary", {})
            branch_summaries = data_dict.get("branch_summaries", [])

            total_ingresos = metrics.get("total_ingresos", 0)
            total_egresos = metrics.get("total_egresos", 0)
            net_flow = total_ingresos - total_egresos
            branch_count = len(branch_summaries)
            anomaly_count = anomalies_summary.get("total_anomalies", 0)
            transaction_count = data_dict.get("records_count", 0)

            response_data = {
                "summary_type": "financial_overview",
                "total_records": transaction_count,
                "raw_metrics": metrics,
                "anomalies_summary": anomalies_summary,
                "branch_summaries": branch_summaries,
                "metrics": {
                    "total_cash": total_ingresos,
                    "total_expenses": total_egresos,
                    "net_flow": net_flow,
                    "anomaly_count": anomaly_count,
                    "branch_count": branch_count,
                    "total_transactions": transaction_count
                }
            }

            message = f"Resumen financiero generado: {response_data['total_records']} registros procesados"
            processing_time = (time.time() - start_time) * 1000

            agent_progress.success(
                self.agent_name,
                task.session_id,
                detail=message,
                extra={'records': transaction_count, 'branches': branch_count}
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
            logger.error(f"Error processing summary task {task.task_id}: {str(e)}")
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
                message=f"Error generando resumen: {str(e)}",
                processing_time_ms=processing_time
            )
