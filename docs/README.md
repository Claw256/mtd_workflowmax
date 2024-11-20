# MTD WorkflowMax Python Module

A Python module for interacting with the WorkflowMax API, providing a clean interface for managing contacts, custom fields, and other WorkflowMax resources.

## Overview

The `mtd_workflowmax` module provides a high-level Python interface to the WorkflowMax API, handling authentication, request/response formatting, and data validation. It implements a repository pattern for clean separation of concerns and maintainable code.

## Key Features

- OAuth2 authentication with WorkflowMax API
- Contact management (view, update)
- Custom field handling with proper XML formatting
- Type validation and conversion
- Comprehensive error handling
- Logging and debugging support

## Getting Started

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure authentication:
- Copy `.env.template` to `.env`
- Fill in your WorkflowMax API credentials

3. Basic usage:
```python
from mtd_workflowmax.api import WorkflowMaxClient
from mtd_workflowmax.services import ContactService

# Initialize client
client = WorkflowMaxClient()

# Create service
contact_service = ContactService(client)

# View contact
contact = contact_service.get_contact("contact-uuid")
print(contact.name)

# Update custom field
contact_service.update_custom_fields("contact-uuid", {
    "LINKEDIN PROFILE": "https://www.linkedin.com/in/username"
})
```

## Documentation Structure

- [Architecture](architecture.md) - System design and component overview
- [API Integration](api_integration.md) - WorkflowMax API integration details
- [Models](models.md) - Data models and XML handling
- [Examples](examples.md) - Code examples and common use cases

## Important Notes

- XML tag order matters when updating custom fields
- All custom fields must be included in update requests
- Link URLs should be preserved in their original format
- UUIDs must be included in custom field updates

## Contributing

1. Follow the existing code structure and patterns
2. Add tests for new functionality
3. Update documentation as needed
4. Submit pull requests for review

## License

MIT License

Copyright (c) 2024 Munster Tool & Die
