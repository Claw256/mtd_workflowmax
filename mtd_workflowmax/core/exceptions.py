"""Custom exceptions for WorkflowMax API."""

import functools
from typing import Callable, Any, Optional, Union
import xml.etree.ElementTree as ET
from requests import Response

class WorkflowMaxError(Exception):
    """Base exception for WorkflowMax API errors."""
    
    def __init__(self, message: str, error_code: str = None, errors: list = None):
        """Initialize exception.
        
        Args:
            message: Error message
            error_code: Optional error code from API
            errors: Optional list of specific error messages
        """
        super().__init__(message)
        self.error_code = error_code
        self.errors = errors or []

class AuthenticationError(WorkflowMaxError):
    """Raised when authentication fails."""
    pass

class TokenExpiredError(AuthenticationError):
    """Raised when the access token has expired."""
    pass

class TokenRefreshError(AuthenticationError):
    """Raised when token refresh fails."""
    pass

class ResourceNotFoundError(WorkflowMaxError):
    """Raised when a resource is not found."""
    
    def __init__(self, resource_type: str, identifier: str):
        """Initialize exception.
        
        Args:
            resource_type: Type of resource (e.g., 'Contact', 'Job')
            identifier: Resource identifier (e.g., UUID)
        """
        super().__init__(f"{resource_type} not found: {identifier}")
        self.resource_type = resource_type
        self.identifier = identifier

class ValidationError(WorkflowMaxError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, errors: list = None):
        """Initialize exception.
        
        Args:
            message: Error message
            errors: Optional list of specific validation errors
        """
        super().__init__(message, errors=errors)

class XMLParsingError(WorkflowMaxError):
    """Raised when XML parsing fails."""
    
    def __init__(self, message: str, xml_element = None):
        """Initialize exception.
        
        Args:
            message: Error message
            xml_element: Optional XML element that failed to parse
        """
        super().__init__(message)
        self.xml_element = xml_element

class ContactNotFoundError(ResourceNotFoundError):
    """Raised when a contact is not found."""
    
    def __init__(self, uuid: str):
        """Initialize exception.
        
        Args:
            uuid: Contact UUID
        """
        super().__init__('Contact', uuid)

class CustomFieldError(WorkflowMaxError):
    """Raised when there's an error with custom fields."""
    pass

class RateLimitError(WorkflowMaxError):
    """Raised when API rate limit is exceeded."""
    
    def __init__(self, retry_after: int = None):
        """Initialize exception.
        
        Args:
            retry_after: Optional number of seconds to wait before retrying
        """
        super().__init__("API rate limit exceeded")
        self.retry_after = retry_after

class ConfigurationError(WorkflowMaxError):
    """Raised when there's a configuration error."""
    pass

def validate_response(expected_status: Optional[str] = 'OK') -> Callable:
    """Decorator to validate API response.
    
    Args:
        expected_status: Expected status text (default: 'OK')
        
    Returns:
        Decorator function
        
    Usage:
        @validate_response()  # With default status
        def my_func():
            pass
            
        @validate_response('Created')  # With custom status
        def my_func():
            pass
    """
    def decorator(func: Callable[..., Response]) -> Callable[..., Response]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Response:
            response = func(*args, **kwargs)
            try:
                xml_root = ET.fromstring(response.text.encode('utf-8'))
                status = xml_root.find('Status')
                if status is not None:
                    if expected_status and status.text != expected_status:
                        raise WorkflowMaxError(f"API error: {status.text}")
            except ET.ParseError as e:
                raise XMLParsingError(f"Failed to parse response XML: {str(e)}")
            return response
        return wrapper
        
    # Handle both @validate_response and @validate_response()
    if callable(expected_status):
        # @validate_response
        func, expected_status = expected_status, 'OK'
        return decorator(func)
    # @validate_response()
    return decorator

def handle_api_errors(func: Optional[Callable] = None) -> Callable:
    """Decorator to handle API errors.
    
    Args:
        func: Optional function to decorate
        
    Returns:
        Decorator function
        
    Usage:
        @handle_api_errors  # Without parentheses
        def my_func():
            pass
            
        @handle_api_errors()  # With parentheses
        def my_func():
            pass
    """
    def decorator(func: Callable[..., Response]) -> Callable[..., Response]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Response:
            try:
                response = func(*args, **kwargs)
                
                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 0))
                    raise RateLimitError(retry_after)
                
                # Check for authentication errors
                if response.status_code == 401:
                    raise TokenExpiredError("Access token expired")
                if response.status_code == 403:
                    raise AuthenticationError("Authentication failed")
                
                # Check for not found errors
                if response.status_code == 404:
                    raise ResourceNotFoundError("Resource", "not found")
                
                # Check for other errors
                if response.status_code >= 400:
                    # Try to parse error from XML response
                    try:
                        xml_root = ET.fromstring(response.text.encode('utf-8'))
                        status = xml_root.find('Status')
                        if status is not None and status.text != 'OK':
                            raise WorkflowMaxError(f"API error: {status.text}")
                    except ET.ParseError:
                        pass
                    
                    # Fallback error message
                    raise WorkflowMaxError(
                        f"API request failed with status {response.status_code}"
                    )
                
                return response
                
            except WorkflowMaxError:
                raise
            except Exception as e:
                raise WorkflowMaxError(f"API request failed: {str(e)}")
        return wrapper
    
    # Handle both @handle_api_errors and @handle_api_errors()
    if func is None:
        # @handle_api_errors()
        return decorator
    # @handle_api_errors
    return decorator(func)
