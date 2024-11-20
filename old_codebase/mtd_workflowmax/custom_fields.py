"""Custom field management for WorkflowMax API."""

from typing import Dict, List, Any, Optional
import xml.etree.ElementTree as ET
from .xml_parser import XMLParser
from .api_client import APIClient
from .exceptions import WorkflowMaxAPIError
from .logging_config import get_logger

logger = get_logger('workflowmax.custom_fields')

class CustomFieldManager:
    """Manages custom field operations for WorkflowMax contacts."""
    
    def __init__(self, api_client: APIClient):
        """Initialize with API client.
        
        Args:
            api_client: Initialized APIClient instance
        """
        self.api_client = api_client
        self._definitions: Optional[List[Dict[str, str]]] = None
        self._definitions_map: Dict[str, Dict[str, str]] = {}

    def get_definitions(self, force_refresh: bool = False) -> List[Dict[str, str]]:
        """Get all custom field definitions.
        
        Args:
            force_refresh: Whether to force refresh cached definitions
            
        Returns:
            List[Dict[str, str]]: List of field definitions
            
        Raises:
            WorkflowMaxAPIError: If API request fails
        """
        if self._definitions is None or force_refresh:
            logger.info("Fetching custom field definitions")
            response = self.api_client.get('customfield.api/definition')
            logger.info(f"Custom field definitions API response status: {response.status_code}")
            
            if not response.ok:
                logger.error(f"Failed to fetch custom field definitions: {response.status_code}")
                raise WorkflowMaxAPIError(f"Failed to fetch custom field definitions: {response.status_code}")
                
            definitions_xml = ET.fromstring(response.text.encode('utf-8'))
            self._definitions = XMLParser.parse_custom_field_definitions(definitions_xml)
            
            # Update definitions map
            self._definitions_map = {d['Name']: d for d in self._definitions}
            
            logger.info(f"Found {len(self._definitions)} custom field definitions")
            
        return self._definitions

    def get_definition(self, field_name: str) -> Optional[Dict[str, str]]:
        """Get definition for a specific field.
        
        Args:
            field_name: Name of the field
            
        Returns:
            Optional[Dict[str, str]]: Field definition if found
        """
        if not self._definitions_map:
            self.get_definitions()
        return self._definitions_map.get(field_name)

    def get_contact_fields(self, contact_uuid: str) -> List[Dict[str, Any]]:
        """Get custom fields for a contact.
        
        Args:
            contact_uuid: UUID of the contact
            
        Returns:
            List[Dict[str, Any]]: List of custom fields
            
        Raises:
            WorkflowMaxAPIError: If API request fails
        """
        logger.info(f"Fetching custom fields for contact {contact_uuid}")
        response = self.api_client.get(f'client.api/contact/{contact_uuid}/customfield')
        logger.info(f"Custom fields API response status: {response.status_code}")
        
        if not response.ok:
            logger.error(f"Failed to fetch custom fields: {response.status_code}")
            raise WorkflowMaxAPIError(f"Failed to fetch custom fields: {response.status_code}")
            
        custom_fields_xml = ET.fromstring(response.text.encode('utf-8'))
        XMLParser.check_response(custom_fields_xml)
        
        custom_fields = []
        custom_fields_elem = custom_fields_xml.find('CustomFields')
        if custom_fields_elem is not None:
            for field_elem in custom_fields_elem.findall('CustomField'):
                field = XMLParser.parse_custom_field_value(field_elem)
                if field.get('Name'):  # Only add fields with a name
                    custom_fields.append(field)
                    logger.debug(f"Parsed custom field: {field}")
                    
        return custom_fields

    def update_field(self, contact_uuid: str, field_name: str, field_value: str) -> bool:
        """Update a custom field value.
        
        Args:
            contact_uuid: UUID of the contact
            field_name: Name of the field to update
            field_value: New value for the field
            
        Returns:
            bool: True if update was successful
            
        Raises:
            WorkflowMaxAPIError: If API request fails
            ValueError: If field definition is invalid
        """
        # Get field definition
        field_def = self.get_definition(field_name)
        if not field_def:
            logger.error(f"Custom field '{field_name}' not found in definitions")
            return False
            
        # Generate XML payload
        try:
            xml_payload = XMLParser.generate_custom_field_xml(field_name, field_value, field_def)
        except ValueError as e:
            logger.error(f"Failed to generate custom field XML: {str(e)}")
            raise
            
        logger.info(f"Updating custom field '{field_name}' for contact {contact_uuid}")
        logger.debug(f"Update payload:\n{xml_payload}")
        
        # Update custom field
        response = self.api_client.put(f'client.api/contact/{contact_uuid}/customfield', data=xml_payload)
        logger.info(f"Update API response status: {response.status_code}")
        
        if not response.ok:
            logger.error(f"Failed to update custom field: {response.status_code}")
            return False
            
        # Parse response and check status
        response_xml = ET.fromstring(response.text.encode('utf-8'))
        try:
            XMLParser.check_response(response_xml)
            logger.info(f"Successfully updated custom field '{field_name}' for contact {contact_uuid}")
            return True
        except WorkflowMaxAPIError:
            return False

    def update_fields(self, contact_uuid: str, updates: Dict[str, str]) -> bool:
        """Update multiple custom fields.
        
        Args:
            contact_uuid: UUID of the contact
            updates: Dictionary mapping field names to new values
            
        Returns:
            bool: True if all updates were successful
        """
        success = True
        for field_name, field_value in updates.items():
            if not self.update_field(contact_uuid, field_name, field_value):
                success = False
        return success

    def print_fields(self, fields: List[Dict[str, Any]], indent: int = 0) -> None:
        """Print custom fields with proper formatting.
        
        Args:
            fields: List of custom field dictionaries
            indent: Indentation level
        """
        # Get definitions if not already loaded
        if not self._definitions_map:
            self.get_definitions()
            
        # Create a map of field values by name
        field_values = {field['Name']: field for field in fields}
        
        # Print all defined fields, using empty string for undefined ones
        for field_def in self._definitions:
            field_name = field_def['Name']
            field_type = field_def['Type']
            
            if field_name in field_values:
                field_value = field_values[field_name]['Value']
            else:
                # For boolean fields, show false by default
                field_value = 'false' if field_type == 'Checkbox' else ''
                
            print(f"{' ' * indent}{field_name} ({field_type}): {field_value}")
