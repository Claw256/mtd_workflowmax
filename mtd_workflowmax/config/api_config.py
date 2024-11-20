"""API configuration for WorkflowMax API."""

from typing import Optional, Dict, Any, Set
from datetime import timedelta
from pathlib import Path
import yaml
from pydantic import BaseModel, Field, field_validator, HttpUrl

from .base import BaseConfig, ConfigurationManager
from ..core.exceptions import ConfigurationError
from ..core.logging import get_logger

logger = get_logger('workflowmax.config.api')

class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    
    model_config = {
        'extra': 'allow'  # Allow extra fields
    }
    
    enabled: bool = Field(
        default=True,
        description="Enable rate limiting"
    )
    concurrent_limit: int = Field(
        default=10,
        description="Maximum concurrent requests"
    )
    minute_limit: int = Field(
        default=60,
        description="Maximum requests per minute"
    )
    daily_limit: int = Field(
        default=5000,
        description="Maximum requests per day"
    )
    
    @field_validator('concurrent_limit', 'minute_limit', 'daily_limit')
    @classmethod
    def validate_positive(cls, v: int) -> int:
        """Validate limits are positive."""
        if v <= 0:
            raise ValueError("Value must be positive")
        return v

class RetryConfig(BaseModel):
    """Retry configuration."""
    
    model_config = {
        'extra': 'allow'  # Allow extra fields
    }
    
    enabled: bool = Field(
        default=True,
        description="Enable request retries"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts"
    )
    backoff_factor: float = Field(
        default=0.5,
        description="Exponential backoff factor"
    )
    retry_statuses: Set[int] = Field(
        default={429, 500, 502, 503, 504},
        description="HTTP status codes to retry"
    )
    
    @field_validator('max_retries')
    @classmethod
    def validate_max_retries(cls, v: int) -> int:
        """Validate max retries is non-negative."""
        if v < 0:
            raise ValueError("max_retries must be non-negative")
        return v
    
    @field_validator('backoff_factor')
    @classmethod
    def validate_backoff_factor(cls, v: float) -> float:
        """Validate backoff factor is positive."""
        if v <= 0:
            raise ValueError("backoff_factor must be positive")
        return v

class ConnectionConfig(BaseModel):
    """Connection configuration."""
    
    model_config = {
        'extra': 'allow'  # Allow extra fields
    }
    
    timeout: float = Field(
        default=30.0,
        description="Request timeout in seconds"
    )
    pool_connections: int = Field(
        default=100,
        description="Number of connection pools"
    )
    pool_maxsize: int = Field(
        default=200,
        description="Maximum size of each connection pool"
    )
    max_keepalive: int = Field(
        default=5,
        description="Maximum number of keepalive connections"
    )
    
    @field_validator('timeout', 'pool_connections', 'pool_maxsize', 'max_keepalive')
    @classmethod
    def validate_positive(cls, v: float) -> float:
        """Validate values are positive."""
        if v <= 0:
            raise ValueError("Value must be positive")
        return v

class CacheConfig(BaseModel):
    """Cache configuration."""
    
    model_config = {
        'extra': 'allow'  # Allow extra fields
    }
    
    enabled: bool = Field(
        default=True,
        description="Enable response caching"
    )
    ttl: timedelta = Field(
        default=timedelta(minutes=5),
        description="Default cache TTL"
    )
    max_size: int = Field(
        default=1000,
        description="Maximum number of cached items"
    )
    
    @field_validator('ttl')
    @classmethod
    def validate_ttl(cls, v: timedelta) -> timedelta:
        """Validate TTL is positive."""
        if v.total_seconds() <= 0:
            raise ValueError("TTL must be positive")
        return v
    
    @field_validator('max_size')
    @classmethod
    def validate_max_size(cls, v: int) -> int:
        """Validate max size is positive."""
        if v <= 0:
            raise ValueError("max_size must be positive")
        return v

class APIConfig(BaseConfig):
    """WorkflowMax API configuration."""
    
    model_config = {
        'extra': 'allow'  # Allow extra fields
    }
    
    base_url: HttpUrl = Field(
        default="https://api.workflowmax2.com",
        description="Base URL for API"
    )
    api_version: str = Field(
        default="1.0",  # Generic default, should be overridden by config.yml
        description="API version (configured in config.yml)"
    )
    batch_size: int = Field(
        default=50,
        description="Batch request size"
    )
    
    # Nested configurations
    rate_limit: RateLimitConfig = Field(
        default_factory=RateLimitConfig,
        description="Rate limiting configuration"
    )
    retry: RetryConfig = Field(
        default_factory=RetryConfig,
        description="Retry configuration"
    )
    connection: ConnectionConfig = Field(
        default_factory=ConnectionConfig,
        description="Connection configuration"
    )
    cache: CacheConfig = Field(
        default_factory=CacheConfig,
        description="Cache configuration"
    )
    
    # Custom headers
    custom_headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom headers to include in requests"
    )
    
    @field_validator('batch_size')
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        """Validate batch size is positive."""
        if v <= 0:
            raise ValueError("batch_size must be positive")
        return v
    
    def get_headers(self, auth_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get complete headers including authentication.
        
        Args:
            auth_headers: Optional authentication headers
            
        Returns:
            Complete headers dictionary
        """
        headers = {
            'Accept': 'application/xml',
            'Content-Type': 'application/xml',
            'User-Agent': f'WorkflowMaxAPI/{self.api_version}',
            **self.custom_headers
        }
        
        if auth_headers:
            headers.update(auth_headers)
            
        return headers
    
    def get_endpoint_url(self, endpoint: str) -> str:
        """Get complete URL for endpoint.
        
        Args:
            endpoint: API endpoint
            
        Returns:
            Complete URL
        """
        # Remove leading slash if present
        endpoint = endpoint.lstrip('/')
        return str(self.base_url / endpoint)
    
    @property
    def default_timeout(self) -> float:
        """Get default timeout value."""
        return self.connection.timeout
    
    @property
    def should_retry(self) -> bool:
        """Check if retries are enabled."""
        return self.retry.enabled
    
    @property
    def should_cache(self) -> bool:
        """Check if caching is enabled."""
        return self.cache.enabled

    @classmethod
    def load(cls) -> 'APIConfig':
        """Load API configuration from root config.yml.
        
        Returns:
            APIConfig instance
            
        Raises:
            ConfigurationError: If config cannot be loaded
        """
        try:
            # Find project root
            root_dir = Path.cwd()
            while root_dir != root_dir.parent:
                if (root_dir / 'config.yml').exists():
                    break
                root_dir = root_dir.parent
            
            config_path = root_dir / 'config.yml'
            if not config_path.exists():
                logger.warning("config.yml not found in project root, using defaults")
                return cls()
            
            # Load and parse config
            with open(config_path) as f:
                config = yaml.safe_load(f)
            
            api_config = config.get('api', {})
            if not api_config:
                logger.warning("No 'api' section found in config.yml, using defaults")
                return cls()
            
            # Convert cache ttl_minutes to timedelta
            if 'cache' in api_config and 'ttl_minutes' in api_config['cache']:
                minutes = api_config['cache'].pop('ttl_minutes')
                api_config['cache']['ttl'] = timedelta(minutes=minutes)
            
            # Map version to api_version if present
            if 'version' in api_config:
                api_config['api_version'] = api_config.pop('version')
            
            return cls.from_dict(api_config)
            
        except Exception as e:
            logger.warning(f"Failed to load API config from config.yml: {str(e)}")
            return cls()
