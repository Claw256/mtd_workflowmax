"""Custom field models for WorkflowMax API."""

from typing import Optional, List, Dict, Any, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, validator
import xml.etree.ElementTree as ET
import re

from ..core.exceptions import ValidationError, XMLParsingError, CustomFieldError
from ..core.logging import get_logger
from ..core.utils import validate_string_length, sanitize_xml, get_xml_text

logger = get_logger('workflowmax.models.custom_field')

class CustomFieldType(str, Enum):
    """Supported custom field types based on API schema."""
    
    TEXT = "Text"
    MULTILINE_TEXT = "Multi-line Text"
    NUMBER = "Number"
    DECIMAL = "Decimal"
    DATE = "Date"
    BOOLEAN = "Boolean"  # Changed from CHECKBOX to match API schema
    SELECT = "Select"
    LINK = "Link"

class CustomFieldDefinition(BaseModel):
    """Custom field definition model."""
    
    name: str = Field(
        ...,
        alias="Name",
        description="Field name"
    )
    type: CustomFieldType = Field(
        ...,
        alias="Type",
        description="Field type"
    )
    description: Optional[str] = Field(
        None,
        alias="Description",
        description="Field description"
    )
    options: List[str] = Field(
        default_factory=list,
        alias="Options",
        description="Available options for Select type fields"
    )
    required: bool = Field(
        False,
        alias="Required",
        description="Whether the field is required"
    )
    
    # Usage flags
    use_client: bool = Field(
        False,
        alias="UseClient",
        description="Whether the field can be used on clients"
    )
    use_contact: bool = Field(
        False,
        alias="UseContact",
        description="Whether the field can be used on contacts"
    )
    use_supplier: bool = Field(
        False,
        alias="UseSupplier",
        description="Whether the field can be used on suppliers"
    )
    use_job: bool = Field(
        False,
        alias="UseJob",
        description="Whether the field can be used on jobs"
    )
    use_lead: bool = Field(
        False,
        alias="UseLead",
        description="Whether the field can be used on leads"
    )
    use_job_task: bool = Field(
        False,
        alias="UseJobTask",
        description="Whether the field can be used on job tasks"
    )
    use_job_cost: bool = Field(
        False,
        alias="UseJobCost",
        description="Whether the field can be used on job costs"
    )
    use_job_time: bool = Field(
        False,
        alias="UseJobTime",
        description="Whether the field can be used on job time entries"
    )
    use_quote: bool = Field(
        False,
        alias="UseQuote",
        description="Whether the field can be used on quotes"
    )
    
    # Link type fields
    link_url: Optional[str] = Field(
        None,
        alias="LinkURL",
        description="URL template for Link type fields"
    )
    value_element: Optional[str] = Field(
        None,
        alias="ValueElement",
        description="XML element to use for field value"
    )
    
    class Config:
        """Model configuration."""
        populate_by_name = True  # Allow both alias and field name for assignment
    
    @validator('name')
    def validate_name(cls, v):
        """Validate field name."""
        validate_string_length(v, 'Field name', min_length=1, max_length=100)
        return v
    
    @validator('description')
    def validate_description(cls, v):
        """Validate description length."""
        if v:
            validate_string_length(v, 'Description', max_length=500)
        return v
    
    @validator('options')
    def validate_options(cls, v, values):
        """Validate options for Select type fields."""
        if 'type' in values and values['type'] == CustomFieldType.SELECT and not v:
            raise ValidationError("Select type fields must have options")
        return v
    
    @classmethod
    def from_xml(cls, xml_element: ET.Element) -> 'CustomFieldDefinition':
        """Create CustomFieldDefinition from XML element.
        
        Args:
            xml_element: XML element containing field definition
            
        Returns:
            CustomFieldDefinition instance
            
        Raises:
            XMLParsingError: If XML parsing fails
            ValidationError: If data validation fails
        """
        try:
            data = {
                "Name": get_xml_text(xml_element, 'Name', required=True),
                "Type": get_xml_text(xml_element, 'Type', required=True),
                "Description": get_xml_text(xml_element, 'Description'),
                "Required": get_xml_text(xml_element, 'Mandatory', 'false').lower() == 'true',
                "UseClient": get_xml_text(xml_element, 'UseClient', 'false').lower() == 'true',
                "UseContact": get_xml_text(xml_element, 'UseContact', 'false').lower() == 'true',
                "UseSupplier": get_xml_text(xml_element, 'UseSupplier', 'false').lower() == 'true',
                "UseJob": get_xml_text(xml_element, 'UseJob', 'false').lower() == 'true',
                "UseLead": get_xml_text(xml_element, 'UseLead', 'false').lower() == 'true',
                "UseJobTask": get_xml_text(xml_element, 'UseJobTask', 'false').lower() == 'true',
                "UseJobCost": get_xml_text(xml_element, 'UseJobCost', 'false').lower() == 'true',
                "UseJobTime": get_xml_text(xml_element, 'UseJobTime', 'false').lower() == 'true',
                "UseQuote": get_xml_text(xml_element, 'UseQuote', 'false').lower() == 'true',
                "LinkURL": get_xml_text(xml_element, 'LinkURL'),
                "ValueElement": get_xml_text(xml_element, 'ValueElement')
            }
            
            # Parse options for Select type
            options_elem = xml_element.find('Options')
            if options_elem is not None:
                data['Options'] = [
                    option.text for option in options_elem.findall('Option')
                    if option.text
                ]
            
            return cls(**data)
            
        except Exception as e:
            raise XMLParsingError(f"Failed to parse custom field definition: {str(e)}", xml_element)
    
    def to_xml(self) -> str:
        """Convert definition to XML string.
        
        Returns:
            XML string representation
        """
        xml = ['<CustomField>']
        
        # Add basic fields
        xml.append(f"<Name>{sanitize_xml(self.name)}</Name>")
        xml.append(f"<Type>{self.type.value}</Type>")
        
        if self.description:
            xml.append(f"<Description>{sanitize_xml(self.description)}</Description>")
            
        xml.append(f"<Mandatory>{str(self.required).lower()}</Mandatory>")
        
        # Add usage flags
        xml.append(f"<UseClient>{str(self.use_client).lower()}</UseClient>")
        xml.append(f"<UseContact>{str(self.use_contact).lower()}</UseContact>")
        xml.append(f"<UseSupplier>{str(self.use_supplier).lower()}</UseSupplier>")
        xml.append(f"<UseJob>{str(self.use_job).lower()}</UseJob>")
        xml.append(f"<UseLead>{str(self.use_lead).lower()}</UseLead>")
        xml.append(f"<UseJobTask>{str(self.use_job_task).lower()}</UseJobTask>")
        xml.append(f"<UseJobCost>{str(self.use_job_cost).lower()}</UseJobCost>")
        xml.append(f"<UseJobTime>{str(self.use_job_time).lower()}</UseJobTime>")
        xml.append(f"<UseQuote>{str(self.use_quote).lower()}</UseQuote>")
        
        # Add link URL and value element if present
        if self.link_url:
            xml.append(f"<LinkURL>{sanitize_xml(self.link_url)}</LinkURL>")
        if self.value_element:
            xml.append(f"<ValueElement>{sanitize_xml(self.value_element)}</ValueElement>")
        
        # Add options for Select type
        if self.type == CustomFieldType.SELECT and self.options:
            xml.append('<Options>')
            for option in self.options:
                xml.append(f"<Option>{sanitize_xml(option)}</Option>")
            xml.append('</Options>')
        
        xml.append('</CustomField>')
        return '\n'.join(xml)

