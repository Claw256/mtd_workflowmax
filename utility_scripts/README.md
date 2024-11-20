# API Specification Utility Scripts

This directory contains utility scripts for managing OpenAPI/Swagger YAML specifications.

## Scripts

### 1. split_yaml.py

Splits a large OpenAPI YAML file into smaller, more manageable files organized by section (paths, schemas, etc.).

**Usage:**
```bash
python split_yaml.py input_file.yaml [--output-dir api_spec] [--verbose]
```

**Features:**
- Splits paths by tag into separate files
- Separates schema definitions
- Creates an organized directory structure
- Generates a reconstruction script
- Validates YAML structure
- Supports verbose logging

### 2. reconstruct_yaml.py

Reconstructs a single YAML file from the split components. This script is automatically generated by `split_yaml.py`.

**Usage:**
```bash
python reconstruct_yaml.py
```

**Features:**
- Combines all split YAML files back into a single file
- Preserves the original structure
- Maintains file organization

### 3. fix_api_descriptions.py

Adds or updates missing descriptions for API endpoint responses.

**Usage:**
```bash
python fix_api_descriptions.py
```

**Features:**
- Updates 200 response descriptions for specified endpoints
- Preserves existing response content
- Creates a backup of the original file
- Maintains YAML structure and formatting

## Common Use Cases

1. **Breaking Down Large API Specs:**
   - Use `split_yaml.py` to split a monolithic API spec into manageable pieces
   - Makes it easier to maintain and review changes
   - Improves version control efficiency

2. **Combining Split Specs:**
   - Use `reconstruct_yaml.py` to combine split files back into a single spec
   - Useful for distribution or when a single file is required

3. **Fixing API Documentation:**
   - Use `fix_api_descriptions.py` to add missing response descriptions
   - Improves API documentation quality
   - Maintains consistency across endpoints

## Requirements

- Python 3.x
- PyYAML library