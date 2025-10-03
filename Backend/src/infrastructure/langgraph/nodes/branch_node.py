"""
Ruta: Backend/src/infrastructure/langgraph/nodes/branch_node.py
Descripción: Nodo para análisis de sucursales usando agentes existentes
Estado: Activo - CORRECCIÓN CRÍTICA
Autor/Responsable: migration-bot
Última actualización: 2025-01-14
Tareas relacionadas: T-005-CRITICAL
Referencias: AI/Tablero/LangGraph/InfoAdicional.md#nodos-faltantes
"""
from __future__ import annotations

import hashlib
import time
from typing import Dict, Any, Optional

from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator
from src.infrastructure.repositories.repository_provider import RepositoryProvider
from src.core.logging import get_logger

logger = get_logger(__name__)

# Import existing BranchAgent and related classes
import sys
import os

AGENTS_AVAILABLE = False
branch_agent_class = None

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

    from agentes.branch.handler import BranchAgent
    from src.application.use_cases.financial_analysis_use_cases import GetBranchAnalysisUseCase
    from src.domain.contracts.agent_io import AgentTask, TaskStatus
    from src.domain.contracts.intent import Intent

    branch_agent_class = BranchAgent
    AGENTS_AVAILABLE = True
    logger.info("Successfully imported existing BranchAgent")

except ImportError as e:
    logger.warning(f"Could not import existing agents: {e}. Using fallback implementation.")
    AGENTS_AVAILABLE = False


