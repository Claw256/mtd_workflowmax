"""Authentication configuration for WorkflowMax API."""

from typing import Optional
from pathlib import Path
from pydantic import BaseModel, Field, HttpUrl, SecretStr, field_validator

from .base import BaseConfig
from ..core.exceptions import ConfigurationError

class OAuth2Endpoints(BaseModel):
    """OAuth2 endpoint configuration."""
    
    authorize_url: HttpUrl = Field(
        default="https://oauth.workflowmax2.com/oauth/authorize",
        description="Authorization endpoint URL"
    )
    token_url: HttpUrl = Field(
        default="https://oauth.workflowmax2.com/oauth/token",
        description="Token endpoint URL"
    )
    redirect_uri: HttpUrl = Field(
        default="http://localhost:8080/callback",
        description="OAuth2 redirect URI"
    )

class OAuth2Credentials(BaseModel):
    """OAuth2 credentials configuration."""
    
    client_id: str = Field(
        default="",
        description="OAuth2 client ID"
    )
    client_secret: SecretStr = Field(
        default=SecretStr(""),
        description="OAuth2 client secret"
    )
    scope: str = Field(
        default="openid profile email workflowmax offline_access",
        description="OAuth2 scope"
    )

class TokenStorage(BaseModel):
    """Token storage configuration."""
    
    enabled: bool = Field(
        default=True,
        description="Enable token storage"
    )
    file_path: Optional[Path] = Field(
        default=Path(".oauth_cache.json"),
        description="Path to token storage file"
    )
    encryption_key: Optional[SecretStr] = Field(
        default=None,
        description="Key for token encryption"
    )
    
    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v: Optional[Path]) -> Optional[Path]:
        """Validate file path."""
        if v:
            # Create parent directories if they don't exist
            v.parent.mkdir(parents=True, exist_ok=True)
        return v

class TokenRefresh(BaseModel):
    """Token refresh configuration."""
    
    auto_refresh: bool = Field(
        default=True,
        description="Enable automatic token refresh"
    )
    refresh_threshold: int = Field(
        default=300,  # 5 minutes
        description="Seconds before expiry to trigger refresh"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum refresh retry attempts"
    )
    
    @field_validator('refresh_threshold', 'max_retries')
    @classmethod
    def validate_positive(cls, v: int) -> int:
        """Validate values are positive."""
        if v <= 0:
            raise ValueError("Value must be positive")
        return v

class AuthConfig(BaseConfig):
    """Authentication configuration."""
    
    auth_type: str = Field(
        default="oauth2",
        description="Authentication type (oauth2)"
    )
    
    # OAuth2 configuration
    oauth2_endpoints: OAuth2Endpoints = Field(
        default_factory=OAuth2Endpoints,
        description="OAuth2 endpoint configuration"
    )
    oauth2_credentials: OAuth2Credentials = Field(
        default_factory=OAuth2Credentials,
        description="OAuth2 credentials configuration"
    )
    
    # Token management
    token_storage: TokenStorage = Field(
        default_factory=TokenStorage,
        description="Token storage configuration"
    )
    token_refresh: TokenRefresh = Field(
        default_factory=TokenRefresh,
        description="Token refresh configuration"
    )
    
    @field_validator('auth_type')
    @classmethod
    def validate_auth_type(cls, v: str) -> str:
        """Validate authentication type."""
        if v.lower() != "oauth2":
            raise ValueError("Only OAuth2 authentication is supported")
        return v.lower()
    
    def load_from_env(self):
        """Load configuration from environment variables."""
        import os
        
        # OAuth2 endpoints
        if auth_url := os.getenv('WORKFLOWMAX_AUTH_URL'):
            self.oauth2_endpoints.authorize_url = auth_url
        if token_url := os.getenv('WORKFLOWMAX_TOKEN_URL'):
            self.oauth2_endpoints.token_url = token_url
        if redirect_uri := os.getenv('WORKFLOWMAX_REDIRECT_URI'):
            self.oauth2_endpoints.redirect_uri = redirect_uri
            
        # OAuth2 credentials
        if client_id := os.getenv('CLIENT_ID'):
            self.oauth2_credentials.client_id = client_id
        if client_secret := os.getenv('CLIENT_SECRET'):
            self.oauth2_credentials.client_secret = SecretStr(client_secret)
        if scope := os.getenv('WORKFLOWMAX_SCOPE'):
            self.oauth2_credentials.scope = scope
            
        # Token storage
        if storage_path := os.getenv('WORKFLOWMAX_TOKEN_STORAGE'):
            self.token_storage.file_path = Path(storage_path)
        if encryption_key := os.getenv('WORKFLOWMAX_TOKEN_ENCRYPTION_KEY'):
            self.token_storage.encryption_key = SecretStr(encryption_key)
    
    def validate_config(self):
        """Validate complete configuration.
        
        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            # Check required OAuth2 settings
            if not self.oauth2_endpoints.authorize_url:
                raise ValueError("OAuth2 authorize URL is required")
            if not self.oauth2_endpoints.token_url:
                raise ValueError("OAuth2 token URL is required")
            if not self.oauth2_endpoints.redirect_uri:
                raise ValueError("OAuth2 redirect URI is required")
                
            if not self.oauth2_credentials.client_id:
                raise ValueError("OAuth2 client ID is required")
            if not self.oauth2_credentials.client_secret.get_secret_value():
                raise ValueError("OAuth2 client secret is required")
                
            # Validate token storage if enabled
            if self.token_storage.enabled:
                if not self.token_storage.file_path:
                    raise ValueError("Token storage path is required when storage is enabled")
                    
        except ValueError as e:
            raise ConfigurationError(f"Invalid auth configuration: {str(e)}")
    
    def get_oauth_params(self) -> dict:
        """Get OAuth2 parameters for authorization.
        
        Returns:
            Dictionary of OAuth2 parameters
        """
        return {
            "client_id": self.oauth2_credentials.client_id,
            "client_secret": self.oauth2_credentials.client_secret.get_secret_value(),
            "redirect_uri": str(self.oauth2_endpoints.redirect_uri),
            "scope": self.oauth2_credentials.scope,
            "authorize_url": str(self.oauth2_endpoints.authorize_url),
            "token_url": str(self.oauth2_endpoints.token_url)
        }
    
    @property
    def should_store_tokens(self) -> bool:
        """Check if token storage is enabled."""
        return self.token_storage.enabled and bool(self.token_storage.file_path)
    
    @property
    def should_encrypt_tokens(self) -> bool:
        """Check if token encryption is enabled."""
        return bool(self.token_storage.encryption_key)
    
    @property
    def should_auto_refresh(self) -> bool:
        """Check if automatic token refresh is enabled."""
        return self.token_refresh.auto_refresh
