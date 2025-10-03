"""
Advanced Query Optimizer for Graph Traversal
============================================

Implements intelligent query optimization techniques for graph operations:
- Query plan optimization using cost-based models
- Adaptive caching with LRU and frequency-based eviction
- Parallel execution for independent subgraphs
- Query rewriting for common patterns
- Statistical cost estimation
"""

from __future__ import annotations
import logging
from typing import Dict, List, Tuple, Set, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from collections import defaultdict, OrderedDict
from enum import Enum
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import heapq
from functools import wraps

from src.core.logging import get_logger

logger = get_logger(__name__)


class QueryType(Enum):
    """Types of graph queries for optimization"""
    SHORTEST_PATH = "shortest_path"
    REACHABILITY = "reachability"
    TOPOLOGICAL_SORT = "topological_sort"
    SCC_DETECTION = "scc_detection"
    GRAPH_TRAVERSAL = "graph_traversal"
    PATTERN_MATCHING = "pattern_matching"


@dataclass
class QueryPlan:
    """Optimized execution plan for graph queries"""
    query_type: QueryType
    estimated_cost: float
    execution_order: List[str]
    parallelizable_operations: List[List[str]]
    cache_strategy: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheEntry:
    """Cache entry with metadata for intelligent eviction"""
    key: str
    value: Any
    access_count: int = 0
    last_access: float = 0.0
    creation_time: float = 0.0
    compute_cost: float = 0.0
    size_estimate: int = 0

    def __post_init__(self):
        if self.creation_time == 0.0:
            self.creation_time = time.time()
        if self.last_access == 0.0:
            self.last_access = time.time()


