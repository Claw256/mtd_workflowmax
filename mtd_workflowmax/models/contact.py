"""Contact model for WorkflowMax API."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator, computed_field
import xml.etree.ElementTree as ET

from ..core.exceptions import ValidationError, XMLParsingError
from ..core.logging import get_logger
from ..core.utils import validate_string_length, sanitize_xml, get_xml_text
from .custom_field import CustomFieldValue, CustomFieldType

logger = get_logger('workflowmax.models.contact')

class Position(BaseModel):
    """Position information for a contact."""
    
    uuid: Optional[str] = Field(
        None,
        alias="UUID",
        description="UUID of the position"
    )
    position: Optional[str] = Field(
        None,
        alias="Position",
        description="Contact's position/title"
    )
    client_name: Optional[str] = Field(
        None,
        alias="Name",
        description="Name of the client organization"
    )
    client_uuid: Optional[str] = Field(
        None,
        alias="ClientUUID",
        description="UUID of the client organization"
    )
    include_in_emails: bool = Field(
        False,
        alias="IncludeInEmails",
        description="Whether to include in emails"
    )
    is_primary: bool = Field(
        False,
        alias="IsPrimary",
        description="Whether this is the primary position"
    )
    
    @validator('position', 'client_name')
    def validate_length(cls, v):
        """Validate string length."""
        if v:
            validate_string_length(v, 'Position/Client name', max_length=100)
        return v
    
    def to_xml(self) -> str:
        """Convert position to XML string."""
        xml = ['<Position>']
        
        if self.uuid:
            xml.append(f"<UUID>{sanitize_xml(self.uuid)}</UUID>")
        if self.position:
            xml.append(f"<Position>{sanitize_xml(self.position)}</Position>")
        if self.client_name:
            xml.append(f"<Name>{sanitize_xml(self.client_name)}</Name>")
        if self.client_uuid:
            xml.append(f"<ClientUUID>{sanitize_xml(self.client_uuid)}</ClientUUID>")
            
        # Add flags as string enums
        xml.append(f"<IncludeInEmails>{'yes' if self.include_in_emails else 'no'}</IncludeInEmails>")
        xml.append(f"<IsPrimary>{'yes' if self.is_primary else 'no'}</IsPrimary>")
        
        xml.append('</Position>')
        return '\n'.join(xml)

class Contact(BaseModel):
    """WorkflowMax contact model."""
    
    uuid: str = Field(
        ...,
        alias="UUID",
        description="Contact UUID"
    )
    name: str = Field(
        ...,
        alias="Name",
        description="Contact name"
    )
    addressee: Optional[str] = Field(
        None,
        alias="Addressee",
        description="Contact addressee"
    )
    email: Optional[str] = Field(
        None,
        alias="Email",
        description="Contact email"
    )
    mobile: Optional[str] = Field(
        None,
        alias="Mobile",
        description="Contact mobile number"
    )
    phone: Optional[str] = Field(
        None,
        alias="Phone",
        description="Contact phone number"
    )
    salutation: Optional[str] = Field(
        None,
        alias="Salutation",
        description="Contact salutation"
    )
    is_primary: str = Field(
        'false',
        alias="IsPrimary",
        description="Whether this is a primary contact"
    )
    
    # Nested objects
    positions: List[Position] = Field(
        default_factory=list,
        alias="Positions",
        description="Contact positions"
    )
    custom_fields: List[CustomFieldValue] = Field(
        default_factory=list,
        alias="CustomFields",
        description="Custom fields"
    )
    
    # ProfileData protocol properties
    @property
    def company_name(self) -> Optional[str]:
        """Get company name from primary position."""
        for pos in self.positions:
            if pos.is_primary:
                return pos.client_name
        return self.positions[0].client_name if self.positions else None
    
    @property
    def position_title(self) -> Optional[str]:
        """Get position title from primary position."""
        for pos in self.positions:
            if pos.is_primary:
                return pos.position
        return self.positions[0].position if self.positions else None
    
    # Validation
    @validator('name')
    def validate_name(cls, v):
        """Validate contact name."""
        validate_string_length(v, 'Name', min_length=1, max_length=100)
        return v
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format."""
        if v:
            # Basic email validation
            if '@' not in v or '.' not in v:
                raise ValueError("Invalid email format")
            validate_string_length(v, 'Email', max_length=254)
        return v
    
    @validator('mobile', 'phone')
    def validate_phone(cls, v):
        """Validate phone numbers."""
        if v:
            # Remove non-numeric characters for validation
            numeric = ''.join(filter(str.isdigit, v))
            if len(numeric) < 5:
                raise ValueError("Phone number too short")
            if len(numeric) > 15:
                raise ValueError("Phone number too long")
        return v
    
    @validator('is_primary')
    def validate_is_primary(cls, v):
        """Validate is_primary as string enum."""
        if v.lower() not in ('true', 'false'):
            raise ValueError("IsPrimary must be 'true' or 'false'")
        return v.lower()
    
    @classmethod
    def from_xml(cls, xml_element: ET.Element) -> 'Contact':
        """Create Contact instance from XML element.
        
        Args:
            xml_element: XML element containing contact data
            
        Returns:
            Contact instance
            
        Raises:
            XMLParsingError: If XML parsing fails
            ValidationError: If data validation fails
        """
        try:
            # Map XML tags to model fields with fallbacks
            field_mappings = {
                'UUID': ('UUID', None),
                'Name': ('Name', None),
                'Addressee': ('Addressee', None),
                'Email': ('Email', None),
                'Mobile': ('Mobile', None),
                'Phone': ('Phone', None),
                'Salutation': ('Salutation', None),
                'IsPrimary': ('IsPrimary', 'false')
            }
            
            data = {}
            for xml_tag, (field_name, default) in field_mappings.items():
                value = get_xml_text(xml_element, xml_tag, default)
                if value is not None:
                    data[field_name] = value
            
            # Parse positions with better error handling
            positions = []
            try:
                positions_elem = xml_element.find('Positions')
                if positions_elem is not None:
                    for pos_elem in positions_elem.findall('Position'):
                        try:
                            pos_data = {
                                'UUID': get_xml_text(pos_elem, 'UUID'),
                                'Position': get_xml_text(pos_elem, 'Position'),
                                'Name': get_xml_text(pos_elem, 'Name'),
                                'ClientUUID': get_xml_text(pos_elem, 'ClientUUID'),
                                'IncludeInEmails': get_xml_text(pos_elem, 'IncludeInEmails', 'no').lower() == 'yes',
                                'IsPrimary': get_xml_text(pos_elem, 'IsPrimary', 'no').lower() == 'yes'
                            }
                            positions.append(Position(**pos_data))
                        except Exception as e:
                            logger.warning(f"Failed to parse position: {str(e)}")
                            continue
            except Exception as e:
                logger.warning(f"Failed to parse positions: {str(e)}")
            
            data['Positions'] = positions
            
            # Parse custom fields if present
            try:
                custom_fields_elem = xml_element.find('CustomFields')
                if custom_fields_elem is not None:
                    data['CustomFields'] = [
                        CustomFieldValue.from_xml(field_elem)
                        for field_elem in custom_fields_elem.findall('CustomField')
                    ]
            except Exception as e:
                logger.warning(f"Failed to parse custom fields: {str(e)}")
                data['CustomFields'] = []
            
            return cls(**data)
            
        except Exception as e:
            raise XMLParsingError(f"Failed to parse contact XML: {str(e)}", xml_element)
    
    def to_xml(self) -> str:
        """Convert contact to XML string.
        
        Returns:
            XML string representation
        """
        # Create main elements
        xml = ['<Contact>']
        
        # Add basic fields
        fields = [
            ('UUID', self.uuid),
            ('Name', self.name),
            ('Addressee', self.addressee),
            ('Email', self.email),
            ('Mobile', self.mobile),
            ('Phone', self.phone),
            ('Salutation', self.salutation),
            ('IsPrimary', self.is_primary)
        ]
        
        for name, value in fields:
            if value is not None:
                xml.append(f"<{name}>{sanitize_xml(str(value))}</{name}>")
        
        # Add positions if present
        if self.positions:
            xml.append('<Positions>')
            for position in self.positions:
                xml.append(position.to_xml())
            xml.append('</Positions>')
        
        # Add custom fields if present
        if self.custom_fields:
            xml.append('<CustomFields>')
            for field in self.custom_fields:
                xml.append(field.to_xml())
            xml.append('</CustomFields>')
        
        xml.append('</Contact>')
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert contact to dictionary representation.
        
        Returns:
            Dictionary representation of contact
        """
        data = {
            'UUID': self.uuid,
            'Name': self.name,
            'Addressee': self.addressee,
            'Email': self.email,
            'Mobile': self.mobile,
            'Phone': self.phone,
            'Salutation': self.salutation,
            'IsPrimary': self.is_primary
        }
        
        if self.positions:
            data['Positions'] = [
                {
                    'UUID': pos.uuid,
                    'Position': pos.position,
                    'ClientName': pos.client_name,
                    'ClientUUID': pos.client_uuid,
                    'IncludeInEmails': pos.include_in_emails,
                    'IsPrimary': pos.is_primary
                }
                for pos in self.positions
            ]
            
        if self.custom_fields:
            data['CustomFields'] = [
                {
                    'Name': field.name,
                    'Value': field.value,
                    'Type': field.type
                }
                for field in self.custom_fields
            ]
            
        return data

    def print_details(self) -> None:
        """Print all contact details in a formatted way."""
        print(f"\nContact Details:")
        print(f"Name: {self.name}")
        print(f"UUID: {self.uuid}")
        if self.email:
            print(f"Email: {self.email}")
        if self.mobile:
            print(f"Mobile: {self.mobile}")
        if self.phone:
            print(f"Phone: {self.phone}")
        if self.addressee:
            print(f"Addressee: {self.addressee}")
        if self.salutation:
            print(f"Salutation: {self.salutation}")
        print(f"Is Primary Contact: {self.is_primary}")
        
        if self.positions:
            print("\nPositions:")
            for pos in self.positions:
                print(f"  Position: {pos.position or 'N/A'}")
                print(f"  Client: {pos.client_name or 'N/A'}")
                print(f"  Include in Emails: {pos.include_in_emails}")
                print(f"  Is Primary: {pos.is_primary}")
                print()
        
        if self.custom_fields:
            print("\nCustom Fields:")
            for field in self.custom_fields:
                print(f"{field.name} ({field.type.value}): {field.format_value()}")
