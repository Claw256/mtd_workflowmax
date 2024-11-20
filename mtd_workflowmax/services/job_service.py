"""Service for managing WorkflowMax jobs."""

from typing import Optional, List, Dict, Any
from datetime import datetime

from ..core.exceptions import (
    ValidationError,
    ResourceNotFoundError,
    WorkflowMaxError
)
from ..core.logging import get_logger, with_logging
from ..core.utils import Timer
from ..models import Job, CustomFieldValue, CustomFieldType
from ..repositories import repositories
from ..config import config

logger = get_logger('workflowmax.services.job')

class JobService:
    """Service for job operations."""
    
    @with_logging
    def get_job(self, uuid: str, include_custom_fields: bool = True) -> Job:
        """Get job by UUID with optional custom fields.
        
        Args:
            uuid: Job UUID
            include_custom_fields: Whether to include custom fields
            
        Returns:
            Job instance
            
        Raises:
            ResourceNotFoundError: If job not found
            WorkflowMaxError: If API request fails
        """
        with Timer("Get job"):
            # Get basic job info
            job = repositories.jobs.get_by_uuid(uuid)
            
            # Add custom fields if requested
            if include_custom_fields:
                # Get field definitions
                definitions = {
                    d.name: d for d in repositories.custom_fields.get_definitions()
                    if d.use_job  # Only include fields that can be used on jobs
                }
                
                # Get current field values
                custom_fields = repositories.jobs.get_custom_fields(uuid)
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
                
                job.custom_fields = all_fields
                
            return job
    
    @with_logging
    def update_custom_fields(
        self,
        uuid: str,
        updates: Dict[str, str],
        validate: bool = True
    ) -> bool:
        """Update job custom fields.
        
        Args:
            uuid: Job UUID
            updates: Dictionary mapping field names to new values
            validate: Whether to validate values against field definitions
            
        Returns:
            True if all updates successful
            
        Raises:
            ResourceNotFoundError: If job not found
            ValidationError: If validation fails
            WorkflowMaxError: If API request fails
        """
        with Timer("Update job custom fields"):
            # Verify job exists
            if not repositories.jobs.exists(uuid):
                raise ResourceNotFoundError('Job', uuid)
            
            # Get field definitions if validation requested
            if validate:
                definitions = {
                    d.name: d for d in repositories.custom_fields.get_definitions()
                    if d.use_job  # Only include fields that can be used on jobs
                }
                
                # Validate each field
                errors = []
                for field_name, field_value in updates.items():
                    if field_name not in definitions:
                        errors.append(f"Custom field '{field_name}' not found or not valid for jobs")
                        continue
                        
                    try:
                        repositories.custom_fields.validate_field_value(
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
                
                # Prepare updates with field types
                typed_updates = {
                    name: {
                        'value': value,
                        'type': definitions[name].type.value
                    }
                    for name, value in updates.items()
                }
            else:
                # Without validation, assume all fields are text type
                typed_updates = {
                    name: {
                        'value': value,
                        'type': CustomFieldType.TEXT.value
                    }
                    for name, value in updates.items()
                }
            
            # Perform updates
            return repositories.jobs.update_custom_fields(uuid, typed_updates)
    
    @with_logging
    def search_jobs(
        self,
        query: Optional[str] = None,
        include_custom_fields: bool = False,
        page: int = 1,
        page_size: int = 50
    ) -> List[Job]:
        """Search for jobs with optional custom fields.
        
        Args:
            query: Optional search query
            include_custom_fields: Whether to include custom fields
            page: Page number (1-based)
            page_size: Results per page
            
        Returns:
            List of jobs matching criteria
            
        Raises:
            ValidationError: If invalid parameters
            WorkflowMaxError: If API request fails
        """
        with Timer("Search jobs"):
            # Search for jobs
            jobs = repositories.jobs.search(query, page, page_size)
            
            # Add custom fields if requested
            if include_custom_fields and jobs:
                # Get field definitions
                definitions = {
                    d.name: d for d in repositories.custom_fields.get_definitions()
                    if d.use_job  # Only include fields that can be used on jobs
                }
                
                for job in jobs:
                    try:
                        # Get current field values
                        custom_fields = repositories.jobs.get_custom_fields(
                            job.uuid
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
                        
                        job.custom_fields = all_fields
                        
                    except WorkflowMaxError as e:
                        logger.warning(
                            f"Failed to get custom fields for job {job.uuid}",
                            error=str(e)
                        )
            
            return jobs