class AdaptiveCache:
    """Advanced caching with multiple eviction strategies"""

    def __init__(self, max_size: int = 10000, max_memory_mb: float = 100.0):
        self.max_size = max_size
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)

        self._cache: Dict[str, CacheEntry] = {}
        self._access_order = OrderedDict()  # For LRU
        self._frequency_heap = []  # For LFU
        self._current_memory = 0
        self._lock = threading.RLock()

        # Statistics
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'memory_evictions': 0
        }

    def get(self, key: str) -> Optional[Any]:
        """Get value with intelligent access tracking"""
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None

            entry = self._cache[key]
            entry.access_count += 1
            entry.last_access = time.time()

            # Update access order for LRU
            self._access_order.move_to_end(key)

            self._stats['hits'] += 1
            return entry.value

    def put(self, key: str, value: Any, compute_cost: float = 1.0, size_estimate: int = None):
        """Put value with intelligent eviction"""
        with self._lock:
            if size_estimate is None:
                size_estimate = self._estimate_size(value)

            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                compute_cost=compute_cost,
                size_estimate=size_estimate
            )

            # Check if we need to evict
            while (len(self._cache) >= self.max_size or
                   self._current_memory + size_estimate > self.max_memory_bytes):
                if not self._evict_entry():
                    break  # Cannot evict more

            # Add entry
            self._cache[key] = entry
            self._access_order[key] = True
            self._current_memory += size_estimate

    def _evict_entry(self) -> bool:
        """Intelligent cache eviction using hybrid strategy"""
        if not self._cache:
            return False

        # Choose eviction strategy based on cache state
        eviction_candidate = self._choose_eviction_candidate()

        if eviction_candidate:
            self._remove_entry(eviction_candidate)
            self._stats['evictions'] += 1
            return True

        return False

    def _choose_eviction_candidate(self) -> Optional[str]:
        """Choose best candidate for eviction using multiple criteria"""
        if not self._cache:
            return None

        # Calculate scores for all entries
        candidates = []
        current_time = time.time()

        for key, entry in self._cache.items():
            # Scoring factors
            recency_score = 1.0 / max(1.0, current_time - entry.last_access)
            frequency_score = entry.access_count
            cost_score = entry.compute_cost
            size_penalty = entry.size_estimate / 1000.0  # Size penalty

            # Combined score (lower is better for eviction)
            score = (recency_score * 0.3 +
                    frequency_score * 0.3 +
                    cost_score * 0.2 -
                    size_penalty * 0.2)

            candidates.append((score, key))

        # Return candidate with lowest score
        candidates.sort()
        return candidates[0][1] if candidates else None

    def _remove_entry(self, key: str):
        """Remove entry and update tracking structures"""
        if key in self._cache:
            entry = self._cache[key]
            self._current_memory -= entry.size_estimate
            del self._cache[key]

        if key in self._access_order:
            del self._access_order[key]

    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of cached value"""
        try:
            import sys
            return sys.getsizeof(value)
        except:
            # Fallback estimation
            if isinstance(value, str):
                return len(value) * 2
            elif isinstance(value, list):
                return len(value) * 50
            elif isinstance(value, dict):
                return len(value) * 100
            else:
                return 100

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            hit_rate = self._stats['hits'] / max(1, self._stats['hits'] + self._stats['misses'])

            return {
                **self._stats,
                'hit_rate': hit_rate,
                'size': len(self._cache),
                'memory_usage_mb': self._current_memory / (1024 * 1024),
                'memory_usage_percent': self._current_memory / self.max_memory_bytes * 100
            }

    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._current_memory = 0


class QueryOptimizer:
    """Advanced query optimizer for graph operations"""

    def __init__(self, cache_size: int = 10000, enable_parallelism: bool = True):
        self.cache = AdaptiveCache(max_size=cache_size)
        self.enable_parallelism = enable_parallelism
        self._executor = ThreadPoolExecutor(max_workers=4) if enable_parallelism else None

        # Query statistics for cost estimation
        self._query_stats: Dict[QueryType, Dict[str, float]] = defaultdict(lambda: {
            'avg_time': 0.0,
            'count': 0,
            'total_time': 0.0
        })

        # Pattern recognition for query rewriting
        self._common_patterns: Dict[str, Callable] = {}

        logger.info(f"QueryOptimizer initialized with parallelism={'enabled' if enable_parallelism else 'disabled'}")

    def optimize_query(self, query_type: QueryType,
                      graph: Any,
                      **query_params) -> QueryPlan:
        """Create optimized execution plan for query"""

        # Estimate query cost
        estimated_cost = self._estimate_query_cost(query_type, graph, **query_params)

        # Determine execution order
        execution_order = self._plan_execution_order(query_type, **query_params)

        # Identify parallelizable operations
        parallel_ops = self._identify_parallel_operations(query_type, execution_order)

        # Choose cache strategy
        cache_strategy = self._choose_cache_strategy(query_type, estimated_cost)

        return QueryPlan(
            query_type=query_type,
            estimated_cost=estimated_cost,
            execution_order=execution_order,
            parallelizable_operations=parallel_ops,
            cache_strategy=cache_strategy,
            metadata={
                'optimization_time': time.time(),
                'graph_size': getattr(graph, '__len__', lambda: 0)(),
                'parallelism_enabled': self.enable_parallelism
            }
        )

    def execute_optimized_query(self, plan: QueryPlan,
                               query_func: Callable,
                               *args, **kwargs) -> Any:
        """Execute query using optimized plan"""

        query_key = self._generate_cache_key(plan.query_type, args, kwargs)

        # Check cache first
        if plan.cache_strategy != 'no_cache':
            cached_result = self.cache.get(query_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for query type {plan.query_type}")
                return cached_result

        # Execute query with timing
        start_time = time.time()

        try:
            if plan.parallelizable_operations and self.enable_parallelism:
                result = self._execute_parallel(plan, query_func, *args, **kwargs)
            else:
                result = self._execute_sequential(plan, query_func, *args, **kwargs)

            execution_time = time.time() - start_time

            # Update statistics
            self._update_query_stats(plan.query_type, execution_time)

            # Cache result
            if plan.cache_strategy != 'no_cache':
                compute_cost = execution_time
                self.cache.put(query_key, result, compute_cost=compute_cost)

            logger.debug(f"Query {plan.query_type} completed in {execution_time:.3f}s")
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self._update_query_stats(plan.query_type, execution_time)
            logger.error(f"Query {plan.query_type} failed after {execution_time:.3f}s: {e}")
            raise

    def _execute_parallel(self, plan: QueryPlan, query_func: Callable, *args, **kwargs) -> Any:
        """Execute query with parallel operations"""

        if not plan.parallelizable_operations:
            return self._execute_sequential(plan, query_func, *args, **kwargs)

        # Submit parallel tasks
        futures = []
        for operation_group in plan.parallelizable_operations:
            future = self._executor.submit(
                self._execute_operation_group,
                operation_group, query_func, *args, **kwargs
            )
            futures.append(future)

        # Collect results
        results = []
        for future in as_completed(futures):
            try:
                result = future.result(timeout=30)  # 30 second timeout
                results.append(result)
            except Exception as e:
                logger.error(f"Parallel operation failed: {e}")
                # Continue with other operations

        # Merge results (query-specific logic)
        return self._merge_parallel_results(plan.query_type, results)

    def _execute_sequential(self, plan: QueryPlan, query_func: Callable, *args, **kwargs) -> Any:
        """Execute query sequentially"""
        return query_func(*args, **kwargs)

    def _execute_operation_group(self, operation_group: List[str],
                                query_func: Callable, *args, **kwargs) -> Any:
        """Execute a group of operations"""
        # This would contain query-specific parallel execution logic
        return query_func(*args, **kwargs)

    def _merge_parallel_results(self, query_type: QueryType, results: List[Any]) -> Any:
        """Merge results from parallel execution"""

        if not results:
            return None

        if query_type == QueryType.REACHABILITY:
            # Merge reachability sets
            merged = set()
            for result in results:
                if isinstance(result, set):
                    merged.update(result)
            return merged

        elif query_type == QueryType.SHORTEST_PATH:
            # Return shortest among all paths
            shortest = None
            for result in results:
                if isinstance(result, list):
                    if shortest is None or len(result) < len(shortest):
                        shortest = result
            return shortest

        else:
            # Default: return first non-None result
            return next((r for r in results if r is not None), None)

    def _estimate_query_cost(self, query_type: QueryType, graph: Any, **params) -> float:
        """Estimate query execution cost"""

        base_cost = 1.0
        graph_size = getattr(graph, '__len__', lambda: 100)()

        # Cost models for different query types
        if query_type == QueryType.SHORTEST_PATH:
            # BFS/Dijkstra complexity: O(V + E)
            estimated_edges = graph_size * 2  # Estimate
            base_cost = (graph_size + estimated_edges) * 0.001

        elif query_type == QueryType.REACHABILITY:
            # DFS complexity: O(V + E)
            base_cost = graph_size * 0.001

        elif query_type == QueryType.TOPOLOGICAL_SORT:
            # Kahn's algorithm: O(V + E)
            base_cost = graph_size * 0.002

        elif query_type == QueryType.SCC_DETECTION:
            # Tarjan's algorithm: O(V + E)
            base_cost = graph_size * 0.005

        elif query_type == QueryType.GRAPH_TRAVERSAL:
            # Full traversal: O(V + E)
            base_cost = graph_size * 0.001

        # Adjust based on historical data
        if query_type in self._query_stats:
            stats = self._query_stats[query_type]
            if stats['count'] > 0:
                historical_avg = stats['avg_time']
                base_cost = max(base_cost, historical_avg * 0.8)  # Conservative estimate

        return base_cost

    def _plan_execution_order(self, query_type: QueryType, **params) -> List[str]:
        """Plan optimal execution order for query operations"""

        # Basic execution orders for different query types
        execution_orders = {
            QueryType.SHORTEST_PATH: ['validate_inputs', 'check_cache', 'execute_bfs', 'cache_result'],
            QueryType.REACHABILITY: ['validate_inputs', 'check_cache', 'execute_dfs', 'cache_result'],
            QueryType.TOPOLOGICAL_SORT: ['validate_dag', 'calculate_degrees', 'execute_kahn', 'cache_result'],
            QueryType.SCC_DETECTION: ['validate_inputs', 'execute_tarjan', 'process_components', 'cache_result'],
            QueryType.GRAPH_TRAVERSAL: ['validate_inputs', 'select_algorithm', 'execute_traversal', 'process_results']
        }

        return execution_orders.get(query_type, ['execute_query'])

    def _identify_parallel_operations(self, query_type: QueryType,
                                     execution_order: List[str]) -> List[List[str]]:
        """Identify operations that can be executed in parallel"""

        if not self.enable_parallelism:
            return []

        # Define parallelizable operation groups
        parallel_patterns = {
            QueryType.REACHABILITY: [['execute_dfs']],  # Can parallel DFS from multiple starting points
            QueryType.SCC_DETECTION: [['execute_tarjan']],  # Can parallel on disconnected components
            QueryType.GRAPH_TRAVERSAL: [['execute_traversal']]  # Can parallel different subgraphs
        }

        return parallel_patterns.get(query_type, [])

    def _choose_cache_strategy(self, query_type: QueryType, estimated_cost: float) -> str:
        """Choose optimal caching strategy"""

        # High-cost queries benefit more from caching
        if estimated_cost > 1.0:
            return 'aggressive_cache'
        elif estimated_cost > 0.1:
            return 'standard_cache'
        else:
            return 'minimal_cache'

    def _generate_cache_key(self, query_type: QueryType, args: Tuple, kwargs: Dict) -> str:
        """Generate stable cache key for query"""

        key_parts = [query_type.value]

        # Add argument hashes
        for arg in args:
            if hasattr(arg, '__hash__'):
                try:
                    key_parts.append(str(hash(arg)))
                except:
                    key_parts.append(str(arg)[:50])  # Truncate long strings
            else:
                key_parts.append(str(arg)[:50])

        # Add keyword argument hashes
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={hash(str(v))}")

        return '|'.join(key_parts)

    def _update_query_stats(self, query_type: QueryType, execution_time: float):
        """Update query execution statistics"""

        stats = self._query_stats[query_type]
        stats['count'] += 1
        stats['total_time'] += execution_time
        stats['avg_time'] = stats['total_time'] / stats['count']

    def add_query_pattern(self, pattern_name: str, pattern_func: Callable):
        """Add custom query pattern for optimization"""
        self._common_patterns[pattern_name] = pattern_func
        logger.info(f"Added query pattern: {pattern_name}")

    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get comprehensive optimization statistics"""

        return {
            'cache_stats': self.cache.get_stats(),
            'query_stats': dict(self._query_stats),
            'parallelism_enabled': self.enable_parallelism,
            'registered_patterns': list(self._common_patterns.keys()),
            'total_optimized_queries': sum(stats['count'] for stats in self._query_stats.values())
        }

    def clear_cache(self):
        """Clear optimization cache"""
        self.cache.clear()
        logger.info("Query optimization cache cleared")

    def __del__(self):
        """Cleanup resources"""
        if self._executor:
            self._executor.shutdown(wait=False)


# Decorator for automatic query optimization
def optimize_graph_query(query_type: QueryType, cache_key_func: Optional[Callable] = None):
    """Decorator to automatically optimize graph queries"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # This would integrate with a global query optimizer instance
            # For now, just execute the function directly
            return func(*args, **kwargs)

        return wrapper
    return decorator