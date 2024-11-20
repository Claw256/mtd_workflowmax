"""Exception handling for WorkflowMax API client."""

import functools
import logging
from typing import Type, Callable, Any, Union, Tuple
from requests.exceptions import RequestException

logger = logging.getLogger('workflowmax.exceptions')

class WorkflowMaxAPIError(Exception):
    """Base exception for WorkflowMax API errors."""
    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class AuthenticationError(WorkflowMaxAPIError):
    """Raised when authentication fails."""
    pass

class TokenExpiredError(AuthenticationError):
    """Raised when the OAuth token has expired."""
    pass

class TokenRefreshError(AuthenticationError):
    """Raised when token refresh fails."""
    pass

class ConfigurationError(WorkflowMaxAPIError):
    """Raised when there's a configuration error."""
    pass

class RateLimitError(WorkflowMaxAPIError):
    """Raised when API rate limit is hit."""
    def __init__(self, message: str, reset_time: int = None):
        super().__init__(message)
        self.reset_time = reset_time

class ValidationError(WorkflowMaxAPIError):
    """Raised when request or response validation fails."""
    def __init__(self, message: str, errors: dict = None):
        super().__init__(message)
        self.errors = errors or {}

class ResourceNotFoundError(WorkflowMaxAPIError):
    """Raised when a requested resource is not found."""
    pass

class XMLParsingError(WorkflowMaxAPIError):
    """Raised when XML parsing fails."""
    pass

def handle_api_errors(
    retries: int = 3,
    retry_exceptions: Tuple[Type[Exception], ...] = (RateLimitError, RequestException),
    exclude_exceptions: Tuple[Type[Exception], ...] = (AuthenticationError, ValidationError)
) -> Callable:
    """Decorator for handling API errors with retries.
    
    Args:
        retries: Number of times to retry the operation
        retry_exceptions: Exceptions that should trigger a retry
        exclude_exceptions: Exceptions that should not be retried
        
    Returns:
        Callable: Decorated function
        
    Example:
        @handle_api_errors(retries=3)
        def make_api_call():
            # API call implementation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                    
                except exclude_exceptions as e:
                    # Don't retry these exceptions
                    logger.error(f"{func.__name__} failed with {type(e).__name__}: {str(e)}")
                    raise
                    
                except retry_exceptions as e:
                    last_exception = e
                    if attempt < retries - 1:  # Don't log on last attempt
                        logger.warning(
                            f"{func.__name__} failed with {type(e).__name__}, "
                            f"attempt {attempt + 1}/{retries}: {str(e)}"
                        )
                    continue
                    
                except Exception as e:
                    logger.error(
                        f"Unexpected error in {func.__name__}: {type(e).__name__}: {str(e)}",
                        exc_info=True
                    )
                    raise
            
            # If we get here, we've exhausted our retries
            logger.error(
                f"{func.__name__} failed after {retries} attempts. "
                f"Last error: {type(last_exception).__name__}: {str(last_exception)}"
            )
            raise last_exception
            
        return wrapper
    return decorator

def validate_response(func: Callable) -> Callable:
    """Decorator for validating API responses.
    
    Example:
        @validate_response
        def make_api_call():
            # API call implementation
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        response = func(*args, **kwargs)
        
        if not hasattr(response, 'status_code'):
            return response
            
        if response.status_code == 404:
            raise ResourceNotFoundError(f"Resource not found: {response.url}")
            
        if response.status_code == 401:
            raise AuthenticationError("Authentication failed")
            
        if response.status_code == 403:
            raise AuthenticationError("Access forbidden")
            
        if response.status_code == 429:
            reset_time = response.headers.get('X-RateLimit-Reset')
            raise RateLimitError(
                "Rate limit exceeded",
                reset_time=int(reset_time) if reset_time else None
            )
            
        if response.status_code >= 500:
            raise WorkflowMaxAPIError(
                f"Server error: {response.status_code}",
                status_code=response.status_code
            )
            
        if not response.ok:
            raise WorkflowMaxAPIError(
                f"API request failed: {response.status_code}",
                status_code=response.status_code
            )
            
        return response
        
    return wrapper
