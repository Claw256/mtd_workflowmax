# MTD WorkflowMax Integration

A Python module for integrating with the WorkflowMax API, providing robust contact management and custom field handling capabilities.

## Features

- OAuth2 authentication with WorkflowMax API
- Contact management (view, update)
- Custom field handling with proper XML formatting
- Type validation and conversion
- Comprehensive error handling
- Logging and debugging support

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure authentication:
- Copy `.env.template` to `.env`
- Fill in your WorkflowMax API credentials:
  ```
  WORKFLOWMAX_CLIENT_ID=your-client-id
  WORKFLOWMAX_CLIENT_SECRET=your-client-secret
  WORKFLOWMAX_REFRESH_TOKEN=your-refresh-token
  ```

3. Basic usage:
```bash
# View contact details
python -m mtd_workflowmax.cli contact view "contact-uuid"

# Update custom field
python -m mtd_workflowmax.cli contact set-field "contact-uuid" "LINKEDIN PROFILE" "https://www.linkedin.com/in/username"
```

## Documentation

Comprehensive documentation is available in the [docs/](docs/) directory:

- [Getting Started](docs/README.md) - Module overview and setup
- [Architecture](docs/architecture.md) - System design and components
- [API Integration](docs/api_integration.md) - WorkflowMax API details
- [Models](docs/models.md) - Data models and XML handling
- [Examples](docs/examples.md) - Code examples and common use cases

## Key Components

- `mtd_workflowmax/cli.py` - Command-line interface
- `mtd_workflowmax/services/` - Business logic layer
- `mtd_workflowmax/repositories/` - Data access layer
- `mtd_workflowmax/models/` - Data models and validation
- `mtd_workflowmax/api/` - API client and authentication

## Important Notes

When working with custom fields:
- XML tag order matters (UUID must come first)
- All custom fields must be included in updates
- Link URLs should be preserved in their original format
- Include UUIDs in custom field updates

## Development

1. Clone the repository:
```bash
git clone https://github.com/Claw256/mtd_workflowmax.git
cd mtd_workflowmax
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Contributing

1. Follow the existing code structure and patterns
2. Add tests for new functionality
3. Update documentation as needed
4. Submit pull requests for review

## License

Internal use only - All rights reserved
