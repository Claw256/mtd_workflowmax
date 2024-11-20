"""WorkflowMax API client library."""

__version__ = '0.1.0'

import os
import json
from typing import Optional, Dict
from .core.logging import get_logger, with_logging
from .core.exceptions import WorkflowMaxError
from .api import api
from .repositories import repositories, initialize as init_repositories, Repositories
from .services.contact_service import ContactService
from .services.custom_field_service import CustomFieldService
from .services.workflowmax_linkedin_service import WorkflowMaxLinkedInService
from .services.relationship_service import RelationshipService
from .services.job_service import JobService

logger = get_logger('workflowmax')

class WorkflowMax:
    """Main entry point for WorkflowMax API interactions."""
    
    def __init__(self):
        """Initialize WorkflowMax client."""
        self._initialized = False
        self._repositories: Optional[Repositories] = None
        self._contacts: Optional[ContactService] = None
        self._custom_fields: Optional[CustomFieldService] = None
        self._linkedin: Optional[WorkflowMaxLinkedInService] = None
        self._relationships: Optional[RelationshipService] = None
        self._jobs: Optional[JobService] = None
    
    def initialize(self):
        """Initialize the client.
        
        Raises:
            WorkflowMaxError: If initialization fails
        """
        try:
            # Get authenticated API client
            api_client = api.initialize()
            
            # Initialize repositories
            self._repositories = init_repositories(api_client)
            
            # Initialize services with repositories instance
            self._contacts = ContactService(self._repositories)
            self._custom_fields = CustomFieldService(self._repositories)
            self._relationships = RelationshipService()
            self._jobs = JobService()
            
            self._initialized = True
            logger.info("WorkflowMax client initialized")
            
        except Exception as e:
            logger.error("Failed to initialize WorkflowMax client", error=str(e))
            raise WorkflowMaxError("Failed to initialize WorkflowMax client") from e
    
    def initialize_linkedin(
        self,
        username: str,
        password: str,
        authenticate: bool = True,
        refresh_cookies: bool = False,
        debug: bool = False,
        proxies: Dict[str, str] = {},
        cookies: Optional[Dict[str, str]] = None,
        cookies_dir: str = ''
    ) -> WorkflowMaxLinkedInService:
        """Initialize LinkedIn integration.
        
        Args:
            username: LinkedIn account username
            password: LinkedIn account password
            authenticate: Whether to authenticate on initialization
            refresh_cookies: Whether to refresh cookies on initialization
            debug: Whether to enable debug mode
            proxies: Proxy configuration for requests
            cookies: Pre-configured cookies to use
            cookies_dir: Directory to store cookies in
            
        Returns:
            WorkflowMaxLinkedInService: Initialized LinkedIn service
            
        Raises:
            WorkflowMaxError: If initialization fails
        """
        try:
            self._ensure_initialized()
            self._linkedin = WorkflowMaxLinkedInService(
                username,
                password,
                repositories=self._repositories,
                authenticate=authenticate,
                refresh_cookies=refresh_cookies,
                debug=debug,
                proxies=proxies,
                cookies=cookies,
                cookies_dir=cookies_dir
            )
            logger.info("LinkedIn integration initialized")
            return self._linkedin
            
        except Exception as e:
            logger.error("Failed to initialize LinkedIn integration", error=str(e))
            raise WorkflowMaxError("Failed to initialize LinkedIn integration") from e
    
    @property
    def contacts(self) -> ContactService:
        """Get contacts service."""
        self._ensure_initialized()
        return self._contacts
    
    @property
    def custom_fields(self) -> CustomFieldService:
        """Get custom fields service."""
        self._ensure_initialized()
        return self._custom_fields
    
    @property
    def linkedin(self) -> WorkflowMaxLinkedInService:
        """Get LinkedIn service."""
        self._ensure_initialized()
        if self._linkedin is None:
            raise WorkflowMaxError("LinkedIn integration not initialized")
        return self._linkedin
    
    @linkedin.setter
    def linkedin(self, service: WorkflowMaxLinkedInService):
        """Set LinkedIn service."""
        self._linkedin = service
    
    @property
    def relationships(self) -> RelationshipService:
        """Get relationships service."""
        self._ensure_initialized()
        return self._relationships
    
    @property
    def jobs(self) -> JobService:
        """Get jobs service."""
        self._ensure_initialized()
        return self._jobs
    
    def is_initialized(self) -> bool:
        """Check if client is initialized.
        
        Returns:
            True if initialized
        """
        return self._initialized
    
    def _ensure_initialized(self):
        """Ensure client is initialized.
        
        Raises:
            RuntimeError: If client not initialized
        """
        if not self._initialized:
            raise RuntimeError("WorkflowMax client not initialized")
