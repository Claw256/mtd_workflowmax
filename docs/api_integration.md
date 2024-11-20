# WorkflowMax API Integration

This document details how the `mtd_workflowmax` module integrates with the WorkflowMax API, focusing on authentication, request/response formats, and common challenges.

## Authentication

The module uses OAuth2 for API authentication:

```python
from mtd_workflowmax.api.auth import OAuthManager

auth_manager = OAuthManager()
token = auth_manager.get_token()
```

Required environment variables:
```bash
WORKFLOWMAX_CLIENT_ID=your-client-id
WORKFLOWMAX_CLIENT_SECRET=your-client-secret
WORKFLOWMAX_REFRESH_TOKEN=your-refresh-token
```

## API Endpoints

Base URL: `https://api.workflowmax2.com/`

### Contact Endpoints

1. Get Contact
```
GET client.api/contact/{uuid}
```

2. Update Contact Custom Fields
```
PUT client.api/contact/{uuid}/customfield
```

### Custom Field Endpoints

1. Get Definitions
```
GET customfield.api/definition
```

## XML Requirements

### Custom Field Updates

The most critical aspect of the API integration is proper XML formatting for custom field updates. The order of XML tags matters and all fields must be included.

#### Correct Format:
```xml
<CustomFields>
  <CustomField>
    <UUID>field-uuid</UUID>      <!-- UUID must come first -->
    <Name>field-name</Name>      <!-- Name comes second -->
    <Type>field-type</Type>      <!-- Type comes third -->
    <Value>field-value</Value>   <!-- Value comes last -->
  </CustomField>
</CustomFields>
```

#### Common Mistakes:
```xml
<!-- Wrong: Missing UUID -->
<CustomField>
  <Name>field-name</Name>
  <Type>field-type</Type>
  <Value>field-value</Value>
</CustomField>

<!-- Wrong: Incorrect tag order -->
<CustomField>
  <Name>field-name</Name>
  <UUID>field-uuid</UUID>
  <Type>field-type</Type>
  <Value>field-value</Value>
</CustomField>
```

### Link Type Fields

Link type fields require special handling:

1. Definition Format:
```xml
<CustomFieldDefinition>
  <UUID>field-uuid</UUID>
  <Name>LINKEDIN PROFILE</Name>
  <Type>Link</Type>
  <LinkURL>https://{value}</LinkURL>
</CustomFieldDefinition>
```

2. Update Format:
```xml
<CustomField>
  <UUID>field-uuid</UUID>
  <Name>LINKEDIN PROFILE</Name>
  <Type>Link</Type>
  <LinkURL>https://www.linkedin.com/in/username</LinkURL>
</CustomField>
```

Key points:
- Preserve the full URL in updates
- Don't apply the template when sending updates
- Include the UUID from the field definition

## Error Handling

### API Error Responses

1. Authentication Error:
```xml
<Response>
  <Status>Error</Status>
  <ErrorDescription>Invalid access token</ErrorDescription>
</Response>
```

2. Validation Error:
```xml
<Response>
  <Status>Error</Status>
  <ErrorDescription>Invalid field value</ErrorDescription>
</Response>
```

### Error Handling Strategy

```python
try:
    response = api_client.put(endpoint, data=xml_payload)
    root = ET.fromstring(response.text)
    status = root.find('Status').text
    
    if status != 'OK':
        error = root.find('ErrorDescription').text
        raise WorkflowMaxError(f"API error: {error}")
        
except ET.ParseError as e:
    raise XMLParsingError(f"Invalid XML response: {str(e)}")
except requests.RequestException as e:
    raise APIError(f"Request failed: {str(e)}")
```

## Rate Limiting

The API has rate limits that must be respected:

- 1000 requests per hour
- 10 requests per second

Implementation:
```python
from time import sleep

class RateLimiter:
    def __init__(self):
        self.last_request = 0
        self.min_interval = 0.1  # 100ms between requests
        
    def wait(self):
        now = time.time()
        elapsed = now - self.last_request
        if elapsed < self.min_interval:
            sleep(self.min_interval - elapsed)
        self.last_request = time.time()
```

## Debugging Tips

1. Enable Debug Logging:
```python
import logging
logging.getLogger('workflowmax').setLevel(logging.DEBUG)
```

2. Log Request/Response:
```python
logger.debug(f"Request XML: {xml_payload}")
logger.debug(f"Response: {response.text}")
```

3. Common Issues:

- XML Formatting:
  ```python
  # Wrong
  f"<Value>{value}</Value>"
  
  # Right
  f"<Value>{sanitize_xml(value)}</Value>"
  ```

- Link URLs:
  ```python
  # Wrong
  link_url.replace('{value}', url)
  
  # Right
  url  # Keep original URL format
  ```

- Custom Field Updates:
  ```python
  # Wrong
  update_single_field(uuid, name, value)
  
  # Right
  update_all_fields(uuid, {name: value})
  ```

## Testing

Use the provided test environment:

```bash
WORKFLOWMAX_API_URL=https://api.workflowmax2.com/test/
```

Test data:
```python
TEST_CONTACT_UUID = "test-contact-uuid"
TEST_CUSTOM_FIELD = {
    "name": "TEST FIELD",
    "type": "Text",
    "value": "test value"
}
```

## Best Practices

1. Always validate XML before sending:
```python
def validate_xml(xml_string: str) -> bool:
    try:
        ET.fromstring(xml_string)
        return True
    except ET.ParseError:
        return False
```

2. Include all required fields:
```python
def validate_required_fields(custom_field: dict) -> None:
    required = ['UUID', 'Name', 'Type']
    missing = [f for f in required if f not in custom_field]
    if missing:
        raise ValidationError(f"Missing required fields: {missing}")
```

3. Handle special characters:
```python
def sanitize_xml(value: str) -> str:
    return value.replace('&', '&amp;') \
                .replace('<', '&lt;') \
                .replace('>', '&gt;') \
                .replace('"', '&quot;') \
                .replace("'", '&apos;')
```

4. Verify updates:
```python
def verify_update(uuid: str, updates: dict) -> bool:
    contact = get_contact(uuid)
    return all(
        contact.custom_fields[name].value == value
        for name, value in updates.items()
    )
