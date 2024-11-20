"""Service for managing WorkflowMax contacts."""

from typing import Optional, List, Dict, Any
from datetime import datetime

from ..core.exceptions import (
    ValidationError,
    ResourceNotFoundError,
    WorkflowMaxError
)
from ..core.logging import get_logger, with_logging
from ..core.utils import Timer
from ..models import Contact, CustomFieldValue, CustomFieldType
from ..repositories import Repositories
from ..config import config

logger = get_logger('workflowmax.services.contact')

class ContactService:
    """Service for contact operations."""
    
    # Special fields that get updated automatically
    INFO_UPTODATE_FIELD = "Is Info up-to-date?"
    LINKEDIN_FIELD = "LINKEDIN PROFILE"
    
    def __init__(self, repositories: Repositories):
        """Initialize contact service.
        
        Args:
            repositories: Initialized repositories instance
        """
        self._repositories = repositories
    
    @with_logging
    def get_contact(self, uuid: str, include_custom_fields: bool = True) -> Contact:
        """Get contact by UUID with optional custom fields.
        
        Args:
            uuid: Contact UUID
            include_custom_fields: Whether to include custom fields
            
        Returns:
            Contact instance
            
        Raises:
            ResourceNotFoundError: If contact not found
            WorkflowMaxError: If API request fails
        """
        with Timer("Get contact"):
            # Get basic contact info
            contact = self._repositories.contacts.get_by_uuid(uuid)
            
            # Add custom fields if requested
            if include_custom_fields:
                # Get field definitions
                definitions = {
                    d.name: d for d in self._repositories.custom_fields.get_definitions()
                    if d.use_contact  # Only include fields that can be used on contacts
                }
                
                # Get current field values
                custom_fields = self._repositories.contacts.get_custom_fields(uuid)
                field_values = {f.name: f for f in custom_fields}
                
                # Create list of all fields, including empty ones
                all_fields = []
                for name, definition in definitions.items():
                    if name in field_values:
                        field = field_values[name]
                        # Ensure field has correct type from definition
                        field.type = definition.type
                        all_fields.append(field)
                    else:
                        # Create empty field with correct type from definition
                        all_fields.append(CustomFieldValue(
                            Name=name,  # Name is required
                            value=None,
                            type=definition.type  # Use type from definition
                        ))
                
                contact.custom_fields = all_fields
                
            return contact
    
    @with_logging
    def update_custom_fields(
        self,
        uuid: str,
        updates: Dict[str, str],
        validate: bool = True,
        auto_update_info_status: bool = False  # Changed to False by default
    ) -> bool:
        """Update contact custom fields.
        
        Args:
            uuid: Contact UUID
            updates: Dictionary mapping field names to new values
            validate: Whether to validate values against field definitions
            auto_update_info_status: Whether to automatically update info status
            
        Returns:
            True if all updates successful
            
        Raises:
            ResourceNotFoundError: If contact not found
            ValidationError: If validation fails
            WorkflowMaxError: If API request fails
        """
        with Timer("Update contact custom fields"):
            # Verify contact exists
            if not self._repositories.contacts.exists(uuid):
                raise ResourceNotFoundError('Contact', uuid)
            
            # Process updates
            processed_updates = updates.copy()
            
            # Auto-update info status if requested
            if auto_update_info_status and updates:
                processed_updates[self.INFO_UPTODATE_FIELD] = 'true'
            
            # Get field definitions if validation requested
            if validate:
                definitions = {
                    d.name: d for d in self._repositories.custom_fields.get_definitions()
                    if d.use_contact  # Only include fields that can be used on contacts
                }
                
                # Validate each field
                errors = []
                for field_name, field_value in processed_updates.items():
                    if field_name not in definitions:
                        errors.append(f"Custom field '{field_name}' not found or not valid for contacts")
                        continue
                        
                    try:
                        self._repositories.custom_fields.validate_field_value(
                            field_name,
                            field_value,
                            definitions[field_name]
                        )
                    except ValidationError as e:
                        errors.append(f"{field_name}: {str(e)}")
                
                if errors:
                    raise ValidationError(
                        "Custom field validation failed",
                        errors=errors
                    )
            
            # Perform updates
            return self._repositories.contacts.update_custom_fields(uuid, processed_updates)
    
    @with_logging
    def search_contacts(
        self,
        query: Optional[str] = None,
        include_custom_fields: bool = False,
        page: int = 1,
        page_size: int = 50
    ) -> List[Contact]:
        """Search for contacts with optional custom fields.
        
        Args:
            query: Optional search query
            include_custom_fields: Whether to include custom fields
            page: Page number (1-based)
            page_size: Results per page
            
        Returns:
            List of contacts matching criteria
            
        Raises:
            ValidationError: If invalid parameters
            WorkflowMaxError: If API request fails
        """
        with Timer("Search contacts"):
            # Search for contacts
            contacts = self._repositories.contacts.search(query, page, page_size)
            
            # Add custom fields if requested
            if include_custom_fields and contacts:
                # Get field definitions
                definitions = {
                    d.name: d for d in self._repositories.custom_fields.get_definitions()
                    if d.use_contact  # Only include fields that can be used on contacts
                }
                
                for contact in contacts:
                    try:
                        # Get current field values
                        custom_fields = self._repositories.contacts.get_custom_fields(
                            contact.uuid
                        )
                        field_values = {f.name: f for f in custom_fields}
                        
                        # Create list of all fields, including empty ones
                        all_fields = []
                        for name, definition in definitions.items():
                            if name in field_values:
                                field = field_values[name]
                                # Ensure field has correct type from definition
                                field.type = definition.type
                                all_fields.append(field)
                            else:
                                # Create empty field with correct type from definition
                                all_fields.append(CustomFieldValue(
                                    Name=name,  # Name is required
                                    value=None,
                                    type=definition.type  # Use type from definition
                                ))
                        
                        contact.custom_fields = all_fields
                        
                    except WorkflowMaxError as e:
                        logger.warning(
                            f"Failed to get custom fields for contact {contact.uuid}",
                            error=str(e)
                        )
            
            return contacts
    
    @with_logging
    def get_contact_with_field(
        self,
        uuid: str,
        field_name: str
    ) -> tuple[Contact, Optional[str]]:
        """Get contact and specific custom field value.
        
        Args:
            uuid: Contact UUID
            field_name: Custom field name
            
        Returns:
            Tuple of (Contact, field_value)
            
        Raises:
            ResourceNotFoundError: If contact not found
            WorkflowMaxError: If API request fails
        """
        with Timer("Get contact with field"):
            # Get contact with custom fields
            contact = self.get_contact(uuid, include_custom_fields=True)
            
            # Find requested field
            field_value = contact.get_custom_field_value(field_name)
            
            # Extract URL from LinkURL tags if present
            if field_name == self.LINKEDIN_FIELD and field_value:
                if field_value.startswith('<LinkURL>') and field_value.endswith('</LinkURL>'):
                    field_value = field_value[9:-10]  # Remove tags
            
            return contact, field_value
    
    @with_logging
    def validate_custom_fields(
        self,
        fields: Dict[str, str]
    ) -> List[str]:
        """Validate custom field values.
        
        Args:
            fields: Dictionary mapping field names to values
            
        Returns:
            List of validation error messages (empty if all valid)
            
        Raises:
            WorkflowMaxError: If API request fails
        """
        return self._repositories.custom_fields.validate_fields(fields)
