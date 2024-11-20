"""Data models for WorkflowMax API."""

from typing import Optional, Dict, List, Any, Union
import xml.etree.ElementTree as ET
from .xml_parser import XMLParser
from .exceptions import WorkflowMaxAPIError
from .logging_config import get_logger

logger = get_logger('workflowmax.models')

class Contact:
    """Represents a WorkflowMax contact."""
    
    def __init__(self, xml_element: ET.Element):
        """Initialize a Contact from an XML element.
        
        Args:
            xml_element: The XML element containing contact data
            
        Raises:
            ValueError: If required fields are missing
            WorkflowMaxAPIError: If API response indicates an error
        """
        # Check response status
        XMLParser.check_response(xml_element)
            
        contact_elem = xml_element.find('Contact')
        if contact_elem is None:
            raise ValueError("Missing Contact element in response")
            
        # Required fields
        self.Name = XMLParser.get_text(contact_elem, 'Name')
        self.UUID = XMLParser.get_text(contact_elem, 'UUID')
        
        # Optional fields
        self.Addressee = XMLParser.get_text(contact_elem, 'Addressee')
        self.Email = XMLParser.get_text(contact_elem, 'Email')
        self.Mobile = XMLParser.get_text(contact_elem, 'Mobile')
        self.Phone = XMLParser.get_text(contact_elem, 'Phone')
        self.Salutation = XMLParser.get_text(contact_elem, 'Salutation')
        
        # IsPrimary is a string enum ('true'/'false')
        is_primary = XMLParser.get_text(contact_elem, 'IsPrimary')
        self.IsPrimary = 'true' if is_primary and is_primary.lower() == 'true' else 'false'
        
        # Position and Client information
        positions_elem = contact_elem.find('Positions')
        if positions_elem is not None:
            position_elem = positions_elem.find('Position')
            if position_elem is not None:
                self.Position = XMLParser.get_text(position_elem, 'Position')
                self.ClientName = XMLParser.get_text(position_elem, 'Name')
                self.ClientUUID = XMLParser.get_text(position_elem, 'UUID')
            else:
                self.Position = None
                self.ClientName = None
                self.ClientUUID = None
        else:
            self.Position = None
            self.ClientName = None
            self.ClientUUID = None
        
        # Initialize custom fields
        self.CustomFields: List[Dict[str, Any]] = []
        self.custom_field_definitions: List[Dict[str, str]] = []
        
        # Validate required fields
        if not self.Name:
            raise ValueError("Contact must have a Name")
        if not self.UUID:
            raise ValueError("Contact must have a UUID")

    def parse_custom_fields(self, xml_element: ET.Element) -> None:
        """Parse custom fields from XML element.
        
        Args:
            xml_element: The XML element containing custom fields data
            
        Raises:
            WorkflowMaxAPIError: If API response indicates an error
        """
        XMLParser.check_response(xml_element)
            
        custom_fields_elem = xml_element.find('CustomFields')
        if custom_fields_elem is not None:
            self.CustomFields = []  # Reset custom fields
            for field_elem in custom_fields_elem.findall('CustomField'):
                field = XMLParser.parse_custom_field_value(field_elem)
                if field.get('Name'):  # Only add fields with a name
                    self.CustomFields.append(field)
                    logger.debug(f"Parsed custom field: {field}")

    def get_custom_field_value(self, field_name: str) -> Optional[str]:
        """Get the value of a custom field by name.
        
        Args:
            field_name: The name of the custom field to get
            
        Returns:
            Optional[str]: The value of the custom field if found
        """
        for field in self.CustomFields:
            if field['Name'] == field_name:
                return field['Value']
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert contact to dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the contact
        """
        return {
            'Name': self.Name,
            'UUID': self.UUID,
            'Addressee': self.Addressee,
            'Email': self.Email,
            'Mobile': self.Mobile,
            'Phone': self.Phone,
            'Position': self.Position,
            'Salutation': self.Salutation,
            'IsPrimary': self.IsPrimary,
            'ClientName': self.ClientName,
            'ClientUUID': self.ClientUUID,
            'CustomFields': self.CustomFields
        }

    def print_details(self) -> None:
        """Print all contact details in a formatted way."""
        print(f"\nContact Details:")
        print(f"Name: {self.Name}")
        print(f"Email: {self.Email}")
        if self.Mobile:
            print(f"Mobile: {self.Mobile}")
        if self.Phone:
            print(f"Phone: {self.Phone}")
        if self.Position:
            print(f"Position: {self.Position}")
        if self.ClientName:
            print(f"Client: {self.ClientName}")
        if self.Addressee:
            print(f"Addressee: {self.Addressee}")
        if self.Salutation:
            print(f"Salutation: {self.Salutation}")
        print(f"Is Primary Contact: {self.IsPrimary}")
        
        if self.CustomFields:
            print("\nCustom Fields:")
            for field in self.CustomFields:
                print(f"{field['Name']} ({field['Type']}): {field['Value']}")
