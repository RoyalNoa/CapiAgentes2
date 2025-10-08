"""
Enhanced Graph Runtime with Optimized Algorithm Integration
==========================================================

Integrates the OptimizedGraph algorithm with the existing LangGraph runtime,
providing backwards compatibility while delivering superior performance.

Features:
- Drop-in replacement for current RuntimeGraph
- Maintains existing API contracts
- Adds advanced graph analysis capabilities
- Provides comprehensive performance monitoring
"""

from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Tuple, Any, Optional, Set
from dataclasses import dataclass
import time
from collections import defaultdict

from src.infrastructure.langgraph.state_schema import GraphState
from src.infrastructure.langgraph.algorithms.optimized_graph import (
    OptimizedGraph, GraphNode as OptNode, GraphEdge, EdgeType
)
from src.infrastructure.langgraph.nodes.base import GraphNode
from src.core.logging import get_logger
from src.infrastructure.websocket.event_broadcaster import get_event_broadcaster

logger = get_logger(__name__)


@dataclass
class ExecutionMetrics:
    """Comprehensive execution metrics for performance analysis"""
    total_steps: int = 0
    execution_time: float = 0.0
    node_execution_times: Dict[str, float] = None
    cache_hit_rate: float = 0.0
    graph_traversal_count: int = 0
    memory_usage_mb: float = 0.0

    def __post_init__(self):
        if self.node_execution_times is None:
            self.node_execution_times = {}


