"""API client management for WorkflowMax API."""

from contextlib import contextmanager
from typing import Generator, Tuple, Dict, Optional
from threading import Lock

from ..core.exceptions import AuthenticationError
from ..core.logging import get_logger, with_logging
from ..core.utils import Timer
from .auth import OAuthManager
from .client import APIClient

logger = get_logger('workflowmax.api.client_manager')

class APIClientManager:
    """Thread-safe singleton manager for API client lifecycle and authentication."""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        """Singleton pattern to ensure only one instance exists."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(APIClientManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the manager if not already initialized."""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._oauth_manager = OAuthManager()
                    self._api_client: Optional[APIClient] = None
                    self._initialized = True

    @with_logging
    def get_client(self) -> APIClient:
        """Get an authenticated API client.
        
        Returns:
            APIClient: Authenticated API client instance
            
        Raises:
            AuthenticationError: If authentication fails
        """
        with Timer("Get API client"):
            with self._lock:
                if self._api_client is None:
                    logger.info("Initializing new API client")
                    
                    try:
                        tokens, org_id = self._oauth_manager.authenticate()
                        
                        self._api_client = APIClient()
                        self._api_client.set_auth(tokens, org_id)
                        
                        logger.info("API client initialized and authenticated")
                        
                    except Exception as e:
                        logger.error("Failed to initialize API client", error=str(e))
                        raise AuthenticationError(str(e))
                
                return self._api_client

    @contextmanager
    def get_client_context(self) -> Generator[APIClient, None, None]:
        """Context manager for getting an authenticated API client.
        
        Yields:
            APIClient: Authenticated API client instance
            
        Raises:
            AuthenticationError: If authentication fails
            
        Example:
            with APIClientManager().get_client_context() as client:
                response = client.get('some/endpoint')
        """
        with Timer("API client context"):
            try:
                client = self.get_client()
                yield client
            except Exception as e:
                logger.error("Error in API client context", error=str(e))
                self.clear_client()  # Clear client on error
                raise
            finally:
                # Could add cleanup logic here if needed
                pass

    @with_logging
    def refresh_auth(self) -> Tuple[Dict, str]:
        """Force refresh of authentication tokens.
        
        Returns:
            Tuple[Dict, str]: Tuple of (tokens, org_id)
            
        Raises:
            AuthenticationError: If authentication fails
        """
        with Timer("Refresh authentication"):
            with self._lock:
                try:
                    logger.info("Forcing authentication refresh")
                    tokens, org_id = self._oauth_manager.authenticate(force_refresh=True)
                    
                    if self._api_client:
                        self._api_client.set_auth(tokens, org_id)
                        logger.info("Updated API client with refreshed authentication")
                    
                    return tokens, org_id
                    
                except Exception as e:
                    logger.error("Failed to refresh authentication", error=str(e))
                    self.clear_client()  # Clear client on error
                    raise AuthenticationError(str(e))

    @with_logging
    def clear_client(self) -> None:
        """Clear the current API client instance."""
        with self._lock:
            self._api_client = None
            logger.info("Cleared API client instance")

# Global instance for convenience
client_manager = APIClientManager()
