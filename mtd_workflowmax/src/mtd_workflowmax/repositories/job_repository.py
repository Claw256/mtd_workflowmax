"""Repository for managing WorkflowMax jobs."""

from typing import Optional, List, Dict, Any
import xml.etree.ElementTree as ET
from datetime import datetime

from ..core.exceptions import (
    ResourceNotFoundError,
    ValidationError,
    XMLParsingError,
    WorkflowMaxError
)
from ..core.logging import get_logger, with_logging
from ..core.utils import Timer
from ..models import Job, CustomFieldValue, CustomFieldType
from ..config import config
from .custom_field_repository import CustomFieldRepository

logger = get_logger('workflowmax.repositories.job')

class JobRepository:
    """Repository for job operations."""
    
    def __init__(self, api_client, custom_fields: Optional[CustomFieldRepository] = None):
        """Initialize repository.
        
        Args:
            api_client: Initialized API client instance
            custom_fields: Optional custom fields repository
        """
        self.api_client = api_client
        self.custom_fields = custom_fields
    
    @with_logging
    def get_by_uuid(self, uuid: str) -> Job:
        """Get job by UUID.
        
        Args:
            uuid: Job UUID
            
        Returns:
            Job instance
            
        Raises:
            ResourceNotFoundError: If job not found
            WorkflowMaxError: If API request fails
        """
        with Timer("Get job by UUID"):
            response = self.api_client.get(f'job.api/get/{uuid}')
            
            try:
                # Log the response text for debugging
                logger.debug(f"Raw API response: {response.text}")
                
                xml_root = ET.fromstring(response.text.encode('utf-8'))
                job_wrapper = xml_root.find('Job')
                if job_wrapper is None:
                    raise XMLParsingError("Missing Job wrapper element")
                    
                return Job.from_xml(job_wrapper)
                
            except Exception as e:
                logger.error(f"Failed to parse job response: {str(e)}")
                raise XMLParsingError(f"Failed to parse job response: {str(e)}")
    
    @with_logging
    def get_custom_fields(self, uuid: str) -> List[CustomFieldValue]:
        """Get custom fields for job.
        
        Args:
            uuid: Job UUID
            
        Returns:
            List of custom field values
            
        Raises:
            ResourceNotFoundError: If job not found
            WorkflowMaxError: If API request fails
        """
        with Timer("Get job custom fields"):
            response = self.api_client.get(f'job.api/{uuid}/customfield')
            
            try:
                # Log the response text for debugging
                logger.debug(f"Raw custom fields response: {response.text}")
                
                xml_root = ET.fromstring(response.text.encode('utf-8'))
                
                # Get field definitions to determine types
                definitions = {}
                if self.custom_fields:
                    definitions = {
                        d.name: d for d in self.custom_fields.get_definitions()
                        if d.use_job  # Only include fields that can be used on jobs
                    }
                
                custom_fields = []
                custom_fields_elem = xml_root.find('CustomFields')
                if custom_fields_elem is not None:
                    for field_elem in custom_fields_elem.findall('CustomField'):
                        name = self._get_text(field_elem, 'Name')
                        
                        # Get field type from definition
                        field_type = CustomFieldType.TEXT  # Default to TEXT
                        if name in definitions:
                            field_type = definitions[name].type
                        
                        # Get value based on field type
                        if field_type == CustomFieldType.CHECKBOX:
                            value = self._get_text(field_elem, 'Boolean')
                        elif field_type == CustomFieldType.LINK:
                            value = self._get_text(field_elem, 'LinkURL')
                        else:
                            value = self._get_text(field_elem, 'Value')
                        
                        custom_fields.append(CustomFieldValue(
                            Name=name,
                            value=value,
                            type=field_type
                        ))
                        
                return custom_fields
                
            except Exception as e:
                logger.error(f"Failed to parse custom fields response: {str(e)}")
                raise XMLParsingError(f"Failed to parse custom fields response: {str(e)}")
    
    @with_logging
    def update_custom_field(
        self,
        uuid: str,
        field_name: str,
        field_value: str,
        field_type: str
    ) -> bool:
        """Update custom field value.
        
        Args:
            uuid: Job UUID
            field_name: Field name
            field_value: New field value
            field_type: Field type
            
        Returns:
            True if update successful
            
        Raises:
            ResourceNotFoundError: If job not found
            ValidationError: If field validation fails
            WorkflowMaxError: If API request fails
        """
        with Timer("Update job custom field"):
            # Create custom field value
            field = CustomFieldValue(
                Name=field_name,
                value=field_value,
                type=field_type
            )
            
            # Generate XML payload
            xml_payload = field.to_xml()
            
            # Update field
            response = self.api_client.put(
                f'job.api/{uuid}/customfield',
                data=xml_payload
            )
            
            try:
                xml_root = ET.fromstring(response.text.encode('utf-8'))
                status_elem = xml_root.find('Status')
                
                if status_elem is not None and status_elem.text == 'OK':
                    logger.info(
                        f"Successfully updated custom field {field_name}",
                        job_uuid=uuid,
                        field_name=field_name
                    )
                    return True
                    
                logger.error(
                    "Failed to update custom field",
                    job_uuid=uuid,
                    field_name=field_name,
                    response=response.text
                )
                return False
                
            except Exception as e:
                logger.error(f"Failed to parse update response: {str(e)}")
                raise XMLParsingError(f"Failed to parse update response: {str(e)}")
    
    @with_logging
    def update_custom_fields(self, uuid: str, updates: Dict[str, Dict[str, str]]) -> bool:
        """Update multiple custom fields.
        
        Args:
            uuid: Job UUID
            updates: Dictionary mapping field names to update info
                    Format: {field_name: {'value': value, 'type': type}}
            
        Returns:
            True if all updates successful
            
        Raises:
            ResourceNotFoundError: If job not found
            ValidationError: If field validation fails
            WorkflowMaxError: If API request fails
        """
        success = True
        for field_name, field_info in updates.items():
            if not self.update_custom_field(
                uuid,
                field_name,
                field_info['value'],
                field_info['type']
            ):
                success = False
                
        return success
    
    @with_logging
    def search(
        self,
        query: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> List[Job]:
        """Search for jobs.
        
        Args:
            query: Optional search query
            page: Page number (1-based)
            page_size: Results per page
            
        Returns:
            List of jobs matching criteria
            
        Raises:
            ValidationError: If invalid parameters
            WorkflowMaxError: If API request fails
        """
        with Timer("Search jobs"):
            # Validate parameters
            if page < 1:
                raise ValidationError("Page must be >= 1")
            if page_size < 1:
                raise ValidationError("Page size must be >= 1")
            
            # Build query parameters
            params = {
                'detailed': 'true',
                'page': str(page),
                'pageSize': str(page_size)
            }
            if query:
                params['query'] = query
                
            # Log request parameters
            logger.debug(f"Searching jobs with params: {params}")
                
            # Search through jobs endpoint
            response = self.api_client.get('job.api/list', params=params)
            
            try:
                # Log raw response for debugging
                logger.debug(f"Raw search response: {response.text}")
                
                xml_root = ET.fromstring(response.text.encode('utf-8'))
                jobs = []
                
                # Extract jobs from response
                jobs_elem = xml_root.find('Jobs')
                if jobs_elem is not None:
                    for job_elem in jobs_elem.findall('Job'):
                        jobs.append(Job.from_xml(job_elem))
                        
                return jobs
                
            except Exception as e:
                logger.error(f"Failed to parse search response: {str(e)}")
                raise XMLParsingError(f"Failed to parse search response: {str(e)}")
    
    @with_logging
    def exists(self, uuid: str) -> bool:
        """Check if job exists.
        
        Args:
            uuid: Job UUID
            
        Returns:
            True if job exists
        """
        try:
            self.get_by_uuid(uuid)
            return True
        except (ResourceNotFoundError, WorkflowMaxError):
            return False
            
    @staticmethod
    def _get_text(element: ET.Element, tag: str, default: Optional[str] = None) -> Optional[str]:
        """Get text content of an XML element.
        
        Args:
            element: Parent XML element
            tag: Tag name to find
            default: Default value if tag not found
            
        Returns:
            Text content or default value
        """
        child = element.find(tag)
        return child.text if child is not None else default
