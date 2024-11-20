"""Repository for managing WorkflowMax custom fields."""

from typing import Optional, List, Dict, Any
import xml.etree.ElementTree as ET
import re
from datetime import datetime

from ..core.exceptions import (
    ValidationError,
    XMLParsingError,
    WorkflowMaxError,
    CustomFieldError
)
from ..core.logging import get_logger, with_logging
from ..core.utils import Timer, get_cache_age
from ..models import CustomFieldDefinition, CustomFieldType

logger = get_logger('workflowmax.repositories.custom_field')

class CustomFieldRepository:
    """Repository for custom field operations."""
    
    # Map API field types to our enum types
    TYPE_MAPPING = {
        'Checkbox': 'Boolean',           # Map checkbox inputs to boolean type
        'Single Line Text': 'Text',      # Map single line inputs to text type
        'TextArea': 'Multi-line Text',   # Map text areas to multi-line text
        'Numeric': 'Number',             # Map numeric inputs to number type
        'Currency': 'Decimal',           # Map currency inputs to decimal type
        'URL': 'Link',                   # Map URL inputs to link type
        'DatePicker': 'Date',            # Map date pickers to date type
        'DropDown': 'Select'             # Map dropdowns to select type
    }
    
    def __init__(self, api_client):
        """Initialize repository.
        
        Args:
            api_client: Initialized API client instance
        """
        self.api_client = api_client
        self._definitions_cache = None
        self._cache_timestamp = None
        logger.debug("Initialized CustomFieldRepository")
    
    @with_logging
    def get_definitions(self, force_refresh: bool = False) -> List[CustomFieldDefinition]:
        """Get custom field definitions.
        
        Args:
            force_refresh: Whether to force refresh the cache
            
        Returns:
            List of custom field definitions
            
        Raises:
            WorkflowMaxError: If API request fails
        """
        with Timer("Get custom field definitions"):
            # Check cache first
            if not force_refresh and self._is_cache_valid():
                logger.debug("Using cached custom field definitions")
                for definition in self._definitions_cache:
                    logger.debug(f"Cached definition: name={definition.name} type={definition.type}")
                return self._definitions_cache
            
            # Cache is empty or expired, fetch from API
            logger.debug(f"Fetching custom field definitions (force_refresh={force_refresh})")
            
            try:
                response = self.api_client.get('customfield.api/definition')
                logger.debug(f"Raw API response: {response.text}")
                
                xml_root = ET.fromstring(response.text.encode('utf-8'))
                definitions = []
                
                definitions_elem = xml_root.find('CustomFieldDefinitions')
                if definitions_elem is not None:
                    logger.debug(f"Found {len(definitions_elem)} custom field definitions")
                    for def_elem in definitions_elem.findall('CustomFieldDefinition'):
                        try:
                            # Get field name and type
                            name = def_elem.find('Name').text
                            field_type = def_elem.find('Type').text
                            logger.debug(f"Processing field: name={name} original_type={field_type}")
                            
                            # Map field type if needed
                            if field_type in self.TYPE_MAPPING:
                                mapped_type = self.TYPE_MAPPING[field_type]
                                logger.debug(f"Mapping field type {field_type} -> {mapped_type} for field {name}")
                                # Create a new Type element with mapped value
                                type_elem = ET.Element('Type')
                                type_elem.text = mapped_type
                                # Replace original Type element
                                old_type = def_elem.find('Type')
                                def_elem.remove(old_type)
                                def_elem.append(type_elem)
                            else:
                                logger.debug(f"No type mapping needed for {field_type}")
                            
                            # Parse field definition
                            definition = CustomFieldDefinition.from_xml(def_elem)
                            logger.debug(f"Successfully parsed field definition: name={definition.name} type={definition.type}")
                            
                            # Log usage flags
                            usage = []
                            if definition.use_client:
                                usage.append('client')
                            if definition.use_contact:
                                usage.append('contact')
                            if definition.use_supplier:
                                usage.append('supplier')
                            if definition.use_job:
                                usage.append('job')
                            if definition.use_lead:
                                usage.append('lead')
                            logger.debug(f"Field {definition.name} usage: {', '.join(usage)}")
                            
                            definitions.append(definition)
                            
                        except Exception as e:
                            logger.warning(
                                f"Failed to parse field definition",
                                name=name if 'name' in locals() else 'unknown',
                                error=str(e)
                            )
                            continue
                
                # Update cache
                self._definitions_cache = definitions
                self._cache_timestamp = datetime.now().timestamp()
                logger.debug(f"Updated definitions cache with {len(definitions)} fields")
                
                return definitions
                
            except Exception as e:
                logger.error(f"Failed to get custom field definitions: {str(e)}")
                raise WorkflowMaxError(f"Failed to get custom field definitions: {str(e)}")
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is valid."""
        if self._definitions_cache is None:
            logger.debug("Cache is empty or timestamp missing")
            return False
            
        # Get cache age in seconds
        age = get_cache_age(self._cache_timestamp)
        logger.debug(f"Cache age: {age:.2f}s valid: {age < 300}")
        
        # Cache is valid for 5 minutes
        return age < 300
    
    @with_logging
    def validate_field_value(
        self,
        field_name: str,
        field_value: str,
        definition: CustomFieldDefinition
    ) -> bool:
        """Validate a field value against its definition.
        
        Args:
            field_name: Name of the field
            field_value: Value to validate
            definition: Field definition to validate against
            
        Returns:
            True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            logger.debug(f"Validating field: name={field_name} value={field_value}")
            logger.debug(f"Validating against definition: type={definition.type} required={definition.required}")
            
            # Remove any XML tags
            field_value = re.sub(r'<[^>]+>', '', field_value)
            
            # Check required fields
            if definition.required and not field_value:
                raise ValidationError(f"Field {field_name} is required")
            
            # Skip validation if empty and not required
            if not field_value and not definition.required:
                return True
            
            # Validate based on type
            if definition.type == CustomFieldType.BOOLEAN:
                logger.debug(f"Validating boolean value: {field_value}")
                if field_value.lower() not in ('true', 'false'):
                    raise ValidationError("Boolean value must be 'true' or 'false'")
                    
            elif definition.type == CustomFieldType.NUMBER:
                logger.debug(f"Validating number value: {field_value}")
                try:
                    int(float(field_value))  # Allow float input but ensure it's whole number
                except ValueError:
                    raise ValidationError("Value must be a whole number")
                    
            elif definition.type == CustomFieldType.DECIMAL:
                logger.debug(f"Validating decimal value: {field_value}")
                try:
                    float(field_value)
                except ValueError:
                    raise ValidationError("Value must be a decimal number")
                    
            elif definition.type == CustomFieldType.DATE:
                logger.debug(f"Validating date value: {field_value}")
                try:
                    # Support both date-only and full datetime formats
                    try:
                        datetime.strptime(field_value, '%Y-%m-%d')
                    except ValueError:
                        datetime.strptime(field_value, '%Y-%m-%d %H:%M:%S%z')
                except ValueError:
                    raise ValidationError("Invalid date format (use YYYY-MM-DD)")
                    
            elif definition.type == CustomFieldType.LINK:
                logger.debug(f"Validating link value: {field_value}")
                # Add https:// prefix if not present
                if not field_value.startswith(('http://', 'https://', 'www.')):
                    field_value = 'https://' + field_value
                
            logger.debug(f"Field {field_name} validation successful")
            return True
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            raise ValidationError(f"Invalid value for field {field_name}: {str(e)}")
    
    @with_logging
    def validate_fields(self, fields: Dict[str, str]) -> List[str]:
        """Validate multiple field values.
        
        Args:
            fields: Dictionary mapping field names to values
            
        Returns:
            List of validation error messages (empty if all valid)
        """
        errors = []
        
        # Get field definitions
        definitions = {d.name: d for d in self.get_definitions()}
        logger.debug(f"Loaded {len(definitions)} field definitions for validation")
        
        # Validate each field
        for field_name, field_value in fields.items():
            try:
                if field_name not in definitions:
                    logger.warning(f"Unknown field: {field_name}")
                    errors.append(f"Unknown field: {field_name}")
                    continue
                    
                definition = definitions[field_name]
                logger.debug(f"Validating field {field_name} with type {definition.type}")
                
                self.validate_field_value(
                    field_name,
                    field_value,
                    definition
                )
                
            except ValidationError as e:
                logger.warning(f"Validation failed for field {field_name}: {str(e)}")
                errors.append(f"{field_name}: {str(e)}")
        
        if errors:
            logger.warning(f"Found {len(errors)} validation errors")
        else:
            logger.debug("All fields validated successfully")
        
        return errors
