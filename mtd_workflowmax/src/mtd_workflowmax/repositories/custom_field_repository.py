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
from ..core.utils import Timer
from ..models import CustomFieldDefinition, CustomFieldType

logger = get_logger('workflowmax.repositories.custom_field')

class CustomFieldRepository:
    """Repository for custom field operations."""
    
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
                logger.debug(f"Cached definitions: {[d.name for d in self._definitions_cache]}")
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
                    for def_elem in definitions_elem.findall('CustomFieldDefinition'):
                        try:
                            # Parse field definition
                            logger.debug(f"Processing field definition: name={def_elem.find('Name').text} type={def_elem.find('Type').text}")
                            
                            # Map field type
                            field_type = def_elem.find('Type').text
                            if field_type == 'Checkbox':
                                logger.debug(f"Mapped Checkbox type to Boolean for field {def_elem.find('Name').text}")
                                field_type = 'Boolean'
                            
                            # Map to enum
                            try:
                                field_type_enum = CustomFieldType(field_type)
                                logger.debug(f"Mapped field type {field_type} to enum {field_type_enum}")
                            except ValueError:
                                logger.warning(f"Unknown field type: {field_type}")
                                continue
                            
                            definition = CustomFieldDefinition.from_xml(def_elem)
                            logger.debug(f"Successfully parsed field definition: {definition.name}")
                            definitions.append(definition)
                            
                        except Exception as e:
                            logger.warning(f"Failed to parse field definition: {str(e)}")
                            continue
                
                # Update cache
                self._definitions_cache = definitions
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
        age = Timer.get_age(self._cache_timestamp)
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
        
        # Validate each field
        for field_name, field_value in fields.items():
            try:
                if field_name not in definitions:
                    errors.append(f"Unknown field: {field_name}")
                    continue
                    
                self.validate_field_value(
                    field_name,
                    field_value,
                    definitions[field_name]
                )
                
            except ValidationError as e:
                errors.append(f"{field_name}: {str(e)}")
        
        return errors
