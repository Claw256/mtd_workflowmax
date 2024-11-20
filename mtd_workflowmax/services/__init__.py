"""Business logic services for WorkflowMax API."""

from typing import Optional
from ..core.utils import Singleton
from ..core.logging import get_logger
from .contact_service import ContactService
from .custom_field_service import CustomFieldService
from .linkedin_service import LinkedInService

logger = get_logger('workflowmax.services')

class ServiceManager(Singleton):
    """Manager for accessing services."""
    
    def __init__(self):
        """Initialize service manager."""
        if not hasattr(self, '_initialized'):
            self._contact_service: Optional[ContactService] = None
            self._custom_field_service: Optional[CustomFieldService] = None
            self._linkedin_service: Optional[LinkedInService] = None
            self._initialized = True
    
    @property
    def contacts(self) -> ContactService:
        """Get contact service.
        
        Returns:
            ContactService instance
        """
        if self._contact_service is None:
            self._contact_service = ContactService()
            logger.debug("Initialized contact service")
            
        return self._contact_service
    
    @property
    def custom_fields(self) -> CustomFieldService:
        """Get custom field service.
        
        Returns:
            CustomFieldService instance
        """
        if self._custom_field_service is None:
            self._custom_field_service = CustomFieldService()
            logger.debug("Initialized custom field service")
            
        return self._custom_field_service
    
    def initialize_linkedin(self, username: str, password: str) -> LinkedInService:
        """Initialize LinkedIn service with credentials.
        
        Args:
            username: LinkedIn username
            password: LinkedIn password
            
        Returns:
            LinkedInService instance
        """
        self._linkedin_service = LinkedInService(username, password)
        logger.info("Initialized LinkedIn service")
        return self._linkedin_service
    
    @property
    def linkedin(self) -> LinkedInService:
        """Get LinkedIn service.
        
        Returns:
            LinkedInService instance
            
        Raises:
            RuntimeError: If LinkedIn service not initialized
        """
        if self._linkedin_service is None:
            raise RuntimeError(
                "LinkedIn service not initialized. Call initialize_linkedin() first."
            )
        return self._linkedin_service
    
    def clear(self):
        """Clear all services."""
        self._contact_service = None
        self._custom_field_service = None
        self._linkedin_service = None
        logger.info("Service manager cleared")

# Global service manager instance
services = ServiceManager()

__all__ = [
    'services',
    'ServiceManager',
    'ContactService',
    'CustomFieldService',
    'LinkedInService'
]
