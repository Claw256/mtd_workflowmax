"""Repository for managing WorkflowMax contacts."""

from typing import Optional, List, Dict, Any, Union, Tuple
import xml.etree.ElementTree as ET
from datetime import datetime
import re

from ..core.exceptions import (
    ResourceNotFoundError,
    ValidationError,
    XMLParsingError,
    WorkflowMaxError,
    ContactNotFoundError,
    CustomFieldError
)
from ..core.logging import get_logger, with_logging
from ..core.utils import Timer
from ..models import Contact, CustomFieldValue, CustomFieldType, Position
from ..config import config
from .custom_field_repository import CustomFieldRepository

logger = get_logger('workflowmax.repositories.contact')

class ContactRepository:
    """Repository for contact operations."""
    
    def __init__(self, api_client, custom_fields: Optional[CustomFieldRepository] = None):
        """Initialize repository.
        
        Args:
            api_client: Initialized API client instance
            custom_fields: Optional custom fields repository
        """
        self.api_client = api_client
        self.custom_fields = custom_fields
        logger.debug("Initialized ContactRepository")
    
    @with_logging
    def get_by_uuid(self, uuid: str) -> Contact:
        """Get contact by UUID.
        
        Args:
            uuid: Contact UUID
            
        Returns:
            Contact instance
            
        Raises:
            ContactNotFoundError: If contact not found
            WorkflowMaxError: If API request fails
        """
        with Timer("Get contact by UUID"):
            logger.debug(f"Fetching contact with UUID: {uuid}")
            
            try:
                response = self.api_client.get(f'client.api/contact/{uuid}')
                
                # Log the response text for debugging
                logger.debug(f"Raw API response: {response.text}")
                
                xml_root = ET.fromstring(response.text.encode('utf-8'))
                contact_wrapper = xml_root.find('.//Contact')
                if contact_wrapper is None:
                    logger.error("Contact not found in response")
                    raise ContactNotFoundError(f"Contact {uuid} not found")
                    
                contact = Contact.from_xml(contact_wrapper)
                logger.debug(f"Successfully parsed contact: {contact.name}")
                return contact
                
            except ResourceNotFoundError:
                raise ContactNotFoundError(f"Contact {uuid} not found")
            except Exception as e:
                logger.error(f"Failed to get contact: {str(e)}", exc_info=True)
                raise WorkflowMaxError(f"Failed to get contact: {str(e)}")
    
    @with_logging
    def get_custom_fields(self, uuid: str) -> List[CustomFieldValue]:
        """Get custom fields for contact.
        
        Args:
            uuid: Contact UUID
            
        Returns:
            List of custom field values
            
        Raises:
            ContactNotFoundError: If contact not found
            WorkflowMaxError: If API request fails
        """
        with Timer("Get contact custom fields"):
            logger.debug(f"Fetching custom fields for contact: {uuid}")
            
            try:
                # Get current custom field values
                response = self.api_client.get(f'client.api/contact/{uuid}/customfield')
                logger.debug(f"Raw custom fields response: {response.text}")
                
                xml_root = ET.fromstring(response.text.encode('utf-8'))
                
                # Check response status
                status = xml_root.find('Status')
                if status is not None and status.text != 'OK':
                    raise WorkflowMaxError(f"Failed to get custom fields: {status.text}")
                
                # Get field definitions to determine types
                definitions = {}
                if self.custom_fields:
                    # Only include fields that can be used on contacts
                    definitions = {
                        d.name: d for d in self.custom_fields.get_definitions()
                        if d.use_contact
                    }
                    logger.debug(f"Found {len(definitions)} contact field definitions")
                
                # Create list of all fields, including empty ones
                custom_fields = []
                for name, definition in definitions.items():
                    field = CustomFieldValue(
                        name=name,
                        type=definition.type,
                        value=None  # Default to None, will be updated if value found
                    )
                    custom_fields.append(field)
                    logger.debug(f"Added empty field: {name} ({definition.type})")
                
                # Update fields with actual values from response
                custom_fields_elem = xml_root.find('CustomFields')
                if custom_fields_elem is not None:
                    for field_elem in custom_fields_elem.findall('CustomField'):
                        try:
                            name = self._get_text(field_elem, 'Name')
                            if not name:
                                logger.warning("Skipping custom field with no name")
                                continue
                            
                            # Find matching field
                            for field in custom_fields:
                                if field.name == name:
                                    # Get value based on field type
                                    if field.type == CustomFieldType.BOOLEAN:
                                        value = self._get_text(field_elem, 'Boolean')
                                        field.value = value.lower() if value else None
                                    elif field.type == CustomFieldType.DATE:
                                        value = self._get_text(field_elem, 'Date')
                                        if value:
                                            try:
                                                dt = datetime.strptime(value, '%Y%m%d')
                                                field.value = dt.strftime('%Y-%m-%d')
                                            except ValueError:
                                                field.value = value
                                    elif field.type == CustomFieldType.NUMBER:
                                        value = self._get_text(field_elem, 'Number')
                                        field.value = str(int(float(value))) if value else None
                                    elif field.type == CustomFieldType.DECIMAL:
                                        value = self._get_text(field_elem, 'Decimal')
                                        field.value = str(float(value)) if value else None
                                    elif field.type == CustomFieldType.LINK:
                                        value = self._get_text(field_elem, 'LinkURL')
                                        field.value = value
                                    else:
                                        value = self._get_text(field_elem, 'Value')
                                        field.value = value
                                    
                                    logger.debug(f"Updated field {name} = {field.value} ({field.type})")
                                    break
                            
                        except Exception as e:
                            logger.warning(f"Failed to parse custom field: {str(e)}")
                            continue
                
                logger.debug(f"Found {len(custom_fields)} custom fields")
                return custom_fields
                
            except ResourceNotFoundError:
                raise ContactNotFoundError(f"Contact {uuid} not found")
            except Exception as e:
                logger.error(f"Failed to get custom fields: {str(e)}", exc_info=True)
                raise WorkflowMaxError(f"Failed to get custom fields: {str(e)}")
    
    @with_logging
    def update_custom_fields(self, uuid: str, updates: Dict[str, Union[str, Dict[str, str]]]) -> bool:
        """Update custom fields for contact.
        
        Args:
            uuid: Contact UUID
            updates: Dictionary mapping field names to values or value dicts
            
        Returns:
            True if update successful
            
        Raises:
            ContactNotFoundError: If contact not found
            ValidationError: If field validation fails
            WorkflowMaxError: If API request fails
        """
        with Timer("Update contact custom fields"):
            logger.debug(f"Updating custom fields for contact {uuid}: {updates}")
            
            try:
                # Get field definitions for type information
                definitions = {}
                if self.custom_fields:
                    definitions = {
                        d.name: d for d in self.custom_fields.get_definitions()
                        if d.use_contact
                    }
                
                # Create XML payload
                root = ET.Element('CustomFields')
                
                # Process each field in updates
                for field_name, field_value in updates.items():
                    field = ET.SubElement(root, 'CustomField')
                    
                    # Extract type and value if dict provided
                    field_type = None
                    if isinstance(field_value, dict):
                        field_type = field_value.get('type')
                        field_value = field_value.get('value', '')
                    
                    # Get field type from definition if available
                    if not field_type and field_name in definitions:
                        field_type = definitions[field_name].type
                    
                    # Default to TEXT type if still not determined
                    if not field_type:
                        field_type = CustomFieldType.TEXT
                    
                    # Add field elements
                    name_elem = ET.SubElement(field, 'Name')
                    name_elem.text = field_name
                    
                    # Add type element
                    type_elem = ET.SubElement(field, 'Type')
                    type_elem.text = field_type.value
                    
                    # Add value using appropriate element based on type
                    if field_type == CustomFieldType.BOOLEAN:
                        value_elem = ET.SubElement(field, 'Boolean')
                        value_elem.text = str(field_value).lower()
                    elif field_type == CustomFieldType.DATE:
                        value_elem = ET.SubElement(field, 'Date')
                        if field_value:
                            try:
                                dt = datetime.strptime(field_value, '%Y-%m-%d')
                                value_elem.text = dt.strftime('%Y-%m-%d %H:%M:%S+00:00')
                            except ValueError:
                                value_elem.text = field_value
                    elif field_type == CustomFieldType.NUMBER:
                        value_elem = ET.SubElement(field, 'Number')
                        value_elem.text = str(int(float(field_value))) if field_value else ''
                    elif field_type == CustomFieldType.DECIMAL:
                        value_elem = ET.SubElement(field, 'Decimal')
                        value_elem.text = str(float(field_value)) if field_value else ''
                    elif field_type == CustomFieldType.LINK:
                        value_elem = ET.SubElement(field, 'LinkURL')
                        # Add https:// prefix if not present
                        if field_value and not field_value.startswith(('http://', 'https://', 'www.')):
                            field_value = 'https://' + field_value
                        value_elem.text = field_value
                    else:
                        value_elem = ET.SubElement(field, 'Value')
                        value_elem.text = field_value
                
                # Convert to string
                xml_payload = ET.tostring(root, encoding='unicode')
                logger.debug(f"Update custom fields payload: {xml_payload}")
                
                # Send update request
                response = self.api_client.put(f'client.api/contact/{uuid}/customfield', data=xml_payload)
                logger.debug(f"Update response: {response.text}")
                
                xml_root = ET.fromstring(response.text.encode('utf-8'))
                status_elem = xml_root.find('Status')
                
                if status_elem is not None and status_elem.text == 'OK':
                    logger.info(f"Successfully updated {len(updates)} custom fields")
                    return True
                else:
                    raise WorkflowMaxError(f"Failed to update custom fields: {status_elem.text if status_elem else 'Unknown error'}")
                    
            except ResourceNotFoundError:
                raise ContactNotFoundError(f"Contact {uuid} not found")
            except ValueError as e:
                raise ValidationError(f"Invalid field value: {str(e)}")
            except Exception as e:
                logger.error(f"Failed to update custom fields: {str(e)}", exc_info=True)
                raise WorkflowMaxError(f"Failed to update custom fields: {str(e)}")
    
    @with_logging
    def exists(self, uuid: str) -> bool:
        """Check if contact exists.
        
        Args:
            uuid: Contact UUID
            
        Returns:
            True if contact exists
        """
        try:
            self.get_by_uuid(uuid)
            return True
        except ContactNotFoundError:
            return False
        except Exception:
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
        try:
            child = element.find(tag)
            return child.text if child is not None and child.text else default
        except Exception as e:
            logger.warning(f"Error getting text for tag {tag}: {str(e)}")
            return default
