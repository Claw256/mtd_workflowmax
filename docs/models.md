# Data Models

This document details the data models used in the `mtd_workflowmax` module, with particular focus on XML handling and validation.

## Overview

The module uses Pydantic models for data validation and serialization. Each model handles its own XML conversion and validation rules.

## Custom Field Models

### CustomFieldType

Enum defining supported field types:

```python
class CustomFieldType(str, Enum):
    TEXT = "Text"
    MULTILINE_TEXT = "Multi-line Text"
    NUMBER = "Number"
    DECIMAL = "Decimal"
    DATE = "Date"
    BOOLEAN = "Boolean"
    SELECT = "Select"
    LINK = "Link"
```

### CustomFieldDefinition

Represents a custom field definition from the API:

```python
class CustomFieldDefinition(BaseModel):
    uuid: Optional[str] = Field(None, alias="UUID")
    name: str = Field(..., alias="Name")
    type: CustomFieldType = Field(..., alias="Type")
    description: Optional[str] = Field(None, alias="Description")
    options: List[str] = Field(default_factory=list, alias="Options")
    required: bool = Field(False, alias="Required")
    link_url: Optional[str] = Field(None, alias="LinkURL")
    
    # Usage flags
    use_client: bool = Field(False, alias="UseClient")
    use_contact: bool = Field(False, alias="UseContact")
    use_supplier: bool = Field(False, alias="UseSupplier")
    use_job: bool = Field(False, alias="UseJob")
    # ... other usage flags
```

Key features:
- UUID is optional but important for updates
- Field aliases match XML tag names
- Usage flags determine where fields can be used

### CustomFieldValue

Represents a custom field value:

```python
class CustomFieldValue(BaseModel):
    uuid: Optional[str] = Field(None, alias="UUID")
    name: str = Field(..., alias="Name")
    type: CustomFieldType = Field(CustomFieldType.TEXT, alias="Type")
    value: Optional[str] = Field(None, alias="Value")
    link_url: Optional[str] = Field(None, alias="LinkURL")
```

Important methods:

```python
def validate_value(cls, v, values):
    """Validate value based on field type."""
    if v is None:
        return v
        
    field_type = values.get('type')
    if field_type == CustomFieldType.NUMBER:
        int(float(v))  # Validate integer
    elif field_type == CustomFieldType.DECIMAL:
        float(v)  # Validate decimal
    elif field_type == CustomFieldType.LINK:
        if not v.startswith(('http://', 'https://', 'www.')):
            v = 'https://' + v
    return v

def to_xml(self) -> str:
    """Convert to XML string."""
    xml = ['<CustomField>']
    
    # Order matters!
    if self.uuid:
        xml.append(f"<UUID>{sanitize_xml(self.uuid)}</UUID>")
    xml.append(f"<Name>{sanitize_xml(self.name)}</Name>")
    xml.append(f"<Type>{self.type.value}</Type>")
    
    if self.type == CustomFieldType.LINK:
        xml.append(f"<LinkURL>{sanitize_xml(self.value)}</LinkURL>")
    else:
        xml.append(f"<Value>{sanitize_xml(self.value or '')}</Value>")
    
    xml.append('</CustomField>')
    return '\n'.join(xml)
```

## Contact Model

Represents a WorkflowMax contact:

```python
class Contact(BaseModel):
    uuid: str = Field(..., alias="UUID")
    name: str = Field(..., alias="Name")
    email: Optional[str] = Field(None, alias="Email")
    mobile: Optional[str] = Field(None, alias="Mobile")
    phone: Optional[str] = Field(None, alias="Phone")
    is_primary: bool = Field(False, alias="IsPrimary")
    positions: List[Position] = Field(default_factory=list)
    custom_fields: List[CustomFieldValue] = Field(default_factory=list)
```

XML handling:

