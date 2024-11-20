"""Base configuration management for WorkflowMax API."""

from typing import Optional, Dict, Any
from pathlib import Path
import os
import yaml
from pydantic import BaseModel, Field, field_validator
import json
import re
from dotenv import load_dotenv

from ..core.exceptions import ConfigurationError
from ..core.logging import get_logger
from ..core.utils import find_project_root

logger = get_logger('workflowmax.config')

class BaseConfig(BaseModel):
    """Base configuration model with common functionality."""
    
    model_config = {
        'extra': 'forbid',  # Forbid extra attributes
        'validate_assignment': True  # Validate on attribute assignment
    }
    
    @staticmethod
    def _interpolate_env_vars(config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively interpolate environment variables in configuration values.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            Dictionary with interpolated values
        """
        def _interpolate_value(value: Any) -> Any:
            if isinstance(value, str):
                # Match ${VAR} pattern
                pattern = r'\${([^}]+)}'
                matches = re.finditer(pattern, value)
                
                # Replace all environment variables
                result = value
                for match in matches:
                    env_var = match.group(1)
                    env_value = os.getenv(env_var)
                    if env_value is None:
                        logger.warning(f"Environment variable {env_var} not found")
                        continue
                    result = result.replace(f"${{{env_var}}}", env_value)
                return result
            elif isinstance(value, dict):
                return {k: _interpolate_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [_interpolate_value(item) for item in value]
            return value
        
        return _interpolate_value(config_dict)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'BaseConfig':
        """Create instance from dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            Configuration instance
            
        Raises:
            ConfigurationError: If validation fails
        """
        try:
            # Interpolate environment variables before validation
            processed_dict = cls._interpolate_env_vars(config_dict)
            return cls.model_validate(processed_dict)
        except Exception as e:
            raise ConfigurationError(f"Invalid configuration: {str(e)}")
    
    @classmethod
    def from_yaml(cls, path: Path) -> 'BaseConfig':
        """Load configuration from YAML file.
        
        Args:
            path: Path to YAML file
            
        Returns:
            Configuration instance
            
        Raises:
            ConfigurationError: If file cannot be read or parsed
        """
        try:
            with open(path) as f:
                config_dict = yaml.safe_load(f)
            return cls.from_dict(config_dict)
        except Exception as e:
            raise ConfigurationError(f"Failed to load config from {path}: {str(e)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Configuration dictionary
        """
        return json.loads(self.model_dump_json(exclude_none=True))
    
    def to_yaml(self, path: Path):
        """Save configuration to YAML file.
        
        Args:
            path: Path to save YAML file
            
        Raises:
            ConfigurationError: If file cannot be written
        """
        try:
            with open(path, 'w') as f:
                yaml.safe_dump(self.to_dict(), f)
        except Exception as e:
            raise ConfigurationError(f"Failed to save config to {path}: {str(e)}")

class EnvironmentConfig(BaseConfig):
    """Environment-specific configuration."""
    
    environment: str = Field(
        default="development",
        description="Current environment (development, staging, production)"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        valid_environments = {'development', 'staging', 'production'}
        if v not in valid_environments:
            raise ValueError(f"Environment must be one of: {', '.join(valid_environments)}")
        return v

class PathConfig(BaseConfig):
    """Path configuration."""
    
    base_dir: Path = Field(
        default_factory=find_project_root,  # Use project root as base directory
        description="Base directory for the application"
    )
    config_dir: Path = Field(
        default=None,  # Will be set in post_init
        description="Configuration directory"
    )
    logs_dir: Path = Field(
        default=None,  # Will be set in post_init
        description="Logs directory"
    )
    cache_dir: Path = Field(
        default=None,  # Will be set in post_init
        description="Cache directory"
    )
    
    def __init__(self, **data):
        """Initialize path configuration with project structure."""
        super().__init__(**data)
        # Set default paths relative to base_dir/mtd_workflowmax
        pkg_dir = self.base_dir / 'mtd_workflowmax'
        self.config_dir = data.get('config_dir', pkg_dir / 'config')
        self.logs_dir = data.get('logs_dir', pkg_dir / 'logs')
        self.cache_dir = data.get('cache_dir', pkg_dir / 'cache')
        
        # Create directories
        for path in [self.config_dir, self.logs_dir, self.cache_dir]:
            path.mkdir(parents=True, exist_ok=True)

class ConfigurationManager:
    """Manages application configuration."""
    
    _instance = None
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize configuration manager."""
        if not self._initialized:
            self.env = EnvironmentConfig()
            self.paths = PathConfig()
            self._config_cache: Dict[str, BaseConfig] = {}
            self._load_environment()
            self._initialized = True
    
    def _load_environment(self):
        """Load configuration from environment variables."""
        # Load environment
        self.env.environment = os.getenv('WORKFLOWMAX_ENV', 'development')
        self.env.debug = os.getenv('WORKFLOWMAX_DEBUG', '').lower() == 'true'
        
        # Load paths
        if base_dir := os.getenv('WORKFLOWMAX_BASE_DIR'):
            self.paths.base_dir = Path(base_dir)
        if config_dir := os.getenv('WORKFLOWMAX_CONFIG_DIR'):
            self.paths.config_dir = Path(config_dir)
        if logs_dir := os.getenv('WORKFLOWMAX_LOGS_DIR'):
            self.paths.logs_dir = Path(logs_dir)
        if cache_dir := os.getenv('WORKFLOWMAX_CACHE_DIR'):
            self.paths.cache_dir = Path(cache_dir)
    
    def load_config(self, config_class: type, name: str) -> BaseConfig:
        """Load configuration of specified type.
        
        Args:
            config_class: Configuration class to load
            name: Configuration name/file
            
        Returns:
            Configuration instance
        """
        # Check cache first
        cache_key = f"{config_class.__name__}_{name}"
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        # First try loading from root config.yml if it exists
        root_config_path = self.paths.base_dir / 'config.yml'
        if root_config_path.exists():
            try:
                with open(root_config_path) as f:
                    root_config = yaml.safe_load(f)
                if name in root_config:
                    config = config_class.from_dict(root_config[name])
                    self._config_cache[cache_key] = config
                    return config
            except Exception as e:
                logger.warning(f"Failed to load {name} from root config.yml: {str(e)}")
        
        # If not found in root config, try package config directory
        config_file = self.paths.config_dir / f"{name}.yml"
        if config_file.exists():
            config = config_class.from_yaml(config_file)
        else:
            # If config class has a load method, use it
            if hasattr(config_class, 'load'):
                config = config_class.load()
            else:
                # Create default config
                config = config_class()
        
        # Load environment variables if config has load_from_env method
        if hasattr(config, 'load_from_env'):
            config.load_from_env()
            
        # Cache configuration
        self._config_cache[cache_key] = config
        return config
    
    def save_config(self, config: BaseConfig, name: str):
        """Save configuration to file.
        
        Args:
            config: Configuration instance to save
            name: Configuration name/file
        """
        config_file = self.paths.config_dir / f"{name}.yml"
        config.to_yaml(config_file)
        
        # Update cache
        cache_key = f"{config.__class__.__name__}_{name}"
        self._config_cache[cache_key] = config
    
    def clear_cache(self):
        """Clear configuration cache."""
        self._config_cache.clear()
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.env.environment == 'development'
    
    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.env.environment == 'staging'
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.env.environment == 'production'
