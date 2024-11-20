"""Repository for managing WorkflowMax contacts."""

from typing import Optional, List, Dict, Any, Union, Tuple
import xml.etree.ElementTree as ET
from datetime import datetime

from ..core.exceptions import (
    ResourceNotFoundError,
    ValidationError,
    XMLParsingError,
    WorkflowMaxError,
    ContactNotFoundError,
    CustomFieldError
)
from ..core.logging import get_logger, with_logging
from ..core.utils import Timer, get_xml_text
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
                status = get_xml_text(xml_root, 'Status')
                if status != 'OK':
                    raise WorkflowMaxError(f"Failed to get custom fields: {status}")
                
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
                        uuid=definition.uuid,
                        name=name,
                        type=definition.type,
                        value=None,  # Default to None, will be updated if value found
                        link_url=definition.link_url  # Pass link_url template from definition
                    )
                    custom_fields.append(field)
                    logger.debug(f"Added empty field: {name} ({definition.type})")
                
                # Update fields with actual values from response
                custom_fields_elem = xml_root.find('CustomFields')
                if custom_fields_elem is not None:
                    for field_elem in custom_fields_elem.findall('CustomField'):
                        try:
                            name = get_xml_text(field_elem, 'Name')
                            if not name:
                                logger.warning("Skipping custom field with no name")
                                continue
                            
                            # Find matching field and update its value
                            for field in custom_fields:
                                if field.name == name:
                                    # Get value based on field type
                                    if field.type == CustomFieldType.BOOLEAN:
                                        value = get_xml_text(field_elem, 'Boolean')
                                        field.value = value.lower() if value else None
                                    elif field.type == CustomFieldType.DATE:
                                        value = get_xml_text(field_elem, 'Date')
                                        if value:
                                            try:
                                                dt = datetime.strptime(value, '%Y%m%d')
                                                field.value = dt.strftime('%Y-%m-%d')
                                            except ValueError:
                                                field.value = value
                                    elif field.type == CustomFieldType.NUMBER:
                                        value = get_xml_text(field_elem, 'Number')
                                        field.value = str(int(float(value))) if value else None
                                    elif field.type == CustomFieldType.DECIMAL:
                                        value = get_xml_text(field_elem, 'Decimal')
                                        field.value = str(float(value)) if value else None
                                    elif field.type == CustomFieldType.LINK:
                                        field.value = get_xml_text(field_elem, 'LinkURL')
                                    else:
                                        field.value = get_xml_text(field_elem, 'Value')
                                    
                                    logger.debug(f"Updated field {field.name} = {field.value} ({field.type})")
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
    def update_custom_fields(self, uuid: str, updates: Dict[str, str]) -> bool:
        """Update custom fields for contact.
        
        Args:
            uuid: Contact UUID
            updates: Dictionary mapping field names to values
            
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
                # Get current custom field values
                response = self.api_client.get(f'client.api/contact/{uuid}/customfield')
                logger.debug(f"Raw custom fields response: {response.text}")
                
                xml_root = ET.fromstring(response.text.encode('utf-8'))
                
                # Check response status
                status = get_xml_text(xml_root, 'Status')
                if status != 'OK':
                    raise WorkflowMaxError(f"Failed to get custom fields: {status}")
                
                # Get field definitions
                definitions = {}
                if self.custom_fields:
                    definitions = {
                        d.name: d for d in self.custom_fields.get_definitions()
                        if d.use_contact
                    }
                
                # Create XML payload
                root = ET.Element('CustomFields')
                
                # Add fields being updated
                for field_name, field_value in updates.items():
                    # Get field definition if available
                    definition = definitions.get(field_name)
                    field_type = definition.type if definition else CustomFieldType.TEXT
                    link_url = definition.link_url if definition else None
                    
                    logger.debug(f"Creating field value: name={field_name} type={field_type} value={field_value} link_url={link_url}")
                    
                    # Create CustomFieldValue instance
                    field = CustomFieldValue(
                        uuid=definition.uuid if definition else None,
                        name=field_name,
                        type=field_type,
                        value=field_value,
                        link_url=link_url
                    )
                    
                    # Convert to XML and append to root
                    field_xml = field.to_xml()
                    logger.debug(f"Field XML before parsing: {field_xml}")
                    field_elem = ET.fromstring(field_xml)
                    root.append(field_elem)
                
                # Add existing fields that aren't being updated
                custom_fields_elem = xml_root.find('CustomFields')
                if custom_fields_elem is not None:
                    for field_elem in custom_fields_elem.findall('CustomField'):
                        name = get_xml_text(field_elem, 'Name')
                        if name and name not in updates:
                            # Copy field as-is
                            root.append(field_elem)
                
                # Convert to string
                xml_payload = ET.tostring(root, encoding='unicode')
                logger.debug(f"Update custom fields request XML: {xml_payload}")
                
                # Send update request
                response = self.api_client.put(f'client.api/contact/{uuid}/customfield', data=xml_payload)
                logger.debug(f"Update response: {response.text}")
                
                xml_root = ET.fromstring(response.text.encode('utf-8'))
                status = get_xml_text(xml_root, 'Status')
                
                if status == 'OK':
                    logger.info(f"Successfully updated {len(updates)} custom fields")
                    return True
                else:
                    raise WorkflowMaxError(f"Failed to update custom fields: {status or 'Unknown error'}")
                    
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
