import time
import uuid
from typing import Dict, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import RequestResponseEndpoint

from src.core.config import settings
from src.core.logging import get_logger, log_request, log_error
from src.core.exceptions import HTTPRateLimitError, HTTPAuthenticationError

logger = get_logger(__name__)

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response

class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all HTTP requests and responses"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        request_id = getattr(request.state, 'request_id', None)
        
        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "request_method": request.method,
                "request_path": str(request.url.path),
                "request_query": str(request.url.query),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "event_type": "request_started"
            }
        )
        
        try:
            response = await call_next(request)
            response_time = time.time() - start_time
            
            # Log successful response
            log_request(
                logger, 
                request.method, 
                str(request.url.path), 
                response.status_code, 
                response_time,
                request_id
            )
            
            return response
            
        except Exception as exc:
            response_time = time.time() - start_time
            
            # Log error
            log_error(
                logger, 
                exc, 
                {
                    "request_id": request_id,
                    "request_method": request.method,
                    "request_path": str(request.url.path),
                    "response_time_ms": round(response_time * 1000, 2)
                }
            )
            raise

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # CSP header for production
        if settings.is_production:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self'"
            )
        
        return response

class RateLimitStore:
    """In-memory rate limit store with sliding window"""
    
    def __init__(self):
        self._store: Dict[str, deque] = defaultdict(deque)
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = datetime.now()
    
    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """Check if request is allowed and return remaining requests"""
        now = datetime.now()
        
        # Cleanup old entries periodically
        if (now - self._last_cleanup).seconds > self._cleanup_interval:
            self._cleanup_old_entries(now, window)
            self._last_cleanup = now
        
        # Get or create bucket
        bucket = self._store[key]
        
        # Remove expired entries
        cutoff = now - timedelta(seconds=window)
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        
        # Check limit
        if len(bucket) >= limit:
            return False, 0
        
        # Add current request
        bucket.append(now)
        remaining = limit - len(bucket)
        
        return True, remaining
    
    def _cleanup_old_entries(self, now: datetime, window: int):
        """Clean up old entries to prevent memory leak"""
        cutoff = now - timedelta(seconds=window * 2)  # Double window for safety
        
        for key in list(self._store.keys()):
            bucket = self._store[key]
            
            # Remove expired entries
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            
            # Remove empty buckets
            if not bucket:
                del self._store[key]

# Global rate limit store
rate_limit_store = RateLimitStore()

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with sliding window"""
    
    def __init__(self, app, enabled: bool = True, requests: int = 100, window: int = 60):
        super().__init__(app)
        self.enabled = enabled
        self.requests = requests
        self.window = window
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self.enabled:
            return await call_next(request)
        
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
        
        # Create rate limit key (IP + endpoint)
        client_ip = request.client.host if request.client else "unknown"
        endpoint = f"{request.method}:{request.url.path}"
        rate_limit_key = f"{client_ip}:{endpoint}"
        
        # Check rate limit
        allowed, remaining = rate_limit_store.is_allowed(
            rate_limit_key, 
            self.requests, 
            self.window
        )
        
        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {client_ip} on {endpoint}",
                extra={
                    "client_ip": client_ip,
                    "endpoint": endpoint,
                    "event_type": "rate_limit_exceeded"
                }
            )
            raise HTTPRateLimitError("Rate limit exceeded", self.window)
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(self.window)
        
        return response

class APIKeyMiddleware(BaseHTTPMiddleware):
    """API key authentication middleware"""
    
    def __init__(self, app, required_paths: Optional[list] = None):
        super().__init__(app)
        self.required_paths = required_paths or ["/api/"]
        self.excluded_paths = ["/health", "/metrics", "/docs", "/openapi.json", "/redoc"]
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        
        # Skip authentication for excluded paths
        if any(path.startswith(excluded) for excluded in self.excluded_paths):
            return await call_next(request)
        
        # Check if path requires authentication
        requires_auth = any(path.startswith(required) for required in self.required_paths)
        
        if requires_auth:
            # Check API key in header
            api_key = request.headers.get("X-API-Key")
            
            if not api_key:
                # Check in query parameter as fallback
                api_key = request.query_params.get("api_key")
            
            if not api_key or api_key != settings.API_KEY_BACKEND:
                logger.warning(
                    f"Invalid API key attempt from {request.client.host if request.client else 'unknown'}",
                    extra={
                        "client_ip": request.client.host if request.client else "unknown",
                        "path": path,
                        "event_type": "authentication_failed"
                    }
                )
                raise HTTPAuthenticationError("Invalid API key")
        
        return await call_next(request)

def setup_middleware(app):
    """Setup all middleware for the application"""
    
    # Security middleware
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS
        )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Custom middleware (order matters - last added is executed first)
    app.add_middleware(SecurityHeadersMiddleware)
    
    if settings.RATE_LIMIT_ENABLED:
        app.add_middleware(
            RateLimitMiddleware,
            enabled=settings.RATE_LIMIT_ENABLED,
            requests=settings.RATE_LIMIT_REQUESTS,
            window=settings.RATE_LIMIT_WINDOW
        )
    
    app.add_middleware(APIKeyMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)