# Code Examples

This document provides practical examples of using the `mtd_workflowmax` module for common tasks.

## Command Line Interface

### View Contact Details
```bash
# View basic contact info
python -m mtd_workflowmax.cli contact view "contact-uuid"

# Enable debug logging
python -m mtd_workflowmax.cli --log-level debug contact view "contact-uuid"
```

### Update Custom Fields
```bash
# Update LinkedIn profile
python -m mtd_workflowmax.cli contact set-field "contact-uuid" "LINKEDIN PROFILE" "https://www.linkedin.com/in/username"

# Update boolean field
python -m mtd_workflowmax.cli contact set-field "contact-uuid" "Is Info up-to-date?" "true"
```

## Python API Usage

### Basic Contact Operations

```python
from mtd_workflowmax.api import WorkflowMaxClient
from mtd_workflowmax.services import ContactService

# Initialize client
client = WorkflowMaxClient()
contact_service = ContactService(client)

# View contact
contact = contact_service.get_contact("contact-uuid")
print(f"Name: {contact.name}")
print(f"Email: {contact.email}")

# View custom fields
for field in contact.custom_fields:
    print(f"{field.name}: {field.format_value()}")

# Update custom field
contact_service.update_custom_fields("contact-uuid", {
    "LINKEDIN PROFILE": "https://www.linkedin.com/in/username"
})
```

### Custom Field Updates

#### Update LinkedIn Profile
```python
from mtd_workflowmax.models import CustomFieldValue, CustomFieldType

# Create field value
field = CustomFieldValue(
    uuid="field-uuid",  # Important: Include UUID
    name="LINKEDIN PROFILE",
    type=CustomFieldType.LINK,
    value="https://www.linkedin.com/in/username"
)

# Convert to XML
xml = field.to_xml()
print(xml)
# Output:
# <CustomField>
#   <UUID>field-uuid</UUID>
#   <Name>LINKEDIN PROFILE</Name>
#   <Type>Link</Type>
#   <LinkURL>https://www.linkedin.com/in/username</LinkURL>
# </CustomField>
```

#### Update Multiple Fields
```python
# Get current fields
contact = contact_service.get_contact("contact-uuid")
current_fields = {f.name: f.value for f in contact.custom_fields}

# Update specific fields
updates = {
    "LINKEDIN PROFILE": "https://www.linkedin.com/in/username",
    "Is Info up-to-date?": "true"
}

# Merge with current fields
current_fields.update(updates)

# Update all fields
contact_service.update_custom_fields("contact-uuid", current_fields)
```

### Error Handling

```python
from mtd_workflowmax.core.exceptions import (
    ContactNotFoundError,
    ValidationError,
    WorkflowMaxError
)

try:
    contact_service.update_custom_fields("contact-uuid", {
        "LINKEDIN PROFILE": "invalid-url"
    })
except ValidationError as e:
    print(f"Invalid field value: {e}")
except ContactNotFoundError:
    print("Contact not found")
except WorkflowMaxError as e:
    print(f"API error: {e}")
```

### Debug Logging

```python
import logging

# Enable debug logging
logging.getLogger('workflowmax').setLevel(logging.DEBUG)

# Log to file
handler = logging.FileHandler('workflowmax.log')
handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
))
logging.getLogger('workflowmax').addHandler(handler)
```

### Repository Layer Usage

```python
from mtd_workflowmax.repositories import ContactRepository
from mtd_workflowmax.api import APIClient

# Initialize repository
api_client = APIClient()
repo = ContactRepository(api_client)

# Get contact
contact = repo.get_by_uuid("contact-uuid")

# Get custom fields
fields = repo.get_custom_fields("contact-uuid")

# Update custom fields
success = repo.update_custom_fields("contact-uuid", {
    "field-name": "field-value"
})
```

### Model Validation

```python
from mtd_workflowmax.models import CustomFieldValue
from pydantic import ValidationError

try:
    # Number field validation
    field = CustomFieldValue(
        name="Amount",
        type="Number",
        value="not-a-number"
    )
except ValidationError as e:
    print(f"Validation error: {e}")

# Date field validation
field = CustomFieldValue(
    name="Due Date",
    type="Date",
    value="2024-01-30"
)
print(field.format_value())  # Output: 30 Jan 2024
```

### XML Handling

```python
from mtd_workflowmax.core.utils import sanitize_xml

# Sanitize XML values
value = "Company & Ltd."
safe_value = sanitize_xml(value)
print(safe_value)  # Output: Company &amp; Ltd.

# Create XML manually (not recommended)
xml = f"""
<CustomFields>
    <CustomField>
        <UUID>{sanitize_xml(uuid)}</UUID>
        <Name>{sanitize_xml(name)}</Name>
        <Type>{field_type}</Type>
        <Value>{sanitize_xml(value)}</Value>
    </CustomField>
</CustomFields>
"""

# Parse XML response
import xml.etree.ElementTree as ET
root = ET.fromstring(response_text)
status = root.find('Status').text
if status != 'OK':
    error = root.find('ErrorDescription').text
    raise WorkflowMaxError(f"API error: {error}")
```

## Common Patterns

### Retry Logic

```python
from time import sleep
from mtd_workflowmax.core.exceptions import APIError

def with_retry(func, max_retries=3, delay=1):
    """Retry function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except APIError as e:
            if attempt == max_retries - 1:
                raise
            sleep(delay * (2 ** attempt))
```

### Batch Updates

```python
def batch_update_fields(contact_uuid: str, updates: dict, batch_size=10):
    """Update fields in batches."""
    # Get current fields
    current = contact_service.get_contact(contact_uuid).custom_fields
    current_dict = {f.name: f.value for f in current}
    
    # Split updates into batches
    batches = []
    batch = {}
    for name, value in updates.items():
        batch[name] = value
        if len(batch) >= batch_size:
            batches.append(batch)
            batch = {}
    if batch:
        batches.append(batch)
    
    # Process each batch
    for batch in batches:
        current_dict.update(batch)
        contact_service.update_custom_fields(contact_uuid, current_dict)
```

### Field Value Formatting

```python
def format_field_value(field_type: str, value: Any) -> str:
    """Format field value for display."""
    if value is None:
        return "Not set"
        
    if field_type == "Boolean":
        return "Yes" if str(value).lower() == "true" else "No"
    elif field_type == "Date":
        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
            return dt.strftime("%d %b %Y")
        except ValueError:
            return value
    elif field_type == "Link":
        return f"<{value}>"
    
    return str(value)
