"""Command-line interface for WorkflowMax API."""

import os
import sys
import json
import argparse
import traceback
from typing import Optional
from . import WorkflowMax
from .core.exceptions import AuthenticationError, WorkflowMaxError
from .core.logging import get_logger, LogManager
from .services.custom_field_service import EntityType
from .services.linkedin_service import LinkedInService

logger = get_logger('workflowmax.cli')

def setup_argparse():
    """Set up argument parser."""
    parser = argparse.ArgumentParser(description='WorkflowMax API CLI')
    
    # Add global arguments
    parser.add_argument(
        '--log-level',
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info',
        help='Set the logging level'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Contact commands
    contact_parser = subparsers.add_parser('contact', help='Contact operations')
    contact_subparsers = contact_parser.add_subparsers(dest='subcommand')
    
    # View contact
    view_parser = contact_subparsers.add_parser('view', help='View contact details')
    view_parser.add_argument('uuid', help='Contact UUID')
    
    # Search contacts
    search_parser = contact_subparsers.add_parser('search', help='Search contacts')
    search_parser.add_argument('--query', help='Search query')
    search_parser.add_argument('--page', type=int, default=1, help='Page number')
    search_parser.add_argument('--page-size', type=int, default=50, help='Results per page')
    search_parser.add_argument('--include-custom-fields', action='store_true', help='Include custom fields')
    
    # Update custom field
    update_parser = contact_subparsers.add_parser('set-field', help='Update custom field')
    update_parser.add_argument('uuid', help='Contact UUID')
    update_parser.add_argument('field_name', help='Field name')
    update_parser.add_argument('field_value', help='Field value')
    
    return parser

def format_custom_field_value(field):
    """Format custom field value for display."""
    if field.value is None:
        return 'Not set'
    
    if field.type == 'Boolean':
        return 'Yes' if field.value.lower() == 'true' else 'No'
    elif field.type == 'Link':
        return f"<{field.value}>"
    else:
        return field.value

def handle_contact_command(wfm: WorkflowMax, args):
    """Handle contact-related commands."""
    if args.subcommand == 'view':
        # Get contact with custom fields included
        contact = wfm.contacts.get_contact(args.uuid, include_custom_fields=True)
        if contact:
            # Print basic contact details
            print("\nContact Details:")
            print(f"Name: {contact.name}")
            print(f"UUID: {contact.uuid}")
            if contact.email:
                print(f"Email: {contact.email}")
            if contact.mobile:
                print(f"Mobile: {contact.mobile}")
            if contact.phone:
                print(f"Phone: {contact.phone}")
            if contact.addressee:
                print(f"Addressee: {contact.addressee}")
            if contact.salutation:
                print(f"Salutation: {contact.salutation}")
            
            # Print positions (company relationships)
            if contact.positions:
                print("\nCompany Relationships:")
                for pos in contact.positions:
                    print(f"  Company: {pos.client_name}")
                    if pos.client_uuid:
                        print(f"  Company UUID: {pos.client_uuid}")
                    if pos.position:
                        print(f"  Position: {pos.position}")
                    if pos.is_primary:
                        print("  Primary Position: Yes")
                    if pos.include_in_emails:
                        print("  Include in Emails: Yes")
                    print()  # Add blank line between positions
            
            # Print custom fields
            if contact.custom_fields:
                print("Custom Fields:")
                for field in contact.custom_fields:
                    value = format_custom_field_value(field)
                    print(f"  {field.name}: {value}")
        else:
            print(f"Failed to fetch contact with UUID: {args.uuid}")
            
    elif args.subcommand == 'search':
        contacts = wfm.contacts.search_contacts(
            query=args.query,
            include_custom_fields=args.include_custom_fields,
            page=args.page,
            page_size=args.page_size
        )
        
        if contacts:
            print(f"\nFound {len(contacts)} contacts:")
            for contact in contacts:
                print(f"\n- {contact.name} ({contact.uuid})")
                if contact.email:
                    print(f"  Email: {contact.email}")
                
                # Print company info
                if contact.positions:
                    for pos in contact.positions:
                        print(f"  Company: {pos.client_name}")
                        if pos.position:
                            print(f"  Position: {pos.position}")
                        if pos.is_primary:
                            print("  Primary Position: Yes")
                
                # Print custom fields if requested
                if args.include_custom_fields and contact.custom_fields:
                    print("  Custom Fields:")
                    for field in contact.custom_fields:
                        value = format_custom_field_value(field)
                        print(f"    {field.name}: {value}")
        else:
            print("\nNo contacts found")
            
    elif args.subcommand == 'set-field':
        updates = {
            args.field_name: args.field_value,
            'Is Info up-to-date?': 'true'  # Always mark as up-to-date when updating
        }
        
        if wfm.contacts.update_custom_fields(args.uuid, updates):
            print(f"\nSuccessfully updated custom fields:")
            for name, value in updates.items():
                print(f"- {name}: {value}")
        else:
            print(f"\nFailed to update custom fields")

def main():
    """Main entry point for CLI."""
    parser = setup_argparse()
    args = parser.parse_args()
    
    # Set log level before any other operations
    LogManager.set_log_level(args.log_level)
    logger.debug(f"Log level set to {args.log_level}")
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        # Initialize client
        wfm = WorkflowMax()
        wfm.initialize()
        
        # Handle commands
        if args.command == 'contact':
            handle_contact_command(wfm, args)
            
    except AuthenticationError as e:
        print(f"Authentication error: {str(e)}")
        logger.error("Authentication error", error=str(e))
    except WorkflowMaxError as e:
        print(f"API error: {str(e)} (code: {e.error_code})")
        logger.error("API error", error=str(e), error_code=e.error_code)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        logger.error("Unexpected error", error=str(e), traceback=traceback.format_exc())

if __name__ == "__main__":
    main()
