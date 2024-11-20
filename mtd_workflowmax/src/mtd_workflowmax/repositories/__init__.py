"""Repository initialization."""

from typing import Optional

from ..api.client import APIClient
from .custom_field_repository import CustomFieldRepository
from .contact_repository import ContactRepository
from .job_repository import JobRepository

class Repositories:
    """Container for all repositories."""
    
    def __init__(self, api_client: APIClient):
        """Initialize repositories.
        
        Args:
            api_client: Initialized API client instance
        """
        # Initialize repositories in dependency order
        self.custom_fields = CustomFieldRepository(api_client)
        self.contacts = ContactRepository(api_client, self.custom_fields)
        self.jobs = JobRepository(api_client, self.custom_fields)

# Global repositories instance
repositories: Optional[Repositories] = None

def initialize(api_client: APIClient) -> Repositories:
    """Initialize global repositories instance.
    
    Args:
        api_client: Initialized API client instance
        
    Returns:
        Initialized Repositories instance
    """
    global repositories
    repositories = Repositories(api_client)
    return repositories
