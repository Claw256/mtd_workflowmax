"""Relationship model for WorkflowMax API."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
import xml.etree.ElementTree as ET

from ..core.exceptions import ValidationError, XMLParsingError
from ..core.logging import get_logger
from ..core.utils import validate_string_length, sanitize_xml

logger = get_logger('workflowmax.models.relationship')

class Relationship(BaseModel):
    """WorkflowMax client relationship model."""
    
    uuid: Optional[str] = Field(
        None,
        alias="UUID",
        description="Relationship UUID (only for existing relationships)"
    )
    client_uuid: str = Field(
        ...,
        alias="ClientUUID",
        description="UUID of the primary client"
    )
    related_client_uuid: str = Field(
        ...,
        alias="RelatedClientUUID",
        description="UUID of the related client"
    )
    type: str = Field(
        ...,
        description="Type of relationship"
    )
    start_date: Optional[str] = Field(
        None,
        alias="StartDate",
        description="Start date of relationship (YYYY-MM-DD)"
    )
    end_date: Optional[str] = Field(
        None,
        alias="EndDate",
        description="End date of relationship (YYYY-MM-DD)"
    )
    number_of_shared: Optional[int] = Field(
        None,
        alias="NumberOfShared",
        description="Number of shared items"
    )
    percentage: Optional[float] = Field(
        None,
        alias="Percentage",
        description="Percentage value for relationship"
    )
    
    # Validation
    @validator('type')
    def validate_type(cls, v):
        """Validate relationship type."""
        valid_types = {
            'Shareholder', 'Director', 'Trustee', 'Beneficiary', 'Partner',
            'Settlor', 'Associate', 'Secretary', 'Public Officer', 'Husband',
            'Wife', 'Spouse', 'Parent Of', 'Child Of', 'Appointer', 'Member',
            'Auditor', 'Owner'
        }
        if v not in valid_types:
            raise ValueError(f"Invalid relationship type. Must be one of: {', '.join(valid_types)}")
        return v
    
    @validator('start_date', 'end_date')
    def validate_date(cls, v):
        """Validate date format."""
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Invalid date format. Use YYYY-MM-DD")
        return v
    
    @validator('percentage')
    def validate_percentage(cls, v):
        """Validate percentage value."""
        if v is not None:
            if v < 0 or v > 100:
                raise ValueError("Percentage must be between 0 and 100")
        return v
    
    @classmethod
    def from_xml(cls, xml_element: ET.Element) -> 'Relationship':
        """Create Relationship instance from XML element.
        
        Args:
            xml_element: XML element containing relationship data
            
        Returns:
            Relationship instance
            
        Raises:
            XMLParsingError: If XML parsing fails
            ValidationError: If data validation fails
        """
        try:
            data = {
                "UUID": cls._get_text(xml_element, 'UUID'),
                "ClientUUID": cls._get_text(xml_element, 'ClientUUID'),
                "RelatedClientUUID": cls._get_text(xml_element, 'RelatedClientUUID'),
                "type": cls._get_text(xml_element, 'Type'),
                "StartDate": cls._get_text(xml_element, 'StartDate'),
                "EndDate": cls._get_text(xml_element, 'EndDate'),
                "NumberOfShared": cls._get_text(xml_element, 'NumberOfShared'),
                "Percentage": cls._get_text(xml_element, 'Percentage')
            }
            
            # Convert numeric fields
            if data["NumberOfShared"]:
                data["NumberOfShared"] = int(data["NumberOfShared"])
            if data["Percentage"]:
                data["Percentage"] = float(data["Percentage"])
            
            return cls(**data)
            
        except Exception as e:
            raise XMLParsingError(f"Failed to parse relationship XML: {str(e)}")
    
    def to_xml(self) -> str:
        """Convert relationship to XML string.
        
        Returns:
            XML string representation
        """
        xml = ['<Relationship>']
        
        # Add fields
        if self.uuid:
            xml.append(f"<UUID>{sanitize_xml(self.uuid)}</UUID>")
        xml.append(f"<ClientUUID>{sanitize_xml(self.client_uuid)}</ClientUUID>")
        xml.append(f"<RelatedClientUUID>{sanitize_xml(self.related_client_uuid)}</RelatedClientUUID>")
        xml.append(f"<Type>{sanitize_xml(self.type)}</Type>")
        
        if self.start_date:
            xml.append(f"<StartDate>{sanitize_xml(self.start_date)}</StartDate>")
        if self.end_date:
            xml.append(f"<EndDate>{sanitize_xml(self.end_date)}</EndDate>")
        if self.number_of_shared is not None:
            xml.append(f"<NumberOfShared>{self.number_of_shared}</NumberOfShared>")
        if self.percentage is not None:
            xml.append(f"<Percentage>{self.percentage}</Percentage>")
        
        xml.append('</Relationship>')
        return '\n'.join(xml)
    
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