class CustomFieldValue(BaseModel):
    """Custom field value model."""
    
    name: str = Field(
        ...,
        alias="Name",
        description="Field name"
    )
    value: Optional[str] = Field(
        None,
        alias="Value",
        description="Field value"
    )
    type: CustomFieldType = Field(
        CustomFieldType.TEXT,  # Default to TEXT type
        alias="Type",
        description="Field type"
    )
    
    class Config:
        """Model configuration."""
        populate_by_name = True  # Allow both alias and field name for assignment
    
    def format_value(self) -> str:
        """Format the field value for display based on its type.
        
        Returns:
            Formatted value string
        """
        if self.value is None:
            return 'Not set'
        
        if self.type == CustomFieldType.BOOLEAN:
            return 'Yes' if self.value.lower() == 'true' else 'No'
        elif self.type == CustomFieldType.LINK:
            return f"<{self.value}>"
        elif self.type == CustomFieldType.DATE:
            try:
                dt = datetime.strptime(self.value, '%Y-%m-%d')
                return dt.strftime('%d %b %Y')
            except ValueError:
                return self.value
        elif self.type == CustomFieldType.NUMBER:
            try:
                return f"{int(float(self.value)):,}"
            except ValueError:
                return self.value
        elif self.type == CustomFieldType.DECIMAL:
            try:
                return f"{float(self.value):,.2f}"
            except ValueError:
                return self.value
        else:
            return self.value
    
    @validator('value')
    def validate_value(cls, v, values):
        """Validate value based on field type."""
        if v is None:
            return v
            
        if 'type' not in values:
            return v
            
        field_type = values['type']
        try:
            if field_type == CustomFieldType.NUMBER:
                # Validate as integer
                int(float(v))  # Allow float input but ensure it's whole number
            elif field_type == CustomFieldType.DECIMAL:
                float(v)  # Validate decimal format
            elif field_type == CustomFieldType.DATE:
                # Support both date-only and full datetime formats
                try:
                    datetime.strptime(v, '%Y-%m-%d')
                except ValueError:
                    datetime.strptime(v, '%Y-%m-%d %H:%M:%S%z')
            elif field_type == CustomFieldType.BOOLEAN:
                if v.lower() not in ('true', 'false'):
                    raise ValueError("Boolean value must be 'true' or 'false'")
            elif field_type == CustomFieldType.LINK:
                # Remove any XML tags
                v = re.sub(r'<[^>]+>', '', v)
                # Add https:// prefix if not present
                if not v.startswith(('http://', 'https://', 'www.')):
                    v = 'https://' + v
        except ValueError as e:
            raise ValidationError(f"Invalid value for type {field_type}: {str(e)}")
            
        return v
    
    @classmethod
    def from_xml(cls, xml_element: ET.Element) -> 'CustomFieldValue':
        """Create CustomFieldValue from XML element.
        
        Args:
            xml_element: XML element containing field value
            
        Returns:
            CustomFieldValue instance
            
        Raises:
            XMLParsingError: If XML parsing fails
            ValidationError: If data validation fails
        """
        try:
            data = {
                "Name": get_xml_text(xml_element, 'Name', required=True),
                "Type": get_xml_text(xml_element, 'Type', CustomFieldType.TEXT)
            }
            
            # Determine value based on type
            field_type = data['Type']
            if field_type == CustomFieldType.BOOLEAN:
                data['Value'] = get_xml_text(xml_element, 'Boolean')
            elif field_type == CustomFieldType.DATE:
                date_val = get_xml_text(xml_element, 'Date')
                if date_val:
                    # Convert to standard format if needed
                    try:
                        dt = datetime.strptime(date_val, '%Y%m%d')
                        date_val = dt.strftime('%Y-%m-%d')
                    except ValueError:
                        pass  # Keep original format if parsing fails
                data['Value'] = date_val
            elif field_type == CustomFieldType.NUMBER:
                data['Value'] = get_xml_text(xml_element, 'Number')
            elif field_type == CustomFieldType.DECIMAL:
                data['Value'] = get_xml_text(xml_element, 'Decimal')
            elif field_type == CustomFieldType.LINK:
                data['Value'] = get_xml_text(xml_element, 'LinkURL')
            else:
                data['Value'] = get_xml_text(xml_element, 'Value')
            
            return cls(**data)
            
        except Exception as e:
            raise XMLParsingError(f"Failed to parse custom field value: {str(e)}", xml_element)
    
    def to_xml(self) -> str:
        """Convert value to XML string.
        
        Returns:
            XML string representation
        """
        xml = ['<CustomField>']
        
        xml.append(f"<Name>{sanitize_xml(self.name)}</Name>")
        xml.append(f"<Type>{self.type.value}</Type>")
        
        # Value handling based on type
        if self.type == CustomFieldType.BOOLEAN:
            xml.append(f"<Boolean>{str(self.value or 'false').lower()}</Boolean>")
        elif self.type == CustomFieldType.DATE:
            if self.value:
                try:
                    # Ensure consistent date format
                    dt = datetime.strptime(self.value, '%Y-%m-%d')
                    xml.append(f"<Date>{dt.strftime('%Y-%m-%d %H:%M:%S+00:00')}</Date>")
                except ValueError:
                    # If already in datetime format, use as is
                    xml.append(f"<Date>{sanitize_xml(self.value)}</Date>")
            else:
                xml.append("<Date></Date>")
        elif self.type == CustomFieldType.NUMBER:
            value_str = str(int(float(self.value))) if self.value else ''
            xml.append(f"<Number>{sanitize_xml(value_str)}</Number>")
        elif self.type == CustomFieldType.DECIMAL:
            value_str = str(float(self.value)) if self.value else ''
            xml.append(f"<Decimal>{sanitize_xml(value_str)}</Decimal>")
        elif self.type == CustomFieldType.LINK:
            xml.append(f"<LinkURL>{sanitize_xml(self.value or '')}</LinkURL>")
        else:
            xml.append(f"<Value>{sanitize_xml(self.value or '')}</Value>")
        
        xml.append('</CustomField>')
        return '\n'.join(xml)
