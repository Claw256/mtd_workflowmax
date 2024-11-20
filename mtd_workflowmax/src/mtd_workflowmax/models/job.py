"""Job model for WorkflowMax API."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import xml.etree.ElementTree as ET

from ..core.exceptions import XMLParsingError
from ..core.logging import get_logger
from ..core.utils import validate_string_length, sanitize_xml
from .custom_field import CustomFieldValue

logger = get_logger('workflowmax.models.job')

class Job(BaseModel):
    """WorkflowMax job model."""
    
    uuid: str = Field(
        ...,
        alias="UUID",
        description="Job UUID"
    )
    name: str = Field(
        ...,
        alias="Name",
        description="Job name"
    )
    description: Optional[str] = Field(
        None,
        alias="Description",
        description="Job description"
    )
    state: Optional[str] = Field(
        None,
        alias="State",
        description="Job state"
    )
    custom_fields: List[CustomFieldValue] = Field(
        default_factory=list,
        alias="CustomFields"
    )
    
    @classmethod
    def from_xml(cls, xml_element: ET.Element) -> 'Job':
        """Create Job instance from XML element.
        
        Args:
            xml_element: XML element containing job data
            
        Returns:
            Job instance
            
        Raises:
            XMLParsingError: If XML parsing fails
        """
        try:
            # Parse basic fields
            data = {
                "UUID": cls._get_text(xml_element, 'UUID'),
                "Name": cls._get_text(xml_element, 'Name'),
                "Description": cls._get_text(xml_element, 'Description'),
                "State": cls._get_text(xml_element, 'State')
            }
            
            # Create instance
            return cls(**data)
            
        except Exception as e:
            raise XMLParsingError(f"Failed to parse job XML: {str(e)}")
    
    def to_xml(self) -> str:
        """Convert job to XML string.
        
        Returns:
            XML string representation
        """
        # Create main elements
        xml = ['<Job>']
        
        # Add basic fields
        fields = [
            ('UUID', self.uuid),
            ('Name', self.name),
            ('Description', self.description),
            ('State', self.state)
        ]
        
        for name, value in fields:
            if value is not None:
                xml.append(f"<{name}>{sanitize_xml(str(value))}</{name}>")
        
        # Add custom fields if present
        if self.custom_fields:
            xml.append('<CustomFields>')
            for field in self.custom_fields:
                xml.append(field.to_xml())
            xml.append('</CustomFields>')
        
        xml.append('</Job>')
        return '\n'.join(xml)
    
    def get_custom_field_value(self, field_name: str) -> Optional[str]:
        """Get value of a custom field by name.
        
        Args:
            field_name: Name of the custom field
            
        Returns:
            Field value if found, None otherwise
        """
        for field in self.custom_fields:
            if field.name == field_name:
                return field.value
        return None
    
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
