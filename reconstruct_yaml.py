#!/usr/bin/env python3
import yaml
from pathlib import Path

def load_yaml(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def reconstruct_yaml():
    base_dir = Path('api_spec')
    
    # Load base info
    result = load_yaml(base_dir / 'info.yaml')
    
    # Load paths
    result['paths'] = {}
    paths_dir = base_dir / 'paths'
    for path_file in paths_dir.glob('*.yaml'):
        path_data = load_yaml(path_file)
        result['paths'].update(path_data['paths'])
    
    # Load schemas
    result['components'] = {'schemas': {}}
    schemas_dir = base_dir / 'components' / 'schemas'
    for schema_file in schemas_dir.glob('*.yaml'):
        schema_data = load_yaml(schema_file)
        result['components']['schemas'].update(schema_data)
    
    # Write reconstructed file
    with open('workflowmax_api_reconstructed.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(result, f, sort_keys=False, allow_unicode=True)

if __name__ == '__main__':
    reconstruct_yaml()
    print("YAML file has been reconstructed as 'workflowmax_api_reconstructed.yaml'")
