import yaml
import sys
import shutil
from typing import Dict, Any

def update_endpoint_description(paths: Dict[str, Any], path: str, method: str, description: str) -> None:
    """Update the description for a specific endpoint's 200 response."""
    if path in paths and method in paths[path]:
        if '200' in paths[path][method].get('responses', {}):
            # Create a new response object with description
            new_response = {
                'description': description
            }
            
            # Preserve content if it exists
            if 'content' in paths[path][method]['responses']['200']:
                new_response['content'] = paths[path][method]['responses']['200']['content']
            
            # Update the response
            paths[path][method]['responses']['200'] = new_response
            print(f"Updated description for {method.upper()} {path}")

def fix_descriptions(api_spec: Dict[str, Any]) -> None:
    """Add missing descriptions to API endpoints."""
    
    # Dictionary mapping endpoints to their descriptions
    descriptions = {
        ("/job.api/delete", "post"): "Successfully deleted the job",
        ("/job.api/document", "post"): "Successfully uploaded document to job",
        ("/job.api/note", "post"): "Successfully added note to job",
        ("/job.api/reordertasks", "put"): "Successfully reordered tasks",
        ("/job.api/staff/{uuid}", "get"): "Successfully retrieved staff member details",
        ("/job.api/task", "put"): "Successfully updated task",
        ("/job.api/task", "post"): "Successfully created new task",
        ("/job.api/tasks", "get"): "Successfully retrieved list of tasks",
        ("/job.api/task/{uuid}/complete", "put"): "Successfully marked task as complete",
        ("/job.api/task/{uuid}/reopen", "put"): "Successfully reopened task",
        ("/lead.api/add", "post"): "Successfully created new lead",
        ("/purchaseorder.api/add", "post"): "Successfully created new purchase order",
        ("/purchaseorder.api/adddraft", "post"): "Successfully created draft purchase order",
        ("/purchaseorder.api/list", "get"): "Successfully retrieved list of purchase orders"
    }
    
    paths = api_spec.get('paths', {})
    for (path, method), description in descriptions.items():
        update_endpoint_description(paths, path, method, description)

def main():
    """Main function to read YAML, update descriptions, and write to new file."""
    input_file = 'workflowmax_api.yaml'
    output_file = 'workflowmax_api_fixed.yaml'
    
    try:
        # First make a copy of the original file
        shutil.copy2(input_file, output_file)
        print(f"Created backup copy: {output_file}")
        
        # Read the YAML file
        with open(output_file, 'r', encoding='utf-8') as file:
            api_spec = yaml.safe_load(file)
        
        # Update the descriptions
        fix_descriptions(api_spec)
        
        # Write the updated YAML back to the new file
        with open(output_file, 'w', encoding='utf-8', newline='\n') as file:
            yaml.dump(api_spec, file, allow_unicode=True, sort_keys=False)
            
        print(f"Successfully updated API descriptions in {output_file}")
        
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error reading/writing file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
