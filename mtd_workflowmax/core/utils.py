"""Utility functions and helpers for WorkflowMax API."""

import time
from typing import TypeVar, Callable, Any, Dict, Optional
from functools import wraps
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .logging import get_logger
from .exceptions import ValidationError, XMLParsingError

logger = get_logger('workflowmax.utils')

T = TypeVar('T')

def find_project_root() -> Path:
    """Find the project root directory by looking for .env file.
    
    Returns:
        Path to project root directory
    """
    current = Path.cwd()
    logger.debug(f"Starting search for project root from: {current}")
    
    # First check current directory and parents
    while current != current.parent:
        if (current / '.env').exists():
            logger.debug(f"Found .env file in: {current}")
            return current
        if (current / 'setup.py').exists():
            logger.debug(f"Found setup.py in: {current}")
            return current
        logger.debug(f"No .env or setup.py found in: {current}")
        current = current.parent
    
    # If not found, check if we're in src directory
    if Path.cwd().name == 'src':
        parent = Path.cwd().parent
        logger.debug(f"In src directory, checking parent: {parent}")
        if (parent / '.env').exists():
            logger.debug(f"Found .env file in parent: {parent}")
            return parent
        if (parent / 'setup.py').exists():
            logger.debug(f"Found setup.py in parent: {parent}")
            return parent
        logger.debug(f"No .env or setup.py found in parent: {parent}")
    
    logger.debug(f"No project root found, returning cwd: {Path.cwd()}")
    return Path.cwd()

def get_xml_text(
    element: ET.Element,
    tag: str,
    default: Optional[str] = None,
    required: bool = False
) -> Optional[str]:
    """Get text content of an XML element.
    
    Args:
        element: Parent XML element
        tag: Tag name to find
        default: Default value if tag not found
        required: Whether the tag is required
        
    Returns:
        Text content or default value
        
    Raises:
        XMLParsingError: If required tag is missing
    """
    try:
        child = element.find(tag)
        if child is None:
            if required:
                raise XMLParsingError(f"Required tag {tag} not found")
            return default
        return child.text or default
    except Exception as e:
        if required:
            raise XMLParsingError(f"Error getting required tag {tag}: {str(e)}")
        logger.warning(f"Error getting tag {tag}: {str(e)}")
        return default

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

def get_cache_age(timestamp: Optional[float]) -> float:
    """Get age of cache in seconds.
    
    Args:
        timestamp: Cache timestamp (seconds since epoch)
        
    Returns:
        Age in seconds, or float('inf') if timestamp is None
    """
    if timestamp is None:
        return float('inf')
    return time.time() - timestamp

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
