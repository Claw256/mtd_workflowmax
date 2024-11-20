"""Configuration management for WorkflowMax API."""

from typing import Optional, Dict, Any
from pathlib import Path

from .base import ConfigurationManager, BaseConfig, EnvironmentConfig, PathConfig
from .api_config import APIConfig, RateLimitConfig, RetryConfig, ConnectionConfig, CacheConfig
from .auth_config import AuthConfig, OAuth2Endpoints, OAuth2Credentials, TokenStorage, TokenRefresh
from ..core.exceptions import ConfigurationError
from ..core.logging import get_logger

logger = get_logger('workflowmax.config')

class WorkflowMaxConfig:
    """Unified configuration for WorkflowMax API."""
    
    def __init__(self):
        """Initialize configuration."""
        self._config_manager = ConfigurationManager()
        self._api_config: Optional[APIConfig] = None
        self._auth_config: Optional[AuthConfig] = None
        
        # Load configurations
        self.reload()
    
    def reload(self):
        """Reload all configurations."""
        logger.info("Reloading configuration")
        
        # Clear configuration cache
        self._config_manager.clear_cache()
        
        # Load configurations
        self._api_config = self._config_manager.load_config(APIConfig, 'api')
        self._auth_config = self._config_manager.load_config(AuthConfig, 'auth')
        
        # Load environment-specific overrides
        self._load_environment_config()
        
        logger.info("Configuration reloaded successfully")
    
    def _load_environment_config(self):
        """Load environment-specific configuration overrides."""
        env = self._config_manager.env.environment
        
        # Try to load environment-specific configs
        try:
            if env != 'development':
                # Load API config overrides
                api_config = self._config_manager.load_config(
                    APIConfig,
                    f'api.{env}'
                )
                self._api_config.copy_update(api_config.dict())
                
                # Load auth config overrides
                auth_config = self._config_manager.load_config(
                    AuthConfig,
                    f'auth.{env}'
                )
                self._auth_config.copy_update(auth_config.dict())
                
        except Exception as e:
            logger.warning(
                f"Failed to load environment config for {env}",
                error=str(e)
            )
    
    def validate(self):
        """Validate complete configuration.
        
        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            # Validate individual configs
            self.api.validate_config()
            self.auth.validate_config()
            
            # Validate compatibility between configs
            self._validate_compatibility()
            
        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {str(e)}")
    
    def _validate_compatibility(self):
        """Validate compatibility between different configurations.
        
        Raises:
            ConfigurationError: If configurations are incompatible
        """
        # Example: Validate rate limit and connection pool compatibility
        if self.api.rate_limit.concurrent_limit > self.api.connection.pool_maxsize:
            raise ConfigurationError(
                "Rate limit concurrent_limit cannot exceed connection pool_maxsize"
            )
    
    def save(self):
        """Save current configuration to files."""
        logger.info("Saving configuration")
        
        try:
            # Save main configs
            self._config_manager.save_config(self.api, 'api')
            self._config_manager.save_config(self.auth, 'auth')
            
            # Save environment-specific configs
            env = self._config_manager.env.environment
            if env != 'development':
                self._config_manager.save_config(self.api, f'api.{env}')
                self._config_manager.save_config(self.auth, f'auth.{env}')
                
            logger.info("Configuration saved successfully")
            
        except Exception as e:
            logger.error(
                "Failed to save configuration",
                error=str(e)
            )
            raise ConfigurationError(f"Failed to save configuration: {str(e)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Dictionary containing all configuration
        """
        return {
            'environment': self._config_manager.env.dict(),
            'paths': self._config_manager.paths.dict(),
            'api': self.api.dict(),
            'auth': self.auth.dict()
        }
    
    @property
    def api(self) -> APIConfig:
        """Get API configuration."""
        return self._api_config
    
    @property
    def auth(self) -> AuthConfig:
        """Get authentication configuration."""
        return self._auth_config
    
    @property
    def environment(self) -> EnvironmentConfig:
        """Get environment configuration."""
        return self._config_manager.env
    
    @property
    def paths(self) -> PathConfig:
        """Get path configuration."""
        return self._config_manager.paths
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self._config_manager.is_development
    
    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self._config_manager.is_staging
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self._config_manager.is_production

# Global configuration instance
config = WorkflowMaxConfig()

__all__ = [
    'config',
    'WorkflowMaxConfig',
    'APIConfig',
    'AuthConfig',
    'BaseConfig',
    'EnvironmentConfig',
    'PathConfig',
    'RateLimitConfig',
    'RetryConfig',
    'ConnectionConfig',
    'CacheConfig',
    'OAuth2Endpoints',
    'OAuth2Credentials',
    'TokenStorage',
    'TokenRefresh'
]
