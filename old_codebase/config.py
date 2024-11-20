"""Configuration management for WorkflowMax API client."""

import os
import yaml
from typing import Dict, Any, Optional
from dataclasses import dataclass
from .exceptions import ConfigurationError
from .logging_config import get_logger

logger = get_logger('workflowmax.config')

@dataclass
class OAuth2Config:
    """OAuth2 configuration settings."""
    redirect_uri: str = 'http://localhost:8000/callback'
    auth_url: str = 'https://oauth.workflowmax2.com/oauth/authorize'
    token_url: str = 'https://oauth.workflowmax2.com/oauth/token'
    cache_file: str = '.oauth_cache.json'
    scope: str = 'openid profile email workflowmax offline_access'

@dataclass
class APIConfig:
    """API configuration settings."""
    base_url: str = 'https://api.workflowmax2.com'
    max_retries: int = 3
    timeout: int = 30
    pool_connections: int = 200
    pool_maxsize: int = 200

@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    concurrent_limit: int = 5
    minute_limit: int = 60
    daily_limit: int = 5000
    requests_per_second: float = 2.0

class Config:
    """Central configuration management."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one config instance exists."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize configuration if not already initialized."""
        if not self._initialized:
            self._load_config()
            self._initialized = True

    def _load_config(self):
        """Load and validate configuration from multiple sources."""
        # Load default configurations
        self.oauth = OAuth2Config()
        self.api = APIConfig()
        self.rate_limit = RateLimitConfig()
        
        # Load from config file
        config_file = 'config.yml'
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    file_config = yaml.safe_load(f) or {}
                self._update_from_dict(file_config)
                logger.info("Loaded configuration from config.yml")
            except Exception as e:
                logger.warning(f"Error loading config file: {str(e)}")

        # Load from environment variables
        self._load_from_env()
        
        # Validate configuration
        self._validate_config()

    def _update_from_dict(self, config_dict: Dict[str, Any]):
        """Update configuration from dictionary."""
        if 'oauth' in config_dict:
            for key, value in config_dict['oauth'].items():
                if hasattr(self.oauth, key):
                    setattr(self.oauth, key, value)
                    
        if 'api' in config_dict:
            for key, value in config_dict['api'].items():
                if hasattr(self.api, key):
                    setattr(self.api, key, value)
                    
        if 'rate_limit' in config_dict:
            for key, value in config_dict['rate_limit'].items():
                if hasattr(self.rate_limit, key):
                    setattr(self.rate_limit, key, value)

    def _load_from_env(self):
        """Load configuration from environment variables."""
        # OAuth2 credentials
        self.client_id = os.getenv('CLIENT_ID')
        self.client_secret = os.getenv('CLIENT_SECRET')
        
        # Override configs from env vars if present
        if api_url := os.getenv('WORKFLOWMAX_API_URL'):
            self.api.base_url = api_url
            
        if max_retries := os.getenv('WORKFLOWMAX_MAX_RETRIES'):
            try:
                self.api.max_retries = int(max_retries)
            except ValueError:
                logger.warning(f"Invalid max_retries value in env: {max_retries}")

    def _validate_config(self):
        """Validate the configuration."""
        if not self.client_id or not self.client_secret:
            raise ConfigurationError("CLIENT_ID and CLIENT_SECRET must be set in environment")
            
        if not self.api.base_url.startswith(('http://', 'https://')):
            raise ConfigurationError(f"Invalid API base URL: {self.api.base_url}")
            
        if self.api.max_retries < 0:
            raise ConfigurationError(f"Invalid max_retries value: {self.api.max_retries}")
            
        if self.api.timeout < 0:
            raise ConfigurationError(f"Invalid timeout value: {self.api.timeout}")
            
        if self.rate_limit.requests_per_second <= 0:
            raise ConfigurationError(
                f"Invalid requests_per_second value: {self.rate_limit.requests_per_second}"
            )

    def get_oauth_config(self) -> OAuth2Config:
        """Get OAuth2 configuration."""
        return self.oauth

    def get_api_config(self) -> APIConfig:
        """Get API configuration."""
        return self.api

    def get_rate_limit_config(self) -> RateLimitConfig:
        """Get rate limiting configuration."""
        return self.rate_limit

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'oauth': {
                'redirect_uri': self.oauth.redirect_uri,
                'auth_url': self.oauth.auth_url,
                'token_url': self.oauth.token_url,
                'cache_file': self.oauth.cache_file,
                'scope': self.oauth.scope
            },
            'api': {
                'base_url': self.api.base_url,
                'max_retries': self.api.max_retries,
                'timeout': self.api.timeout,
                'pool_connections': self.api.pool_connections,
                'pool_maxsize': self.api.pool_maxsize
            },
            'rate_limit': {
                'concurrent_limit': self.rate_limit.concurrent_limit,
                'minute_limit': self.rate_limit.minute_limit,
                'daily_limit': self.rate_limit.daily_limit,
                'requests_per_second': self.rate_limit.requests_per_second
            }
        }
