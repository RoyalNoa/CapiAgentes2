from typing import Any, Dict, Optional
from fastapi import HTTPException, status

class CapiException(Exception):
    """Base exception for CAPI application"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class ConfigurationError(CapiException):
    """Configuration related errors"""
    pass

class ValidationError(CapiException):
    """Data validation errors"""
    pass

class AuthenticationError(CapiException):
    """Authentication related errors"""
    pass

class AuthorizationError(CapiException):
    """Authorization related errors"""
    pass

class ExternalAPIError(CapiException):
    """External API related errors"""
    pass

class DatabaseError(CapiException):
    """Database related errors"""
    pass

class FileOperationError(CapiException):
    """File operation related errors"""
    pass

class RateLimitError(CapiException):
    """Rate limiting errors"""
    pass

class WorkspaceError(CapiException):
    """Workspace operation errors"""
    pass

class OrchestratorError(CapiException):
    """Orchestrator operation errors"""
    pass

class AgentError(CapiException):
    """Agent operation errors"""
    pass

# HTTP Exceptions for FastAPI
class HTTPValidationError(HTTPException):
    """HTTP validation error with structured details"""
    
    def __init__(self, detail: str, errors: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": detail, "errors": errors or {}}
        )

class HTTPAuthenticationError(HTTPException):
    """HTTP authentication error"""
    
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": detail, "type": "authentication_error"},
            headers={"WWW-Authenticate": "Bearer"}
        )

class HTTPAuthorizationError(HTTPException):
    """HTTP authorization error"""
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": detail, "type": "authorization_error"}
        )

class HTTPNotFoundError(HTTPException):
    """HTTP not found error"""
    
    def __init__(self, resource: str, identifier: str = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": message, "type": "not_found_error", "resource": resource}
        )

class HTTPConflictError(HTTPException):
    """HTTP conflict error"""
    
    def __init__(self, detail: str, resource: str = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": detail, "type": "conflict_error", "resource": resource}
        )

class HTTPRateLimitError(HTTPException):
    """HTTP rate limit error"""
    
    def __init__(self, detail: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"message": detail, "type": "rate_limit_error"},
            headers={"Retry-After": str(retry_after)}
        )

class HTTPInternalServerError(HTTPException):
    """HTTP internal server error"""
    
    def __init__(self, detail: str = "Internal server error", error_id: str = None):
        error_detail = {"message": detail, "type": "internal_server_error"}
        if error_id:
            error_detail["error_id"] = error_id
        
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )

class HTTPServiceUnavailableError(HTTPException):
    """HTTP service unavailable error"""
    
    def __init__(self, detail: str = "Service temporarily unavailable", retry_after: int = 300):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": detail, "type": "service_unavailable_error"},
            headers={"Retry-After": str(retry_after)}
        )

# Exception mapping for consistent error responses
EXCEPTION_MAP = {
    ValidationError: HTTPValidationError,
    AuthenticationError: HTTPAuthenticationError,
    AuthorizationError: HTTPAuthorizationError,
    RateLimitError: HTTPRateLimitError,
    ExternalAPIError: HTTPServiceUnavailableError,
    DatabaseError: HTTPInternalServerError,
    FileOperationError: HTTPInternalServerError,
    WorkspaceError: HTTPInternalServerError,
    OrchestratorError: HTTPInternalServerError,
}

def map_exception_to_http(exc: CapiException) -> HTTPException:
    """Map application exception to HTTP exception"""
    exception_class = EXCEPTION_MAP.get(type(exc), HTTPInternalServerError)
    
    if exception_class == HTTPValidationError:
        return exception_class(exc.message, exc.details)
    elif exception_class in [HTTPAuthenticationError, HTTPAuthorizationError]:
        return exception_class(exc.message)
    elif exception_class == HTTPRateLimitError:
        retry_after = exc.details.get('retry_after', 60)
        return exception_class(exc.message, retry_after)
    elif exception_class == HTTPServiceUnavailableError:
        retry_after = exc.details.get('retry_after', 300)
        return exception_class(exc.message, retry_after)
    else:
        error_id = exc.details.get('error_id')
        return exception_class(exc.message, error_id)