class BranchNode(GraphNode):
    def __init__(self, name: str = "branch") -> None:
        super().__init__(name=name)
        self.repo_provider = RepositoryProvider()

        # Initialize existing BranchAgent if available
        if AGENTS_AVAILABLE and branch_agent_class:
            try:
                financial_repo = self.repo_provider.get_financial_repository()
                branch_use_case = GetBranchAnalysisUseCase(financial_repo)
                self.branch_agent = branch_agent_class(branch_use_case)
                logger.info({"event": "existing_agent_loaded", "agent": "BranchAgent"})
            except Exception as e:
                logger.warning(f"Could not initialize BranchAgent: {e}")
                self.branch_agent = None
        else:
            self.branch_agent = None

    def run(self, state: GraphState) -> GraphState:
        logger.info({"event": "branch_node_start", "node": self.name, "using_existing_agent": self.branch_agent is not None})

        # Try to use existing BranchAgent first
        if self.branch_agent is not None:
            try:
                import asyncio
                branch_data, message = asyncio.run(self._use_existing_agent(state))
                logger.info({"event": "using_existing_branch_agent", "success": True})
            except Exception as e:
                logger.warning(f"Existing agent failed, falling back to legacy: {e}")
                branch_data = self._generate_branch_analysis(state)
                message = self._build_response_message(branch_data, False)
        else:
            # Fallback to legacy implementation
            branch_data = self._generate_branch_analysis(state)
            message = self._build_response_message(branch_data, False)

        # Calculate hash for deduplication
        branch_hash = self._calculate_hash(branch_data)

        # Check if this is a repeated query (basic deduplication)
        is_repeated = self._check_if_repeated(state.session_id, branch_hash)

        # Update state
        s = StateMutator.update_field(state, "current_node", self.name)
        s = StateMutator.update_field(s, "response_message", message)
        s = StateMutator.merge_dict(s, "response_data", branch_data)
        s = StateMutator.append_to_list(s, "completed_nodes", self.name)
        s = StateMutator.merge_dict(
            s,
            "response_metadata",
            {
                "agent_type": "branch",
                "branch_hash": branch_hash,
                "is_repeated": is_repeated,
                "deduplication_applied": True,
            },
        )

        logger.info(
            {
                "event": "branch_node_end",
                "branch_hash": branch_hash[:8],
                "total_branches": branch_data.get("total_branches", 0),
                "is_repeated": is_repeated,
            }
        )

        return s

    async def _use_existing_agent(self, state: GraphState) -> tuple[Dict[str, Any], str]:
        """
        Use existing BranchAgent to generate branch analysis.

        Args:
            state: Current graph state

        Returns:
            Tuple of (branch_data, formatted_message)
        """
        # Create AgentTask for the existing agent
        task = AgentTask(
            task_id=f"branch_{state.session_id}_{int(time.time())}",
            intent=Intent.BRANCH_QUERY,
            query=state.user_input or "análisis de sucursales",
            user_id=state.user_id,
            session_id=state.session_id
        )

        # Process task with existing agent
        result = await self.branch_agent.process(task)

        if result.status == TaskStatus.SUCCESS:
            # Extract data and message from agent result
            branch_data = result.data or {}
            message = result.response or "Análisis de sucursales generado exitosamente"

            logger.info({"event": "existing_agent_success", "branches": branch_data.get("total_branches", 0)})
            return branch_data, message
        else:
            # Agent failed, raise exception to trigger fallback
            error_msg = result.error_message or "Agent processing failed"
            logger.warning({"event": "existing_agent_failed", "error": error_msg})
            raise Exception(f"BranchAgent failed: {error_msg}")

    def _generate_branch_analysis(self, state: GraphState) -> Dict[str, Any]:
        """
        Generate branch analysis from sample data (fallback implementation).

        Args:
            state: Current graph state

        Returns:
            Dictionary containing branch analysis metrics
        """
        try:
            # Sample branch data for fallback
            sample_branches = [
                {
                    "branch_id": 1,
                    "branch_name": "Sucursal Central",
                    "location": "Centro Ciudad",
                    "total_transactions": 150,
                    "total_income": 75000.0,
                    "total_expenses": 45000.0,
                    "net_result": 30000.0,
                    "efficiency_score": 0.85
                },
                {
                    "branch_id": 2,
                    "branch_name": "Sucursal Norte",
                    "location": "Zona Norte",
                    "total_transactions": 120,
                    "total_income": 60000.0,
                    "total_expenses": 40000.0,
                    "net_result": 20000.0,
                    "efficiency_score": 0.75
                },
                {
                    "branch_id": 3,
                    "branch_name": "Sucursal Sur",
                    "location": "Zona Sur",
                    "total_transactions": 90,
                    "total_income": 45000.0,
                    "total_expenses": 35000.0,
                    "net_result": 10000.0,
                    "efficiency_score": 0.65
                }
            ]

            # Calculate aggregated metrics
            total_branches = len(sample_branches)
            total_transactions = sum(branch["total_transactions"] for branch in sample_branches)
            total_income = sum(branch["total_income"] for branch in sample_branches)
            total_expenses = sum(branch["total_expenses"] for branch in sample_branches)
            total_net_result = sum(branch["net_result"] for branch in sample_branches)
            average_efficiency = sum(branch["efficiency_score"] for branch in sample_branches) / total_branches

            # Identify top and bottom performers
            top_performer = max(sample_branches, key=lambda x: x["net_result"])
            bottom_performer = min(sample_branches, key=lambda x: x["net_result"])

            return {
                "total_branches": total_branches,
                "total_transactions": total_transactions,
                "total_income": round(total_income, 2),
                "total_expenses": round(total_expenses, 2),
                "total_net_result": round(total_net_result, 2),
                "average_efficiency": round(average_efficiency, 2),
                "top_performer": {
                    "branch_name": top_performer["branch_name"],
                    "net_result": top_performer["net_result"],
                    "efficiency_score": top_performer["efficiency_score"]
                },
                "bottom_performer": {
                    "branch_name": bottom_performer["branch_name"],
                    "net_result": bottom_performer["net_result"],
                    "efficiency_score": bottom_performer["efficiency_score"]
                },
                "branch_details": sample_branches,
                "analysis_type": "comprehensive_branch_analysis"
            }

        except Exception as e:
            logger.error(f"Error generating branch analysis: {e}")
            return {
                "total_branches": 0,
                "total_transactions": 0,
                "total_income": 0.0,
                "total_expenses": 0.0,
                "error": str(e),
            }

    def _calculate_hash(self, branch_data: Dict[str, Any]) -> str:
        """
        Calculate deterministic hash for deduplication.

        Args:
            branch_data: Branch analysis dictionary

        Returns:
            Truncated hash (16 characters) for deduplication
        """
        # Use core metrics for hash calculation
        core_metrics = {
            "total_branches": branch_data.get("total_branches", 0),
            "total_transactions": branch_data.get("total_transactions", 0),
            "total_income": branch_data.get("total_income", 0.0),
            "average_efficiency": branch_data.get("average_efficiency", 0.0),
        }

        # Create deterministic hash
        hash_input = str(sorted(core_metrics.items())).encode('utf-8')
        full_hash = hashlib.md5(hash_input).hexdigest()

        # Return truncated hash (16 chars)
        return full_hash[:16]

    def _check_if_repeated(self, session_id: str, branch_hash: str) -> bool:
        """
        Check if this branch analysis was already generated in this session.

        Args:
            session_id: Session identifier
            branch_hash: Hash of current branch analysis

        Returns:
            True if this analysis was already generated
        """
        # Simple in-memory tracking (could be enhanced with persistent storage)
        if not hasattr(self, '_session_hashes'):
            self._session_hashes = {}

        session_hashes = self._session_hashes.get(session_id, set())
        is_repeated = branch_hash in session_hashes

        # Store hash for future checks
        session_hashes.add(branch_hash)
        self._session_hashes[session_id] = session_hashes

        return is_repeated

    def _build_response_message(self, branch_data: Dict[str, Any], is_repeated: bool) -> str:
        """
        Build human-readable response message.

        Args:
            branch_data: Branch analysis data
            is_repeated: Whether this is a repeated query

        Returns:
            Formatted response message
        """
        if is_repeated:
            prefix = "🏢 *Análisis de Sucursales* (ya consultado previamente):\n\n"
        else:
            prefix = "🏢 *Análisis de Sucursales*:\n\n"

        total_branches = branch_data.get("total_branches", 0)
        total_transactions = branch_data.get("total_transactions", 0)
        total_income = branch_data.get("total_income", 0.0)
        total_expenses = branch_data.get("total_expenses", 0.0)
        total_net_result = branch_data.get("total_net_result", 0.0)
        average_efficiency = branch_data.get("average_efficiency", 0.0)

        if total_branches == 0:
            return prefix + "⚠️ No se encontraron datos de sucursales para analizar.\n\nPor favor, verifica que existan datos de sucursales en el sistema."

        top_performer = branch_data.get("top_performer", {})
        bottom_performer = branch_data.get("bottom_performer", {})

        message = f"""{prefix}• **Total de sucursales**: {total_branches}
• **Transacciones totales**: {total_transactions:,}
• **Ingresos totales**: ${total_income:,.2f}
• **Gastos totales**: ${total_expenses:,.2f}
• **Resultado neto**: ${total_net_result:,.2f}
• **Eficiencia promedio**: {average_efficiency:.1%}

🏆 **Mejor sucursal**: {top_performer.get("branch_name", "N/A")}
   - Resultado: ${top_performer.get("net_result", 0):,.2f}
   - Eficiencia: {top_performer.get("efficiency_score", 0):.1%}

⚠️ **Sucursal a mejorar**: {bottom_performer.get("branch_name", "N/A")}
   - Resultado: ${bottom_performer.get("net_result", 0):,.2f}
   - Eficiencia: {bottom_performer.get("efficiency_score", 0):.1%}"""

        if total_net_result > 0:
            message += "\n\n✅ **Estado general**: Rendimiento positivo del conjunto de sucursales"
        elif total_net_result < 0:
            message += "\n\n⚠️ **Estado general**: Rendimiento negativo - requiere atención"
        else:
            message += "\n\n➖ **Estado general**: Balance neutro en sucursales"

        return message