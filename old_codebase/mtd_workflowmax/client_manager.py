"""API client management for WorkflowMax API."""

from contextlib import contextmanager
from typing import Generator, Tuple, Dict
from .api_client import APIClient
from .auth import OAuthManager
from .exceptions import AuthenticationError
from .logging_config import get_logger

logger = get_logger('workflowmax.client_manager')

class APIClientManager:
    """Manages API client lifecycle and authentication."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super(APIClientManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the manager if not already initialized."""
        if not self._initialized:
            self._oauth_manager = OAuthManager()
            self._api_client = None
            self._initialized = True

    def get_client(self) -> APIClient:
        """Get an authenticated API client.
        
        Returns:
            APIClient: Authenticated API client instance
            
        Raises:
            AuthenticationError: If authentication fails
        """
        if self._api_client is None:
            logger.info("Initializing new API client")
            tokens, org_id = self._oauth_manager.authenticate()
            
            self._api_client = APIClient()
            self._api_client.set_auth(tokens, org_id)
            logger.info("API client initialized and authenticated")
            
        return self._api_client

    @contextmanager
    def get_client_context(self) -> Generator[APIClient, None, None]:
        """Context manager for getting an authenticated API client.
        
        Yields:
            APIClient: Authenticated API client instance
            
        Example:
            with APIClientManager().get_client_context() as client:
                response = client.get('some/endpoint')
        """
        try:
            client = self.get_client()
            yield client
        except Exception as e:
            logger.error(f"Error in API client context: {str(e)}")
            raise
        finally:
            # Could add cleanup logic here if needed
            pass

    def refresh_auth(self) -> Tuple[Dict, str]:
        """Force refresh of authentication tokens.
        
        Returns:
            Tuple[Dict, str]: Tuple of (tokens, org_id)
            
        Raises:
            AuthenticationError: If authentication fails
        """
        logger.info("Forcing authentication refresh")
        tokens, org_id = self._oauth_manager.authenticate(force_refresh=True)
        
        if self._api_client:
            self._api_client.set_auth(tokens, org_id)
            logger.info("Updated API client with refreshed authentication")
            
        return tokens, org_id

    def clear_client(self) -> None:
        """Clear the current API client instance."""
        self._api_client = None
        logger.info("Cleared API client instance")