```python
@classmethod
def from_xml(cls, xml_element: ET.Element) -> 'Contact':
    """Create Contact from XML element."""
    data = {
        "UUID": get_xml_text(xml_element, 'UUID', required=True),
        "Name": get_xml_text(xml_element, 'Name', required=True),
        "Email": get_xml_text(xml_element, 'Email'),
        "Mobile": get_xml_text(xml_element, 'Mobile'),
        "Phone": get_xml_text(xml_element, 'Phone'),
        "IsPrimary": get_xml_text(xml_element, 'IsPrimary', 'false').lower() == 'true'
    }
    
    # Parse positions
    positions_elem = xml_element.find('Positions')
    if positions_elem is not None:
        data['positions'] = [
            Position.from_xml(pos_elem)
            for pos_elem in positions_elem.findall('Position')
        ]
    
    return cls(**data)
```

## Position Model

Represents a contact's position:

```python
class Position(BaseModel):
    uuid: Optional[str] = Field(None, alias="UUID")
    position: str = Field(..., alias="Position")
    client_name: str = Field(..., alias="Name")
    client_uuid: Optional[str] = None
    include_in_emails: bool = Field(False, alias="IncludeInEmails")
    is_primary: bool = Field(False, alias="IsPrimary")
```

## XML Handling Best Practices

1. Tag Order
```python
def to_xml(self) -> str:
    """Always maintain correct tag order."""
    xml = []
    # UUID first
    if self.uuid:
        xml.append(f"<UUID>{sanitize_xml(self.uuid)}</UUID>")
    # Name second
    xml.append(f"<Name>{sanitize_xml(self.name)}</Name>")
    # Type third
    xml.append(f"<Type>{self.type.value}</Type>")
    # Value last
    xml.append(f"<Value>{sanitize_xml(self.value)}</Value>")
    return '\n'.join(xml)
```

2. Value Handling
```python
def format_value(self) -> str:
    """Format value for display."""
    if self.value is None:
        return 'Not set'
    
    if self.type == CustomFieldType.BOOLEAN:
        return 'Yes' if self.value.lower() == 'true' else 'No'
    elif self.type == CustomFieldType.LINK:
        return f"<{self.value}>"
    elif self.type == CustomFieldType.DATE:
        dt = datetime.strptime(self.value, '%Y-%m-%d')
        return dt.strftime('%d %b %Y')
    return self.value
```

3. Link URL Handling
```python
def validate_link_url(cls, v, values):
    """Validate and format link URLs."""
    if not v:
        return v
    
    # Add protocol if missing
    if not v.startswith(('http://', 'https://', 'www.')):
        v = 'https://' + v
    
    # Don't modify the URL structure
    return v
```

4. XML Parsing
```python
@classmethod
def from_xml(cls, xml_element: ET.Element) -> 'CustomFieldValue':
    """Create instance from XML."""
    try:
        data = {
            "UUID": get_xml_text(xml_element, 'UUID'),
            "Name": get_xml_text(xml_element, 'Name', required=True),
            "Type": get_xml_text(xml_element, 'Type', CustomFieldType.TEXT)
        }
        
        # Get value based on type
        field_type = data['Type']
        if field_type == CustomFieldType.LINK:
            data['Value'] = get_xml_text(xml_element, 'LinkURL')
        else:
            data['Value'] = get_xml_text(xml_element, 'Value')
        
        return cls(**data)
    except Exception as e:
        raise XMLParsingError(f"Failed to parse: {str(e)}", xml_element)
```

## Common Pitfalls

1. XML Tag Order
   - Always put UUID first
   - Follow with Name and Type
   - Put value tags last

2. Link URLs
   - Don't modify URL structure
   - Keep original format
   - Include full URL in updates

3. Value Types
   - Validate numbers properly
   - Handle date formats consistently
   - Convert booleans to lowercase

4. Missing Fields
   - Include all fields in updates
   - Preserve existing values
   - Handle optional fields properly
