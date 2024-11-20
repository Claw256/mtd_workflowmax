"""Utility functions and helpers for WorkflowMax API."""

import time
from typing import TypeVar, Callable, Any, Dict, Optional
from functools import wraps
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import hashlib
import json

from .logging import get_logger
from .exceptions import ValidationError

logger = get_logger('workflowmax.utils')

T = TypeVar('T')

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """Retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        raise
                        
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{max_attempts} for {func.__name__}",
                        error=str(e),
                        next_retry=current_delay
                    )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
                    
            raise last_exception  # Should never reach here
            
        return wrapper
    return decorator

def validate_xml(xml_string: str) -> ET.Element:
    """Validate and parse XML string.
    
    Args:
        xml_string: XML content to validate
        
    Returns:
        Parsed XML element
        
    Raises:
        ValidationError: If XML is invalid
    """
    try:
        return ET.fromstring(xml_string.encode('utf-8'))
    except ET.ParseError as e:
        raise ValidationError(f"Invalid XML: {str(e)}")

def format_datetime(dt: Optional[datetime] = None) -> str:
    """Format datetime in ISO 8601 format.
    
    Args:
        dt: Datetime to format. If None, uses current time.
        
    Returns:
        Formatted datetime string
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
        
    return dt.isoformat()

def generate_cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments.
    
    Args:
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key
        
    Returns:
        Cache key string
    """
    # Create a dictionary of all arguments
    key_dict = {
        'args': args,
        'kwargs': kwargs
    }
    
    # Convert to stable string representation
    key_str = json.dumps(key_dict, sort_keys=True)
    
    # Generate hash
    return hashlib.sha256(key_str.encode()).hexdigest()

class Singleton:
    """Base class for singleton pattern implementation."""
    
    _instances: Dict[type, Any] = {}
    
    def __new__(cls, *args, **kwargs):
        """Ensure only one instance exists."""
        if cls not in cls._instances:
            cls._instances[cls] = super().__new__(cls)
        return cls._instances[cls]

def validate_required(value: Any, name: str):
    """Validate required field is not None or empty.
    
    Args:
        value: Value to validate
        name: Field name for error message
        
    Raises:
        ValidationError: If validation fails
    """
    if value is None or (isinstance(value, (str, list, dict)) and not value):
        raise ValidationError(f"{name} is required")

def validate_string_length(value: str, name: str, min_length: int = 0, max_length: Optional[int] = None):
    """Validate string length is within bounds.
    
    Args:
        value: String to validate
        name: Field name for error message
        min_length: Minimum allowed length
        max_length: Maximum allowed length (optional)
        
    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be a string")
        
    if len(value) < min_length:
        raise ValidationError(f"{name} must be at least {min_length} characters")
        
    if max_length is not None and len(value) > max_length:
        raise ValidationError(f"{name} must be no more than {max_length} characters")

def validate_enum(value: Any, name: str, valid_values: tuple):
    """Validate value is one of allowed enum values.
    
    Args:
        value: Value to validate
        name: Field name for error message
        valid_values: Tuple of allowed values
        
    Raises:
        ValidationError: If validation fails
    """
    if value not in valid_values:
        raise ValidationError(
            f"Invalid {name}. Must be one of: {', '.join(str(v) for v in valid_values)}"
        )

def sanitize_xml(value: str) -> str:
    """Sanitize string for use in XML.
    
    Args:
        value: String to sanitize
        
    Returns:
        Sanitized string safe for XML
    """
    return value.replace('&', '&amp;') \
                .replace('<', '&lt;') \
                .replace('>', '&gt;') \
                .replace('"', '&quot;') \
                .replace("'", '&apos;')

def truncate_string(value: str, max_length: int, suffix: str = '...') -> str:
    """Truncate string to maximum length.
    
    Args:
        value: String to truncate
        max_length: Maximum length
        suffix: String to append when truncating
        
    Returns:
        Truncated string
    """
    if len(value) <= max_length:
        return value
        
    return value[:max_length - len(suffix)] + suffix

class Timer:
    """Context manager for timing code execution."""
    
    def __init__(self, name: str):
        """Initialize timer.
        
        Args:
            name: Name for logging
        """
        self.name = name
        self.start_time = None
        self.logger = get_logger('workflowmax.timer')
    
    def __enter__(self):
        """Start timer."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        """Log elapsed time."""
        elapsed = time.time() - self.start_time
        self.logger.info(
            f"{self.name} completed",
            elapsed_seconds=elapsed
        )
