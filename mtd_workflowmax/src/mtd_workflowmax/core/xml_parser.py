"""Base XML parsing functionality for WorkflowMax API responses."""

import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any, List
from datetime import datetime
from .exceptions import WorkflowMaxError
from .logging import get_logger

logger = get_logger('workflowmax.core.xml_parser')

class XMLParser:
    """Base class for XML parsing operations."""
    
    @staticmethod
    def get_text(element: Optional[ET.Element], tag_name: str) -> Optional[str]:
        """Extract text from XML elements safely.
        
        Args:
            element: The XML element to extract text from
            tag_name: The name of the tag to find
            
        Returns:
            Optional[str]: The text content of the tag if found, None otherwise
        """
        if element is None:
            return None
        tag = element.find(tag_name)
        return tag.text if tag is not None else None

    @staticmethod
    def check_response(response_xml: ET.Element) -> bool:
        """Check API response for errors.
        
        Args:
            response_xml: The XML response element to check
            
        Returns:
            bool: True if response is OK
            
        Raises:
            WorkflowMaxError: If response indicates an error
        """
        status = response_xml.find('Status')
        if status is None or status.text != 'OK':
            error = response_xml.find('Error')
            error_msg = error.text if error is not None else "Unknown API error"
            raise WorkflowMaxError(error_msg)
        return True

    @staticmethod
    def parse_custom_field_value(field_elem: ET.Element) -> Dict[str, Any]:
        """Parse a custom field value from XML element.
        
        Args:
            field_elem: The XML element containing the custom field data
            
        Returns:
            Dict[str, Any]: Dictionary containing the parsed field data
        """
        field = {
            'Name': XMLParser.get_text(field_elem, 'Name'),
            'UUID': XMLParser.get_text(field_elem, 'UUID')
        }
        
        # Check each possible value type
        if (value := XMLParser.get_text(field_elem, 'Boolean')) is not None:
            field['Type'] = 'Boolean'
            field['Value'] = value.lower()
        elif (value := XMLParser.get_text(field_elem, 'Date')) is not None:
            field['Type'] = 'Date'
            try:
                date_obj = datetime.strptime(value, '%Y-%m-%d')
                field['Value'] = date_obj.strftime('%Y-%m-%d')
            except ValueError:
                field['Value'] = value
        elif (value := XMLParser.get_text(field_elem, 'Decimal')) is not None:
            field['Type'] = 'Decimal'
            field['Value'] = value
        elif (value := XMLParser.get_text(field_elem, 'Number')) is not None:
            field['Type'] = 'Number'
            field['Value'] = value
        elif (value := XMLParser.get_text(field_elem, 'Text')) is not None:
            field['Type'] = 'Text'
            field['Value'] = value
        elif (value := XMLParser.get_text(field_elem, 'LinkURL')) is not None:
            field['Type'] = 'Link'
            field['Value'] = value
        else:
            field['Type'] = 'Text'
            field['Value'] = ''
        
        return field

    @staticmethod
    def parse_custom_field_definitions(definitions_xml: ET.Element) -> List[Dict[str, str]]:
        """Parse custom field definitions from XML response.
        
        Args:
            definitions_xml: The XML element containing definitions
            
        Returns:
            List[Dict[str, str]]: List of parsed field definitions
        """
        XMLParser.check_response(definitions_xml)
        
        definitions = []
        custom_field_defs = definitions_xml.find('CustomFieldDefinitions')
        if custom_field_defs is not None:
            for field_elem in custom_field_defs.findall('CustomFieldDefinition'):
                definition = {
                    'Name': XMLParser.get_text(field_elem, 'Name'),
                    'Type': XMLParser.get_text(field_elem, 'Type'),
                    'UUID': XMLParser.get_text(field_elem, 'UUID'),
                    'UseContact': XMLParser.get_text(field_elem, 'UseContact')
                }
                
                if options := field_elem.find('Options'):
                    definition['Options'] = options.text
                if mandatory := field_elem.find('Mandatory'):
                    definition['Mandatory'] = mandatory.text
                
                if (definition['UseContact'] == 'true' and 
                    definition['Name'] and 
                    definition['Type'] and 
                    definition['UUID']):
                    definitions.append(definition)
                    logger.debug(f"Found contact custom field definition: {definition}")
        
        return definitions

    @staticmethod
    def generate_custom_field_xml(field_name: str, field_value: str, field_def: Dict[str, str]) -> str:
        """Generate XML for updating a custom field.
        
        Args:
            field_name: Name of the field to update
            field_value: New value for the field
            field_def: Field definition dictionary
            
        Returns:
            str: Generated XML string
            
        Raises:
            ValueError: If field definition is missing required information
        """
        if 'Type' not in field_def:
            raise ValueError(f"Field definition for {field_name} missing Type")
            
        root = ET.Element('CustomFields')
        custom_field = ET.SubElement(root, 'CustomField')
        
        # Add UUID element (required)
        uuid_elem = ET.SubElement(custom_field, 'UUID')
        uuid_elem.text = field_def['UUID']
        
        # Add Name element (required)
        name_elem = ET.SubElement(custom_field, 'Name')
        name_elem.text = field_name
        
        # Add value under type-specific element
        if field_def['Type'] == 'Checkbox':
            value_elem = ET.SubElement(custom_field, 'Boolean')
            value_elem.text = str(field_value).lower()
        elif field_def['Type'] == 'Date':
            value_elem = ET.SubElement(custom_field, 'Date')
            try:
                date_obj = datetime.strptime(field_value, '%Y-%m-%d')
                value_elem.text = date_obj.strftime('%Y-%m-%d')
            except ValueError:
                raise ValueError(f"Invalid date format for {field_name}. Expected YYYY-MM-DD")
        elif field_def['Type'] == 'Decimal':
            value_elem = ET.SubElement(custom_field, 'Decimal')
            value_elem.text = field_value
        elif field_def['Type'] == 'Number':
            value_elem = ET.SubElement(custom_field, 'Number')
            value_elem.text = field_value
        elif field_def['Type'] == 'Link':
            value_elem = ET.SubElement(custom_field, 'LinkURL')
            value_elem.text = field_value
        else:
            value_elem = ET.SubElement(custom_field, 'Text')
            value_elem.text = field_value
        
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
