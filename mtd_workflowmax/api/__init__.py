"""API components for WorkflowMax API."""

from typing import Optional, Dict
from ..core.utils import Singleton
from ..core.logging import get_logger
from ..core.exceptions import AuthenticationError
from .client import APIClient
from .auth import OAuthManager

logger = get_logger('workflowmax.api')

class APIManager(Singleton):
    """Manager for API client and authentication."""
    
    def __init__(self):
        """Initialize API manager."""
        if not hasattr(self, '_initialized'):
            self._api_client: Optional[APIClient] = None
            self._auth_manager: Optional[OAuthManager] = None
            self._initialized = True
    
    @property
    def client(self) -> APIClient:
        """Get API client.
        
        Returns:
            APIClient instance
            
        Raises:
            RuntimeError: If client not initialized
        """
        if self._api_client is None:
            raise RuntimeError("API client not initialized")
        return self._api_client
    
    @property
    def auth(self) -> OAuthManager:
        """Get OAuth manager.
        
        Returns:
            OAuthManager instance
        """
        if self._auth_manager is None:
            self._auth_manager = OAuthManager()
        return self._auth_manager
    
    def initialize(self, force_auth: bool = False) -> APIClient:
        """Initialize API client with authentication.
        
        Args:
            force_auth: Whether to force new authentication
            
        Returns:
            Initialized APIClient instance
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Create new API client
            self._api_client = APIClient()
            
            # Perform authentication
            tokens, org_id = self.auth.authenticate(force_refresh=force_auth)
            
            # Set authentication on client
            self._api_client.set_auth(tokens, org_id)
            
            logger.info("API client initialized successfully")
            return self._api_client
            
        except Exception as e:
            self._api_client = None
            logger.error(f"Failed to initialize API client: {str(e)}")
            raise AuthenticationError(f"Failed to initialize API client: {str(e)}")
    
    def clear(self):
        """Clear API manager state."""
        self._api_client = None
        self._auth_manager = None
        logger.info("API manager cleared")

# Global API manager instance
api = APIManager()

__all__ = [
    'api',
    'APIManager',
    'APIClient',
    'OAuthManager'
]
