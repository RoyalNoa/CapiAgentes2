#!/usr/bin/env python3
"""
CAPI - Branch Agent (Agente de Análisis por Sucursales)
======================================================
Ruta: /ia_workspace/agentes/branch/handler.py
Descripción: Agente especializado en analizar desempeño por sucursal y
comparaciones entre ellas. Genera rankings y métricas comparativas.
Estado: ✅ AGENTE CORE ACTIVO - Análisis de sucursales
Dependencias: BaseAgent, AgentTask, BranchAnalysisUseCase
Intenciones: branch_query
Entradas: branch_name (opcional)
Salidas: ranking, mejores/peores, métricas comparativas
Propósito: Análisis detallado del rendimiento por sucursal
"""
import time
from typing import List

from ...domain.agents.agent_protocol import BaseAgent
from ...domain.contracts.intent import Intent
from ...domain.contracts.agent_io import AgentTask, AgentResult, TaskStatus
from ...application.use_cases.financial_analysis_use_cases import GetBranchAnalysisUseCase
from ...core.logging.tracing import get_traced_logger
from ...infrastructure.agents.progress_emitter import agent_progress

logger = get_traced_logger(__name__)


class BranchAgent(BaseAgent):
    """
    Agent responsible for branch-specific financial analysis.
    
    Delegates to the GetBranchAnalysisUseCase for actual analysis.
    """
    
    def __init__(self, branch_use_case: GetBranchAnalysisUseCase):
        """
        Initialize the branch agent.
        
        Args:
            branch_use_case: Use case for branch analysis
        """
        super().__init__(name="BranchAgent")
        self.branch_use_case = branch_use_case
    
    @property
    def supported_intents(self) -> List[Intent]:
        """Return intents this agent can handle."""
        return [Intent.BRANCH_QUERY]
    
    async def process(self, task: AgentTask) -> AgentResult:
        """
        Process a branch query task.

        Args:
            task: Task to process

        Returns:
            AgentResult with branch analysis data
        """
        start_time = time.time()

        agent_progress.start(
            self.agent_name,
            task.session_id,
            query=task.query,
            extra={'intent': getattr(task, 'intent', None)}
        )

        try:
            logger.info(f"Processing branch query: {task.task_id}")

            if task.intent != Intent.BRANCH_QUERY:
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
                    message=f"Invalid intent '{task.intent}' for BranchAgent",
                    processing_time_ms=(time.time() - start_time) * 1000
                )

            branch_name = self._extract_branch_name(task.query, task.context)

            if branch_name and branch_name.strip():
                branch_data = await self.branch_use_case.execute(branch_name)
            else:
                branch_data = await self.branch_use_case.execute()
                branch_name = ""

            response_data = {
                "analysis_type": "branch_performance",
                "branch_name": branch_name,
                "total_branches": branch_data.get("total_branches", 0),
                "branch_metrics": branch_data.get("branch_metrics", {}),
                "comparison_data": branch_data.get("comparison", {}),
                "top_performing": branch_data.get("top_performing", []),
                "underperforming": branch_data.get("underperforming", [])
            }

            if branch_name:
                message = f"Análisis de sucursal '{branch_name}' completado"
            else:
                message = f"Análisis de {response_data['total_branches']} sucursales completado"

            processing_time = (time.time() - start_time) * 1000

            agent_progress.success(
                self.agent_name,
                task.session_id,
                detail=message,
                branch=branch_name or None,
                extra={'branches': response_data['total_branches']}
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
            logger.error(f"Error processing branch task {task.task_id}: {str(e)}")
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
                message=f"Error analizando sucursales: {str(e)}",
                processing_time_ms=processing_time
            )
    def _extract_branch_name(self, query: str, context: dict) -> str:
        """
        Extract branch name from query or context.
        
        Args:
            query: User query string
            context: Task context
            
        Returns:
            Branch name if found, empty string otherwise
        """
        # Check context first
        if context and "branch_name" in context:
            return context["branch_name"]
        
        # Simple extraction from query (can be enhanced with NLP)
        query_lower = query.lower()
        
        # Common branch name patterns
        branch_indicators = ["sucursal", "branch", "oficina", "office"]
        
        for indicator in branch_indicators:
            # Use word boundaries to avoid partial matches
            import re
            pattern = r'\b' + re.escape(indicator) + r'\b'
            if re.search(pattern, query_lower):
                # Look for text after the indicator
                parts = re.split(pattern, query_lower)
                if len(parts) > 1:
                    # Extract potential branch name (first non-empty word after indicator)
                    remaining_text = parts[1].strip()
                    if remaining_text:
                        # Skip common connecting words
                        words = remaining_text.split()
                        for word in words:
                            if word not in ["de", "la", "el", "del", "performance", "of", "the", "todas", "all"]:
                                if len(word) > 2:  # Minimum 3 characters for branch name
                                    return word.title()
                        # If no good word found after filtering, don't return anything
                        return ""
        
        return ""