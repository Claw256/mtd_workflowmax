"""Service for managing WorkflowMax custom fields."""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..core.exceptions import (
    ValidationError,
    ResourceNotFoundError,
    WorkflowMaxError
)
from ..core.logging import get_logger, with_logging
from ..core.utils import Timer
from ..models import CustomFieldDefinition, CustomFieldType, CustomFieldValue
from ..repositories import Repositories
from ..config import config

logger = get_logger('workflowmax.services.custom_field')

class EntityType(str, Enum):
    """Entity types that can have custom fields."""
    
    CLIENT = "client"
    CONTACT = "contact"
    SUPPLIER = "supplier"
    JOB = "job"
    LEAD = "lead"
    JOB_TASK = "job_task"
    JOB_COST = "job_cost"
    JOB_TIME = "job_time"
    QUOTE = "quote"

class CustomFieldService:
    """Service for custom field operations."""
    
    def __init__(self, repositories: Repositories):
        """Initialize custom field service.
        
        Args:
            repositories: Initialized repositories instance
        """
        self._repositories = repositories
    
    @with_logging
    def get_field_definitions(
        self,
        force_refresh: bool = False
    ) -> List[CustomFieldDefinition]:
        """Get all custom field definitions.
        
        Args:
            force_refresh: Whether to force refresh cached definitions
            
        Returns:
            List of field definitions
            
        Raises:
            WorkflowMaxError: If API request fails
        """
        with Timer("Get field definitions"):
            return self._repositories.custom_fields.get_definitions(force_refresh)
    
    @with_logging
    def get_field_definition(
        self,
        field_name: str,
        force_refresh: bool = False
    ) -> Optional[CustomFieldDefinition]:
        """Get definition for specific field.
        
        Args:
            field_name: Name of the field
            force_refresh: Whether to force refresh cached definitions
            
        Returns:
            Field definition if found
            
        Raises:
            WorkflowMaxError: If API request fails
        """
        with Timer("Get field definition"):
            if force_refresh:
                self._repositories.custom_fields.clear_cache()
            return self._repositories.custom_fields.get_definition(field_name)
    
    @with_logging
    def validate_field_value(
        self,
        field_name: str,
        field_value: str
    ) -> List[str]:
        """Validate field value.
        
        Args:
            field_name: Name of the field
            field_value: Value to validate
            
        Returns:
            List of validation error messages (empty if valid)
            
        Raises:
            WorkflowMaxError: If API request fails
        """
        with Timer("Validate field value"):
            try:
                self._repositories.custom_fields.validate_field_value(
                    field_name,
                    field_value
                )
                return []
            except ValidationError as e:
                return [str(e)]
    
    @with_logging
    def validate_fields(
        self,
        fields: Dict[str, str]
    ) -> List[str]:
        """Validate multiple field values.
        
        Args:
            fields: Dictionary mapping field names to values
            
        Returns:
            List of validation error messages (empty if all valid)
            
        Raises:
            WorkflowMaxError: If API request fails
        """
        with Timer("Validate fields"):
            return self._repositories.custom_fields.validate_fields(fields)
    
    @with_logging
    def get_field_values_for_contacts(
        self,
        contact_uuids: List[str],
        field_names: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, str]]:
        """Get custom field values for multiple contacts.
        
        Args:
            contact_uuids: List of contact UUIDs
            field_names: Optional list of specific fields to get
            
        Returns:
            Dictionary mapping contact UUIDs to field values
            Format: {contact_uuid: {field_name: field_value}}
            
        Raises:
            WorkflowMaxError: If API request fails
        """
        with Timer("Get field values for contacts"):
            result = {}
            
            for uuid in contact_uuids:
                try:
                    # Get all custom fields for contact
                    custom_fields = self._repositories.contacts.get_custom_fields(uuid)
                    
                    # Filter fields if specific ones requested
                    if field_names:
                        field_values = {
                            field.name: field.value
                            for field in custom_fields
                            if field.name in field_names
                        }
                    else:
                        field_values = {
                            field.name: field.value
                            for field in custom_fields
                        }
                    
                    result[uuid] = field_values
                    
                except WorkflowMaxError as e:
                    logger.warning(
                        f"Failed to get custom fields for contact {uuid}",
                        error=str(e)
                    )
                    result[uuid] = {}
            
            return result
    
    @with_logging
    def update_field_values(
        self,
        updates: Dict[str, Dict[str, str]],
        validate: bool = True
    ) -> Dict[str, List[str]]:
        """Update custom field values for multiple contacts.
        
        Args:
            updates: Dictionary mapping contact UUIDs to field updates
                    Format: {contact_uuid: {field_name: field_value}}
            validate: Whether to validate values against field definitions
            
        Returns:
            Dictionary mapping contact UUIDs to error messages
            
        Raises:
            WorkflowMaxError: If API request fails
        """
        with Timer("Update field values"):
            results = {}
            
            for uuid, fields in updates.items():
                try:
                    # Validate contact exists
                    if not self._repositories.contacts.exists(uuid):
                        results[uuid] = [f"Contact {uuid} not found"]
                        continue
                    
                    # Validate fields if requested
                    if validate:
                        errors = self.validate_fields(fields)
                        if errors:
                            results[uuid] = errors
                            continue
                    
                    # Update fields
                    success = self._repositories.contacts.update_custom_fields(
                        uuid,
                        fields
                    )
                    
                    if not success:
                        results[uuid] = ["Failed to update custom fields"]
                    else:
                        results[uuid] = []
                        
                except WorkflowMaxError as e:
                    results[uuid] = [str(e)]
            
            return results

    @with_logging
    def update_field(
        self,
        contact_uuid: str,
        field_name: str,
        field_value: str,
        validate: bool = True
    ) -> bool:
        """Update a single custom field value.
        
        Args:
            contact_uuid: UUID of the contact
            field_name: Name of the field to update
            field_value: New value for the field
            validate: Whether to validate value against field definition
            
        Returns:
            True if update was successful
            
        Raises:
            WorkflowMaxError: If API request fails
            ValidationError: If validation fails
        """
        with Timer("Update field"):
            # Validate field value if requested
            if validate:
                errors = self.validate_field_value(field_name, field_value)
                if errors:
                    raise ValidationError(errors[0])
            
            # Update single field
            return self._repositories.contacts.update_custom_fields(
                contact_uuid,
                {field_name: field_value}
            )
    
    @with_logging
    def get_field_statistics(
        self,
        field_name: str,
        page_size: int = 100
    ) -> Dict[str, int]:
        """Get statistics for a custom field.
        
        Args:
            field_name: Name of the field
            page_size: Number of contacts to process per page
            
        Returns:
            Dictionary of value frequencies
            
        Raises:
            ValidationError: If field not found
            WorkflowMaxError: If API request fails
        """
        with Timer("Get field statistics"):
            # Verify field exists
            if not self.get_field_definition(field_name):
                raise ValidationError(f"Custom field '{field_name}' not found")
            
            stats = {}
            page = 1
            
            while True:
                # Get batch of contacts
                contacts = self._repositories.contacts.search(
                    page=page,
                    page_size=page_size
                )
                
                if not contacts:
                    break
                
                # Process contacts
                for contact in contacts:
                    try:
                        custom_fields = self._repositories.contacts.get_custom_fields(
                            contact.uuid
                        )
                        
                        for field in custom_fields:
                            if field.name == field_name:
                                value = field.value or 'None'
                                stats[value] = stats.get(value, 0) + 1
                                break
                                
                    except WorkflowMaxError as e:
                        logger.warning(
                            f"Failed to get custom fields for contact {contact.uuid}",
                            error=str(e)
                        )
                
                page += 1
            
            return stats

    def print_fields(
        self,
        fields: List[CustomFieldValue],
        entity_type: EntityType = EntityType.CONTACT,
        indent: int = 0
    ) -> None:
        """Print custom fields with proper formatting.
        
        Args:
            fields: List of custom field values
            entity_type: Type of entity the fields belong to
            indent: Indentation level
        """
        with Timer("Get field definitions"):
            # Get all field definitions that are valid for the entity type
            definitions = {
                d.name: d for d in self.get_field_definitions()
                if self._is_field_valid_for_entity(d, entity_type)
            }
        
        # Create value map for quick lookup
        field_values = {
            field.name: field.value
            for field in fields
        }
        
        # Print fields that are valid for the entity type
        print("\nCustom Fields:")
        for name, definition in definitions.items():
            value = field_values.get(name, '')
            if not value and definition.type == CustomFieldType.CHECKBOX:
                value = 'false'
                
            print(f"{' ' * indent}{name} ({definition.type.value}): {value}")
            
    def _is_field_valid_for_entity(
        self,
        definition: CustomFieldDefinition,
        entity_type: EntityType
    ) -> bool:
        """Check if field is valid for entity type.
        
        Args:
            definition: Field definition
            entity_type: Entity type to check
            
        Returns:
            True if field is valid for entity type
        """
        if entity_type == EntityType.CLIENT:
            return definition.use_client
        elif entity_type == EntityType.CONTACT:
            return definition.use_contact
        elif entity_type == EntityType.SUPPLIER:
            return definition.use_supplier
        elif entity_type == EntityType.JOB:
            return definition.use_job
        elif entity_type == EntityType.LEAD:
            return definition.use_lead
        elif entity_type == EntityType.JOB_TASK:
            return definition.use_job_task
        elif entity_type == EntityType.JOB_COST:
            return definition.use_job_cost
        elif entity_type == EntityType.JOB_TIME:
            return definition.use_job_time
        elif entity_type == EntityType.QUOTE:
            return definition.use_quote
        return False
