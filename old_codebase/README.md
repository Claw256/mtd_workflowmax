# Legacy WorkflowMax API Testing Ground

⚠️ **DEPRECATED**: This directory contains experimental code that was used as a testing ground during early development. For the current implementation, please refer to the Python module in the `mtd_workflowmax/` directory.

This codebase provides a Python implementation for interacting with the WorkflowMax API, with additional LinkedIn integration capabilities. It handles API authentication, rate limiting, contact management, and custom field operations.

## Core Components

### API Client (`api_client.py`)
- Handles HTTP requests to the WorkflowMax API
- Implements rate limiting and connection pooling
- Manages authentication tokens and headers

### Authentication (`auth.py`)
- OAuth2 authentication implementation
- Token management (refresh, storage)
- Callback handler for OAuth flow

### Configuration (`config.py`)
- Configuration management for API, OAuth, and rate limiting
- Environment variable support
- Configuration validation

### Contact Management
- `contact_fetcher.py`: Fetches and updates WorkflowMax contacts
- `models.py`: Data models for contacts and related entities
- `custom_fields.py`: Management of custom fields for contacts

### LinkedIn Integration
- `linkedin_fetcher.py`: Fetches LinkedIn profile data
- `linkedin_matcher.py`: Matches WorkflowMax contacts with LinkedIn profiles

### Utilities
- `xml_parser.py`: XML parsing utilities for API responses
- `exceptions.py`: Custom exception handling
- `logging_config.py`: Logging configuration and management

## Error Handling

The codebase implements comprehensive error handling through custom exceptions:
- `WorkflowMaxAPIError`: Base exception class
- `AuthenticationError`: OAuth and token-related errors
- `RateLimitError`: API rate limit handling
- `ValidationError`: Data validation errors
- `ResourceNotFoundError`: 404 and missing resource handling
- `XMLParsingError`: XML parsing issues

## Rate Limiting

The API client includes built-in rate limiting to prevent exceeding WorkflowMax API limits:
- Configurable rate limits
- Automatic request throttling
- Rate limit metrics tracking

## Logging

Comprehensive logging system with:
- Console and file logging
- Custom formatting
- Log rotation
- Context-based filtering

## Usage Example

```python
# Initialize API client
client = APIClient()

# Fetch a contact
contact = get_workflowmax_contact("contact-uuid")

# Update custom fields
updates = {"LinkedIn": "https://linkedin.com/in/profile"}
update_contact_custom_fields("contact-uuid", updates)

# LinkedIn matching
matcher = LinkedInMatcher(username, password)
linkedin_profile = matcher.find_linkedin_profile(contact)
```

## Configuration

The system requires configuration for:
- WorkflowMax API credentials
- OAuth2 settings
- Rate limiting parameters
- LinkedIn API credentials (if using LinkedIn integration)

Configuration can be provided via environment variables or configuration files.

## Error Handling Example

```python
try:
    contact = get_workflowmax_contact("invalid-uuid")
except ResourceNotFoundError:
    logger.error("Contact not found")
except RateLimitError as e:
    logger.warning(f"Rate limit exceeded. Reset in {e.reset_time} seconds")
except WorkflowMaxAPIError as e:
    logger.error(f"API error: {str(e)}")
```

## Dependencies

- requests: HTTP client library
- lxml: XML processing
- python-dotenv: Environment variable management
- logging: Python standard logging

## Best Practices

This codebase follows several best practices:
- Comprehensive error handling
- Rate limiting and resource management
- Modular design with clear separation of concerns
- Extensive logging for debugging and monitoring
- Type hints for better code maintainability
- Configuration management with validation
