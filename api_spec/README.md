# WorkflowMax API Specification

This directory contains the split components of the WorkflowMax API specification. The original YAML file has been divided into smaller, more manageable files for easier maintenance and version control.

## Directory Structure

- `info.yaml` - Contains the API metadata, servers configuration, and tags
- `paths/` - API endpoints split by tag/category
  - `category.yaml` - Category-related endpoints
  - `client.yaml` - Client-related endpoints
  - `client_group.yaml` - Client group-related endpoints
  - `cost.yaml` - Cost-related endpoints
  - `custom_field.yaml` - Custom field-related endpoints
  - `invoice.yaml` - Invoice-related endpoints
  - `job.yaml` - Job-related endpoints
  - `lead.yaml` - Lead-related endpoints
  - `purchase_order.yaml` - Purchase order-related endpoints
  - `quote.yaml` - Quote-related endpoints
  - `staff.yaml` - Staff-related endpoints
  - `supplier.yaml` - Supplier-related endpoints
  - `task.yaml` - Task-related endpoints
  - `template.yaml` - Template-related endpoints
  - `time.yaml` - Time-related endpoints
- `components/` - Reusable components
  - `schemas.yaml` - Data models and schemas

## Usage

### Reconstructing the Original File

To combine all the files back into a single OpenAPI specification:

```bash
python reconstruct_yaml.py
```

This will create `workflowmax_api_reconstructed.yaml` in the root directory.

### Making Changes

1. Each endpoint is in its own file under the `paths/` directory, organized by tag
2. Common schemas and components are in the `components/` directory
3. Base API information is in `info.yaml`

Make changes to the relevant files and use the reconstruction script to rebuild the complete specification.
