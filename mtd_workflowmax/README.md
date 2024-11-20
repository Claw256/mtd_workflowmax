# WorkflowMax API Client

A Python client for the WorkflowMax API with support for contact management and LinkedIn integration.

## Installation

```bash
# From the root directory
pip install -e mtd_workflowmax/
```

## Environment Variables

Required environment variables:
```bash
# WorkflowMax OAuth2 credentials
WORKFLOWMAX_CLIENT_ID="your_client_id"
WORKFLOWMAX_CLIENT_SECRET="your_client_secret"

# For testing specific contacts
WORKFLOWMAX_TEST_CONTACT_UUID="contact_uuid"

# For LinkedIn integration (optional)
LINKEDIN_USERNAME="your_linkedin_username"
LINKEDIN_PASSWORD="your_linkedin_password"
```

## Usage

### 1. Command Line Interface

View contact details:
```bash
python -m mtd_workflowmax.cli
```

Update custom fields:
```bash
# Update LinkedIn profile
python -m mtd_workflowmax.cli set "LINKEDIN PROFILE" "https://linkedin.com/in/username"

# Update any custom field
python -m mtd_workflowmax.cli set "Field Name" "Field Value"
```

### 2. Python Module

Basic usage:
```python
from mtd_workflowmax import client

# Initialize the client
client.initialize()

# Get contact details
contact = client.contacts.get_contact("contact-uuid")
print(f"Contact: {contact.name}")

# Update custom fields
updates = {
    "LINKEDIN PROFILE": "https://linkedin.com/in/username",
    "Status": "Active"
}
client.contacts.update_custom_fields("contact-uuid", updates)
```

With LinkedIn integration:
```python
from mtd_workflowmax import client

# Initialize base client
client.initialize()

# Initialize LinkedIn integration
client.initialize_linkedin(
    username="linkedin_username",
    password="linkedin_password"
)

# Get contact
contact = client.contacts.get_contact("contact-uuid")

# Find LinkedIn profile
if linkedin_url := client.linkedin.find_linkedin_profile(contact):
    print(f"Found LinkedIn profile: {linkedin_url}")
    
    # Update contact's LinkedIn profile
    client.contacts.update_custom_fields(
        contact.uuid,
        {"LINKEDIN PROFILE": linkedin_url}
    )
```

### 3. Example Script

Here's a complete example that demonstrates key functionality:

```python
import os
import logging
from mtd_workflowmax import client
from mtd_workflowmax.core.exceptions import WorkflowMaxError

def main():
    try:
        # Initialize with debug logging
        client.initialize(log_level=logging.DEBUG)
        
        # Get test contact
        contact_uuid = os.getenv('WORKFLOWMAX_TEST_CONTACT_UUID')
        if not contact_uuid:
            print("Please set WORKFLOWMAX_TEST_CONTACT_UUID")
            return
            
        # Get contact details
        contact = client.contacts.get_contact(contact_uuid)
        print(f"\nContact: {contact.name}")
        
        # Get custom fields
        linkedin_url = contact.get_custom_field_value("LINKEDIN PROFILE")
        status = contact.get_custom_field_value("Status")
        print(f"LinkedIn: {linkedin_url or 'Not set'}")
        print(f"Status: {status or 'Not set'}")
        
        # Update fields
        updates = {
            "Status": "Active",
            "Is Info up-to-date?": "true"
        }
        if client.contacts.update_custom_fields(contact_uuid, updates):
            print("\nSuccessfully updated fields")
            
        # Try LinkedIn integration if credentials available
        linkedin_username = os.getenv('LINKEDIN_USERNAME')
        linkedin_password = os.getenv('LINKEDIN_PASSWORD')
        
        if linkedin_username and linkedin_password:
            client.initialize_linkedin(linkedin_username, linkedin_password)
            
            if not linkedin_url:  # Only search if no URL set
                if found_url := client.linkedin.find_linkedin_profile(contact):
                    print(f"\nFound LinkedIn profile: {found_url}")
                    
                    # Update profile URL
                    client.contacts.update_custom_fields(
                        contact_uuid,
                        {"LINKEDIN PROFILE": found_url}
                    )
                    
    except WorkflowMaxError as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
```

Save this as `example.py` and run:
```bash
python example.py
```

## Development

The module is organized into several packages:

- `api/` - API client and authentication
- `config/` - Configuration management
- `core/` - Core utilities and exceptions
- `models/` - Data models
- `repositories/` - Data access layer
- `services/` - Business logic

## Logging

Logs are written to `logs/workflowmax.log`. Set the log level when initializing:

```python
client.initialize(log_level=logging.DEBUG)  # For detailed logs
