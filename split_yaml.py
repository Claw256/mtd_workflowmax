#!/usr/bin/env python3
import yaml
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, Any

def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def validate_yaml_structure(data: Dict[str, Any]) -> bool:
    """Validate the basic structure of the OpenAPI YAML file"""
    required_fields = ['openapi', 'info', 'paths']
    for field in required_fields:
        if field not in data:
            logging.error(f"Missing required field: {field}")
            return False
    return True

def split_schemas(schemas: Dict[str, Any], output_dir: Path) -> None:
    """Split schemas into individual files by type"""
    if not schemas:
        return

    schemas_dir = output_dir / 'components' / 'schemas'
    schemas_dir.mkdir(parents=True, exist_ok=True)
    
    # Create an index file for schemas
    schema_index = {'schemas': {}}
    
    for schema_name, schema_data in schemas.items():
        # Write individual schema file
        schema_file = schemas_dir / f'{schema_name.lower()}.yaml'
        logging.info(f"Writing schema {schema_name} to {schema_file}")
        with schema_file.open('w', encoding='utf-8') as f:
            yaml.dump({schema_name: schema_data}, f, sort_keys=False, allow_unicode=True)
        
        # Add reference to index
        schema_index['schemas'][schema_name] = f'./schemas/{schema_name.lower()}.yaml#{schema_name}'
    
    # Write schema index file
    index_file = output_dir / 'components' / 'schemas.yaml'
    logging.info(f"Writing schema index to {index_file}")
    with index_file.open('w', encoding='utf-8') as f:
        yaml.dump(schema_index, f, sort_keys=False, allow_unicode=True)

def split_paths_by_tag(paths: Dict[str, Any], output_dir: Path) -> None:
    """Split paths into separate files by tag"""
    if not paths:
        return

    paths_dir = output_dir / 'paths'
    paths_dir.mkdir(exist_ok=True)
    
    paths_by_tag = {}
    untagged_paths = {'paths': {}}

    # Group paths by tag
    for path, path_data in paths.items():
        tag_found = False
        for operation in path_data.values():
            if isinstance(operation, dict) and 'tags' in operation and operation['tags']:
                tag = operation['tags'][0]
                if tag not in paths_by_tag:
                    paths_by_tag[tag] = {'paths': {}}
                paths_by_tag[tag]['paths'][path] = path_data
                tag_found = True
                break
        
        if not tag_found:
            untagged_paths['paths'][path] = path_data

    # Write paths by tag
    for tag, tag_data in paths_by_tag.items():
        output_file = paths_dir / f'{tag.lower().replace(" ", "_")}.yaml'
        logging.info(f"Writing paths/{tag} to {output_file}")
        with output_file.open('w', encoding='utf-8') as f:
            yaml.dump(tag_data, f, sort_keys=False, allow_unicode=True)

    # Write untagged paths if any exist
    if untagged_paths['paths']:
        output_file = paths_dir / 'untagged.yaml'
        logging.info(f"Writing untagged paths to {output_file}")
        with output_file.open('w', encoding='utf-8') as f:
            yaml.dump(untagged_paths, f, sort_keys=False, allow_unicode=True)

def write_base_info(data: Dict[str, Any], output_dir: Path) -> None:
    """Write base OpenAPI info to a file"""
    base_info = {
        'openapi': data.get('openapi'),
        'info': data.get('info', {}),
        'servers': data.get('servers', []),
        'tags': data.get('tags', [])
    }
    
    output_file = output_dir / 'info.yaml'
    logging.info(f"Writing base info to {output_file}")
    with output_file.open('w', encoding='utf-8') as f:
        yaml.dump(base_info, f, sort_keys=False, allow_unicode=True)

def create_reconstruction_script(output_dir: Path) -> None:
    """Create a script to reconstruct the original YAML file"""
    script_content = '''#!/usr/bin/env python3
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
'''
    
    output_file = output_dir.parent / 'reconstruct_yaml.py'
    logging.info(f"Writing reconstruction script to {output_file}")
    with output_file.open('w', encoding='utf-8') as f:
        f.write(script_content)
    
    # Make the script executable on Unix-like systems
    if os.name != 'nt':
        os.chmod(output_file, 0o755)

def split_yaml_file(input_file: str, output_dir: str, verbose: bool = False) -> None:
    """Split a large YAML file into smaller files by section"""
    setup_logging(verbose)
    
    input_path = Path(input_file)
    output_path = Path(output_dir)
    
    if not input_path.exists():
        logging.error(f"Input file not found: {input_file}")
        sys.exit(1)
    
    try:
        logging.info(f"Reading input file: {input_file}")
        with input_path.open('r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not validate_yaml_structure(data):
            logging.error("Invalid YAML structure")
            sys.exit(1)
        
        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Split the file into sections
        write_base_info(data, output_path)
        split_paths_by_tag(data.get('paths', {}), output_path)
        split_schemas(data.get('components', {}).get('schemas', {}), output_path)
        
        # Create reconstruction script
        create_reconstruction_script(output_path)
        
        logging.info(f"YAML file has been split into sections in the '{output_dir}' directory")
        logging.info("Use reconstruct_yaml.py to rebuild the original file if needed")
        
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML file: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Split a large YAML file into smaller files by section')
    parser.add_argument('input_file', help='Input YAML file to split')
    parser.add_argument('--output-dir', '-o', default='api_spec',
                      help='Output directory for split files (default: api_spec)')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Enable verbose logging')
    
    args = parser.parse_args()
    split_yaml_file(args.input_file, args.output_dir, args.verbose)

if __name__ == '__main__':
    main()