class EnhancedRuntimeGraph:
    """
    Enhanced runtime graph with optimized algorithm backend

    Provides drop-in replacement for existing RuntimeGraph while adding:
    - O(1) node access via optimized indexing
    - Bidirectional BFS for shortest paths
    - Intelligent caching for repeated queries
    - Advanced graph analysis capabilities
    """

    def __init__(self, nodes: Dict[str, GraphNode],
                 edges: List[Tuple[str, str]],
                 entrypoint: str):
        """Initialize enhanced runtime with backwards compatibility"""
        # Maintain original interface
        self.nodes = nodes
        self.edges = edges
        self.entrypoint = entrypoint

        # Legacy adjacency list for compatibility
        self._adj: Dict[str, List[str]] = {}
        for src, dst in self.edges:
            self._adj.setdefault(src, []).append(dst)

        # Initialize optimized graph backend
        self._optimized_graph = OptimizedGraph(initial_capacity=len(nodes) * 2)
        self._node_execution_cache: Dict[str, Any] = {}
        self._execution_metrics = ExecutionMetrics()
        self._event_broadcaster = get_event_broadcaster()

        # Build optimized representation
        self._build_optimized_backend()

        # Performance monitoring
        self._start_time = time.time()
        self._last_optimization = time.time()
        self._optimization_interval = 300  # 5 minutes

    def _schedule_event(self, coro):
        """Dispatch coroutine without blocking current thread."""
        if coro is None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                asyncio.run(coro)
            except Exception as exc:
                logger.warning(f'Failed to dispatch event: {exc}')
        else:
            loop.create_task(coro)

    def _state_snapshot(self, state: GraphState) -> Dict[str, Any]:
        try:
            return state.to_frontend_format()
        except Exception as exc:
            logger.debug(f'Unable to serialize state snapshot: {exc}')
            return {"trace_id": getattr(state, 'trace_id', None)}

    def _record_state(self, session_id: str, state: GraphState):
        if not self._event_broadcaster or not session_id:
            return
        snapshot = self._state_snapshot(state)
        self._event_broadcaster.update_session_state(session_id, snapshot)

    def _map_node_to_action(self, node_name: str) -> str:
        """Map node name to semantic action type for frontend display."""
        node_lower = node_name.lower()

        action_map = {
            'intent': 'intent',
            'planner': 'planner',
            'analysis': 'analysis',
            'research': 'research',
            'execution': 'execution',
            'validation': 'validation',
            'response': 'response',
            'supervisor': 'planner',
            'router': 'intent',
            'summary': 'summary_generation',
            'branch': 'branch_analysis',
            'anomaly': 'anomaly_detection',
            'datab': 'database_query',
            'capidatab': 'database_query',
        }

        return action_map.get(node_lower, node_name.lower())

    def _emit_transition(self, previous: str, following: Optional[str], session_id: str, state: GraphState, step_index: int):
        if not self._event_broadcaster or not previous:
            return
        snapshot = self._state_snapshot(state)
        meta = {
            'trace_id': getattr(state, 'trace_id', None),
            'current_node': getattr(state, 'current_node', None),
            'status': getattr(getattr(state, 'status', None), 'value', None),
            'intent': getattr(getattr(state, 'detected_intent', None), 'value', None),
            'completed_nodes': list(getattr(state, 'completed_nodes', []) or []),
            'step': step_index,
            'state': snapshot,
        }
        clean_meta = {k: v for k, v in meta.items() if v is not None}
        # Map node to semantic action
        action = self._map_node_to_action(following) if following else None
        self._schedule_event(
            self._event_broadcaster.broadcast_node_transition(
                from_node=previous,
                to_node=following,
                session_id=session_id or 'unknown',
                action=action,
                meta=clean_meta
            )
        )

    def run(self, state: GraphState, max_steps: int = 50) -> GraphState:
        current = self.entrypoint
        steps = 0
        s = state
        session_id = getattr(state, "session_id", "") or "unknown"
        self._record_state(session_id, state)
        while current and steps < max_steps:
            previous = current
            s, current = self.step(s, current)
            self._record_state(session_id, s)
            step_index = steps + 1
            self._emit_transition(previous, current, session_id, s, step_index)
            steps += 1
        self._record_state(session_id, s)
        logger.info({
            "event": "graph_run_complete",
            "steps": steps
        })
        return s

    def _build_optimized_backend(self):
        """Build optimized graph representation from legacy format"""
        logger.info("Building optimized graph backend")

        # Add all nodes to optimized graph
        for node_id, node in self.nodes.items():
            # Extract node type from class name
            node_type = type(node).__name__.lower().replace('node', '')

            opt_node = OptNode(
                id=node_id,
                node_type=node_type,
                priority=getattr(node, 'priority', 0),
                metadata={
                    'original_class': type(node).__name__,
                    'has_condition': hasattr(node, 'condition'),
                }
            )
            self._optimized_graph.add_node(opt_node)

        # Add all edges with intelligent type detection
        for src, dst in self.edges:
            edge_type = self._detect_edge_type(src, dst)
            self._optimized_graph.add_edge(src, dst, edge_type=edge_type)

        # Optimize layout for better performance
        self._optimized_graph.optimize_layout()

        logger.info(f"Optimized backend built: {len(self.nodes)} nodes, {len(self.edges)} edges")

    def _detect_edge_type(self, source: str, target: str) -> EdgeType:
        """Intelligently detect edge type based on node names and patterns"""

        # Router nodes typically have conditional edges
        if 'router' in source.lower():
            return EdgeType.CONDITIONAL

        # Assemble nodes typically merge multiple inputs
        if 'assemble' in target.lower():
            return EdgeType.MERGE

        # Parallel processing patterns
        source_neighbors = self._adj.get(source, [])
        if len(source_neighbors) > 1:
            return EdgeType.PARALLEL

        # Default to sequential
        return EdgeType.SEQUENTIAL

    def step(self, state: GraphState, current: str) -> Tuple[GraphState, str | None]:
        """Enhanced step with performance monitoring and caching"""
        step_start = time.time()

        # Check if we should auto-optimize
        if (time.time() - self._last_optimization) > self._optimization_interval:
            self._auto_optimize()

        # Execute original step logic with enhancements
        node = self.nodes[current]
        logger.debug({"event": "enhanced_node_start", "node": current})

        # Check execution cache for deterministic nodes
        cache_key = (current, hash(str(state.original_query)))
        if self._should_use_cache(current) and cache_key in self._node_execution_cache:
            cached_result = self._node_execution_cache[cache_key]
            logger.debug({"event": "cache_hit", "node": current})
            self._execution_metrics.cache_hit_rate += 1
            new_state = cached_result['state']
            next_name = cached_result['next']
        else:
            # Execute node
            new_state = node.run(state)

            # Determine next node using optimized pathfinding
            next_name = self._get_next_node_optimized(current, new_state)

            # Cache result if appropriate
            if self._should_use_cache(current):
                self._node_execution_cache[cache_key] = {
                    'state': new_state,
                    'next': next_name
                }

        # Record execution metrics
        execution_time = time.time() - step_start
        self._execution_metrics.node_execution_times[current] = execution_time
        self._execution_metrics.total_steps += 1

        logger.debug({
            "event": "enhanced_node_end",
            "node": current,
            "next": next_name,
            "execution_time": execution_time
        })

        return new_state, next_name

    def _get_next_node_optimized(self, current: str, state: GraphState) -> str | None:
        """Get next node using optimized algorithms"""

        # Handle conditional routing from router node with optimization
        if current == "router" and hasattr(state, 'routing_decision'):
            routing_decision = state.routing_decision

            # Use optimized graph to verify reachability
            if routing_decision in self.nodes:
                reachable = self._optimized_graph.get_reachable_nodes(routing_decision)
                if 'finalize' in reachable:  # Ensure path to completion
                    return routing_decision

            # Fallback with optimal path to assemble
            logger.debug({
                "event": "conditional_routing_fallback",
                "node": current,
                "decision": routing_decision
            })
            return "assemble"

        # Standard edge following with optimization
        neighbors = self._optimized_graph.get_neighbors(current)
        if neighbors:
            # Select best neighbor based on criteria
            return self._select_optimal_neighbor(current, neighbors, state)

        return None

    def _select_optimal_neighbor(self, current: str,
                               neighbors: List[Tuple[str, GraphEdge]],
                               state: GraphState) -> str:
        """Select optimal neighbor based on various criteria"""

        if len(neighbors) == 1:
            return neighbors[0][0]

        # Multi-criteria selection
        scored_neighbors = []

        for neighbor_id, edge in neighbors:
            score = 0.0

            # Priority scoring
            if neighbor_id in self.nodes:
                node_priority = getattr(self.nodes[neighbor_id], 'priority', 0)
                score += node_priority * 10

            # Edge type scoring
            if edge.edge_type == EdgeType.CONDITIONAL:
                score += 5
            elif edge.edge_type == EdgeType.SEQUENTIAL:
                score += 3

            # Weight scoring
            score += edge.weight

            # Historical performance scoring
            if neighbor_id in self._execution_metrics.node_execution_times:
                avg_time = self._execution_metrics.node_execution_times[neighbor_id]
                score -= avg_time * 100  # Prefer faster nodes

            scored_neighbors.append((score, neighbor_id))

        # Return highest scoring neighbor
        scored_neighbors.sort(reverse=True)
        return scored_neighbors[0][1]

    def _should_use_cache(self, node_name: str) -> bool:
        """Determine if node results should be cached"""

        # Don't cache router decisions (context-dependent)
        if 'router' in node_name.lower():
            return False

        # Don't cache nodes with side effects
        if 'finalize' in node_name.lower():
            return False

        # Cache deterministic analysis nodes
        if any(term in node_name.lower() for term in ['summary', 'branch', 'anomaly']):
            return True

        return False

    def run(self, state: GraphState, max_steps: int = 50) -> GraphState:
        """Enhanced run with comprehensive monitoring"""
        run_start = time.time()
        current = self.entrypoint
        steps = 0
        s = state

        logger.info({
            "event": "enhanced_graph_run_start",
            "entrypoint": current,
            "max_steps": max_steps
        })

        while current and steps < max_steps:
            s, current = self.step(s, current)
            steps += 1

            # Safety check for infinite loops
            if steps > max_steps * 0.8:
                logger.warning(f"High step count: {steps}/{max_steps}")

        # Record final metrics
        total_time = time.time() - run_start
        self._execution_metrics.execution_time = total_time
        self._execution_metrics.graph_traversal_count += 1

        # Calculate cache hit rate
        total_cache_operations = len(self._node_execution_cache)
        if total_cache_operations > 0:
            self._execution_metrics.cache_hit_rate = (
                self._execution_metrics.cache_hit_rate / total_cache_operations
            )

        logger.info({
            "event": "enhanced_graph_run_complete",
            "steps": steps,
            "execution_time": total_time,
            "avg_step_time": total_time / max(1, steps),
            "cache_hit_rate": self._execution_metrics.cache_hit_rate
        })

        return s

    def _auto_optimize(self):
        """Automatically optimize graph performance"""
        logger.info("Performing automatic graph optimization")

        # Optimize backend layout
        self._optimized_graph.optimize_layout()

        # Clean old cache entries to prevent memory leaks
        cache_size_limit = 1000
        if len(self._node_execution_cache) > cache_size_limit:
            # Keep most recent entries (simple LRU simulation)
            items = list(self._node_execution_cache.items())
            self._node_execution_cache = dict(items[-cache_size_limit//2:])

        self._last_optimization = time.time()

    def analyze_graph_properties(self) -> Dict[str, Any]:
        """Comprehensive graph analysis using optimized algorithms"""

        analysis = {}

        try:
            # Basic properties
            analysis['node_count'] = len(self.nodes)
            analysis['edge_count'] = len(self.edges)
            analysis['density'] = len(self.edges) / (len(self.nodes) * (len(self.nodes) - 1))

            # Topological analysis
            try:
                topo_order = self._optimized_graph.topological_sort()
                analysis['is_dag'] = True
                analysis['topological_complexity'] = len(topo_order)
            except ValueError:
                analysis['is_dag'] = False
                analysis['topological_complexity'] = None

            # Connectivity analysis
            analysis['reachability_matrix'] = {}
            for node_id in self.nodes:
                reachable = self._optimized_graph.get_reachable_nodes(node_id)
                analysis['reachability_matrix'][node_id] = len(reachable)

            # Strongly connected components
            sccs = self._optimized_graph.find_strongly_connected_components()
            analysis['strongly_connected_components'] = len(sccs)
            analysis['largest_scc_size'] = max(len(scc) for scc in sccs) if sccs else 0

            # Path analysis
            if self.entrypoint in self.nodes:
                reachable_from_entry = self._optimized_graph.get_reachable_nodes(self.entrypoint)
                analysis['reachable_from_entrypoint'] = len(reachable_from_entry)
                analysis['coverage_ratio'] = len(reachable_from_entry) / len(self.nodes)

            # Performance metrics
            analysis['optimization_stats'] = self._optimized_graph.get_statistics()
            analysis['execution_metrics'] = {
                'total_steps': self._execution_metrics.total_steps,
                'total_execution_time': self._execution_metrics.execution_time,
                'cache_hit_rate': self._execution_metrics.cache_hit_rate,
                'traversal_count': self._execution_metrics.graph_traversal_count,
                'avg_node_execution_times': dict(self._execution_metrics.node_execution_times)
            }

        except Exception as e:
            logger.error(f"Error in graph analysis: {e}")
            analysis['error'] = str(e)

        return analysis

    def find_optimal_path(self, source: str, target: str) -> Optional[List[str]]:
        """Find optimal path between nodes using advanced algorithms"""
        return self._optimized_graph.find_shortest_path(source, target)

    def get_critical_path(self) -> List[str]:
        """Find critical path (longest path from entry to any exit node)"""

        if self.entrypoint not in self.nodes:
            return []

        # Find all nodes with no outgoing edges (potential exit nodes)
        exit_nodes = []
        for node_id in self.nodes:
            if not self._optimized_graph.get_neighbors(node_id):
                exit_nodes.append(node_id)

        # Find longest path to any exit node
        longest_path = []
        for exit_node in exit_nodes:
            path = self._optimized_graph.find_shortest_path(self.entrypoint, exit_node)
            if path and len(path) > len(longest_path):
                longest_path = path

        return longest_path

    def export_performance_report(self) -> Dict[str, Any]:
        """Export comprehensive performance report"""

        return {
            'timestamp': time.time(),
            'uptime': time.time() - self._start_time,
            'graph_analysis': self.analyze_graph_properties(),
            'performance_summary': {
                'avg_execution_time': (
                    self._execution_metrics.execution_time /
                    max(1, self._execution_metrics.graph_traversal_count)
                ),
                'total_optimizations': self._optimized_graph.get_statistics()['rebuilds'],
                'cache_efficiency': self._execution_metrics.cache_hit_rate,
                'memory_footprint_estimate': len(self._node_execution_cache) * 100  # rough estimate
            },
            'recommendations': self._generate_performance_recommendations()
        }

    def _generate_performance_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations"""

        recommendations = []
        stats = self._optimized_graph.get_statistics()

        # Cache performance recommendations
        if stats['cache_hit_rate'] < 0.5:
            recommendations.append("Consider increasing cache size or reviewing cache strategies")

        # Graph structure recommendations
        if len(self.nodes) > 50:
            recommendations.append("Large graph detected - consider graph partitioning")

        # Execution time recommendations
        slow_nodes = [
            node for node, time in self._execution_metrics.node_execution_times.items()
            if time > 1.0
        ]
        if slow_nodes:
            recommendations.append(f"Optimize slow nodes: {', '.join(slow_nodes)}")

        # Memory recommendations
        if len(self._node_execution_cache) > 5000:
            recommendations.append("Consider more aggressive cache cleanup policies")

        return recommendations

    def visualize_execution_flow(self) -> str:
        """Generate DOT visualization with execution metrics overlay"""

        lines = ['digraph ExecutionFlow {']
        lines.append('  rankdir=TB;')
        lines.append('  node [shape=box, style=filled];')

        # Add nodes with execution time colors
        max_time = max(self._execution_metrics.node_execution_times.values()) if self._execution_metrics.node_execution_times else 1.0

        for node_id in self.nodes:
            exec_time = self._execution_metrics.node_execution_times.get(node_id, 0)

            # Color based on execution time (green=fast, red=slow)
            if max_time > 0:
                intensity = min(1.0, exec_time / max_time)
                color = f"#{int(255 * intensity):02x}{int(255 * (1-intensity)):02x}00"
            else:
                color = "#00ff00"

            label = f"{node_id}\\n{exec_time:.3f}s"
            lines.append(f'  "{node_id}" [label="{label}", fillcolor="{color}"];')

        # Add edges
        for src, dst in self.edges:
            lines.append(f'  "{src}" -> "{dst}";')

        lines.append('}')
        return '\n'.join(lines)