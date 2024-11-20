# WorkflowMax LinkedIn Profile Fetcher

A Python script to fetch LinkedIn profiles from WorkflowMax contacts with support for parallel processing, caching, and multiple output formats.

## Features

- Parallel contact processing for improved performance
- Custom field caching to reduce API calls
- Rate limiting and retry mechanisms
- Multiple output formats (JSON/CSV)
- Progress tracking with progress bar
- Configurable settings via YAML file
- Detailed logging with different log levels
- Type hints for better code maintainability

## Requirements

```bash
pip install requests pyjwt python-dotenv pyyaml tqdm
```

## Configuration

The script can be configured using `config.yml`:

```yaml
max_workers: 5              # Maximum number of parallel workers
max_retries: 3             # Maximum retry attempts for failed requests
requests_per_second: 2     # Rate limiting for API requests

logging:
  level: INFO
  file: workflowmax.log   # Optional log file

custom_fields:
  linkedin_field_name: "LINKEDIN PROFILE"
  enable_caching: true
  max_cache_size: 1000

output:
  default_format: json
  include_custom_fields: true
  directory: output
```

## Environment Variables

Create a `.env` file with your WorkflowMax API credentials:

```
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
```

## Usage

Basic usage:
```bash
python workflowmax_linkedin.py
```

With options:
```bash
python workflowmax_linkedin.py --limit 100 --format csv
```

Available options:
- `--limit`: Maximum number of contacts to process
- `--start`: Page number to start from (default: 1)
- `--client`: Only process contacts from a specific client
- `--format`: Output format (json or csv, default: json)

## Output

The script generates either a JSON or CSV file containing:
- Contact information (name, email, phone, etc.)
- Client name
- LinkedIn profile URL
- Custom fields (optional)

Example JSON output:
```json
[
  {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "123-456-7890",
    "mobile": "098-765-4321",
    "position": "Manager",
    "is_primary": "true",
    "client_name": "Example Corp",
    "linkedin_url": "https://linkedin.com/in/johndoe",
    "custom_fields": [
      ["LINKEDIN PROFILE", "https://linkedin.com/in/johndoe"],
      ["OTHER FIELD", "value"]
    ]
  }
]
```

## Error Handling

The script includes robust error handling:
- Retries for transient network issues
- Rate limiting to prevent API throttling
- Specific exception types for different errors
- Detailed error logging

## Logging

Default logging level is INFO, which shows:
- Processing progress
- Custom fields responses
- LinkedIn URL status for each contact
- Summary statistics

Debug logging (if enabled) shows:
- API responses
- Detailed processing information
- Cache operations
- Rate limiting details

## Performance Optimization

The script optimizes performance through:
1. Parallel processing of contacts using ThreadPoolExecutor
2. Caching of custom field definitions
3. Rate limiting to prevent API throttling
4. Efficient API calls with pagination

## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License
