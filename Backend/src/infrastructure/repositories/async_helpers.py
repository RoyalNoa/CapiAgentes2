"""
Async Helpers - Utilities for handling async repository calls
Provides sync wrappers and helpers for async repository methods
"""

import asyncio
import functools
from typing import Any, Callable, TypeVar, Coroutine
from concurrent.futures import ThreadPoolExecutor

T = TypeVar('T')


def async_to_sync(async_func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """
    Decorator to convert async function to sync
    Handles event loop properly to avoid conflicts
    
    Args:
        async_func: Async function to wrap
        
    Returns:
        Sync version of the function
    """
    @functools.wraps(async_func)
    def wrapper(*args, **kwargs) -> T:
        try:
            # Try to get current event loop
            loop = asyncio.get_running_loop()
            # If we're in an event loop, use thread executor
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, async_func(*args, **kwargs))
                return future.result()
        except RuntimeError:
            # No event loop running, create one
            return asyncio.run(async_func(*args, **kwargs))
    
    return wrapper


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run an async coroutine from sync context
    Handles nested event loops properly
    
    Args:
        coro: Coroutine to run
        
    Returns:
        Result of the coroutine
    """
    try:
        # Check if there's already an event loop
        loop = asyncio.get_running_loop()
        # Use thread to avoid conflict
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No loop running, safe to create one
        return asyncio.run(coro)


class AsyncRepositoryWrapper:
    """
    Wrapper to provide sync access to async repository methods
    Useful for gradual migration and compatibility
    """
    
    def __init__(self, async_repo):
        """
        Initialize wrapper with async repository
        
        Args:
            async_repo: Async repository instance
        """
        self._async_repo = async_repo
        self._wrap_methods()
    
    def _wrap_methods(self):
        """Wrap all async methods to provide sync versions"""
        for attr_name in dir(self._async_repo):
            if not attr_name.startswith('_'):
                attr = getattr(self._async_repo, attr_name)
                if asyncio.iscoroutinefunction(attr):
                    # Create sync wrapper
                    sync_method = async_to_sync(attr)
                    # Add as sync_ prefixed method
                    setattr(self, f"sync_{attr_name}", sync_method)
                    # Also override original name for transparency
                    setattr(self, attr_name, sync_method)
    
    def __getattr__(self, name):
        """Fallback to async repo for non-wrapped attributes"""
        return getattr(self._async_repo, name)


def ensure_async_context(func: Callable) -> Callable:
    """
    Decorator to ensure function runs in async context
    Creates event loop if needed
    
    Args:
        func: Function that needs async context
        
    Returns:
        Wrapped function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            return run_async(func(*args, **kwargs))
        else:
            return func(*args, **kwargs)
    
    return wrapper


class RepositoryAsyncAdapter:
    """
    Adapter to make async repositories work in sync contexts
    Provides both async and sync interfaces
    """
    
    def __init__(self, repository):
        """
        Initialize adapter
        
        Args:
            repository: Repository instance (async or sync)
        """
        self._repository = repository
        self._is_async = any(
            asyncio.iscoroutinefunction(getattr(repository, attr))
            for attr in dir(repository)
            if not attr.startswith('_')
        )
    
    def _call_method(self, method_name: str, *args, **kwargs):
        """
        Call repository method handling async/sync
        
        Args:
            method_name: Name of method to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Method result
        """
        method = getattr(self._repository, method_name)
        
        if asyncio.iscoroutinefunction(method):
            return run_async(method(*args, **kwargs))
        else:
            return method(*args, **kwargs)
    
    def save(self, *args, **kwargs):
        """Save with async handling"""
        return self._call_method('save', *args, **kwargs)
    
    def find_all(self, *args, **kwargs):
        """Find all with async handling"""
        return self._call_method('find_all', *args, **kwargs)
    
    def find_by_id(self, *args, **kwargs):
        """Find by ID with async handling"""
        return self._call_method('find_by_id', *args, **kwargs)
    
    def count(self, *args, **kwargs):
        """Count with async handling"""
        return self._call_method('count', *args, **kwargs)
    
    def delete_all(self, *args, **kwargs):
        """Delete all with async handling"""
        return self._call_method('delete_all', *args, **kwargs)
    
    def __getattr__(self, name):
        """Fallback for other methods"""
        def method_wrapper(*args, **kwargs):
            return self._call_method(name, *args, **kwargs)
        return method_wrapper


# Helper functions for common operations
def sync_save(repo, record):
    """Sync wrapper for repository save"""
    if asyncio.iscoroutinefunction(repo.save):
        return run_async(repo.save(record))
    return repo.save(record)


def sync_find_all(repo):
    """Sync wrapper for repository find_all"""
    if asyncio.iscoroutinefunction(repo.find_all):
        return run_async(repo.find_all())
    return repo.find_all()


def sync_count(repo):
    """Sync wrapper for repository count"""
    if asyncio.iscoroutinefunction(repo.count):
        return run_async(repo.count())
    return repo.count()


# Export main utilities
__all__ = [
    'async_to_sync',
    'run_async',
    'AsyncRepositoryWrapper',
    'ensure_async_context',
    'RepositoryAsyncAdapter',
    'sync_save',
    'sync_find_all',
    'sync_count'
]