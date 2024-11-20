"""Module for fetching WorkflowMax contact information."""

import os
import sys
from typing import Optional, Dict
import xml.etree.ElementTree as ET

from .models import Contact
from .client_manager import APIClientManager
from .custom_fields import CustomFieldManager
from .exceptions import AuthenticationError, WorkflowMaxAPIError
from .logging_config import get_logger

logger = get_logger('workflowmax.contact_fetcher')

def get_workflowmax_contact(UUID: str) -> Optional[Contact]:
    """Fetch contact details from WorkflowMax API.
    
    Args:
        UUID: The UUID of the contact to fetch
        
    Returns:
        Optional[Contact]: Contact object if found and parsed successfully
        
    Raises:
        WorkflowMaxAPIError: If API request fails
    """
    try:
        # Get authenticated API client
        client_manager = APIClientManager()
        with client_manager.get_client_context() as api_client:
            # Initialize custom field manager
            custom_field_manager = CustomFieldManager(api_client)
            
            # Get custom field definitions
            custom_field_defs = custom_field_manager.get_definitions()
            logger.info(f"Found {len(custom_field_defs)} custom field definitions")
            
            print("\nAvailable Custom Fields:")
            for field_def in custom_field_defs:
                print(f"- {field_def['Name']} ({field_def['Type']})")
            print()
            
            # Get contact details
            logger.info(f"Fetching contact details for UUID: {UUID}")
            response = api_client.get(f'client.api/contact/{UUID}')
            logger.info(f"Contact API response status: {response.status_code}")
            
            if not response.ok:
                logger.error(f"Failed to fetch contact {UUID}: {response.status_code}")
                return None
                
            contact_xml = ET.fromstring(response.text.encode('utf-8'))
            contact = Contact(contact_xml)
            logger.info(f"Successfully parsed contact: {contact.Name}")
            
            # Get custom fields
            contact.CustomFields = custom_field_manager.get_contact_fields(UUID)
            contact.custom_field_definitions = custom_field_defs
            logger.info(f"Found {len(contact.CustomFields)} custom fields")
            
            return contact
            
    except Exception as e:
        logger.error(f"Error fetching contact {UUID}: {str(e)}", exc_info=True)
        raise WorkflowMaxAPIError(f"Failed to fetch contact: {str(e)}")

def update_contact_custom_fields(UUID: str, updates: Dict[str, str]) -> bool:
    """Update custom field values for a contact.
    
    Args:
        UUID: The UUID of the contact to update
        updates: Dictionary mapping field names to their new values
        
    Returns:
        bool: True if update was successful
    """
    try:
        # Get authenticated API client
        client_manager = APIClientManager()
        with client_manager.get_client_context() as api_client:
            # Initialize custom field manager
            custom_field_manager = CustomFieldManager(api_client)
            
            # Update fields
            return custom_field_manager.update_fields(UUID, updates)
            
    except Exception as e:
        logger.error(f"Error updating custom fields for contact {UUID}: {str(e)}", exc_info=True)
        raise WorkflowMaxAPIError(f"Failed to update custom fields: {str(e)}")

def get_contact_custom_field(UUID: str, field_name: str) -> Optional[str]:
    """Get a specific custom field value for a contact.
    
    Args:
        UUID: The UUID of the contact
        field_name: Name of the field to get
        
    Returns:
        Optional[str]: Field value if found
    """
    contact = get_workflowmax_contact(UUID)
    if not contact:
        return None
    
    return contact.get_custom_field_value(field_name)

def print_usage():
    """Print script usage information."""
    print("\nUsage:")
    print("1. View contact details:")
    print("   python -m mtd_workflowmax.contact_fetcher")
    print("\n2. Update custom field:")
    print("   python -m mtd_workflowmax.contact_fetcher set \"Field Name\" \"Field Value\"")
    print("\nExample:")
    print("   python -m mtd_workflowmax.contact_fetcher set \"LINKEDIN PROFILE\" \"https://linkedin.com/in/username\"")
    print("   python -m mtd_workflowmax.contact_fetcher set \"Is Info up-to-date?\" \"true\"")

if __name__ == "__main__":
    # Example usage
    contact_uuid = os.getenv('WORKFLOWMAX_TEST_CONTACT_UUID')
    if not contact_uuid:
        print("Please set WORKFLOWMAX_TEST_CONTACT_UUID environment variable")
        sys.exit(1)
        
    try:
        if len(sys.argv) > 1:
            if sys.argv[1] == 'set' and len(sys.argv) == 4:
                field_name = sys.argv[2]
                field_value = sys.argv[3]
                
                # Update both fields to ensure they're in sync
                updates = {
                    field_name: field_value,
                    'Is Info up-to-date?': 'true'  # Set to true since we're updating info
                }
                
                if update_contact_custom_fields(contact_uuid, updates):
                    print(f"\nSuccessfully updated custom fields:")
                    for name, value in updates.items():
                        print(f"- {name}: {value}")
                else:
                    print(f"\nFailed to update custom fields")
                    print_usage()
            else:
                print_usage()
        else:
            # Get contact details
            contact = get_workflowmax_contact(contact_uuid)
            if contact:
                contact.print_details()
            else:
                print(f"Failed to fetch contact with UUID: {contact_uuid}")
            
    except AuthenticationError as e:
        print(f"Authentication error: {str(e)}")
    except WorkflowMaxAPIError as e:
        print(f"API error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
