"""Main LinkedIn profile fetching logic for MTD's WorkflowMax 2 API client."""

import asyncio
from typing import Dict, List, Optional, Generator, AsyncGenerator, Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from cachetools import TTLCache, cached
from lxml import etree
from tqdm import tqdm

from .api_client import APIClient
from .models import Client, Contact, CustomField
from .logging_config import get_logger
from . import metrics

# Set up logger for this module
logger = get_logger('workflowmax.linkedin_fetcher')

# Configure caches with TTL of 1 hour (3600 seconds)
CUSTOM_FIELDS_CACHE = TTLCache(maxsize=5000, ttl=3600)  # Increased cache size
XML_CACHE = TTLCache(maxsize=500, ttl=3600)  # Increased cache size

class LinkedInProfileFetcher:
    """Main class for fetching LinkedIn profiles from WorkflowMax."""
    
    def __init__(self, api_client: APIClient, config: Dict):
        """Initialize the LinkedIn profile fetcher."""
        self.api_client = api_client
        self.config = config
        
        # Pre-compile XPath expressions for better performance
        self.custom_field_xpath = etree.XPath(".//CustomFieldDefinition")
        self.client_xpath = etree.XPath(".//Client")
        self.value_xpath = etree.XPath(".//Value/text()|.//LinkURL/text()|.//Text/text()|.//Boolean/text()|.//Number/text()|.//Decimal/text()")
        self.name_xpath = etree.XPath(".//Name/text()")
        
        # Initialize caches
        self.custom_fields_cache = CUSTOM_FIELDS_CACHE
        self.xml_cache = XML_CACHE
        
        # Batch processing settings
        self.batch_size = 50  # Batch size for contacts
        self.max_workers = config.get('max_workers', 40)  # Increased default workers
        self.page_size = 250  # Page size for client list
        
        # Create a single thread pool for reuse
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
    
    def _parse_xml(self, xml_text: str) -> etree._Element:
        """Parse XML text using lxml for better performance."""
        try:
            return etree.fromstring(xml_text.encode('utf-8'))
        except etree.XMLSyntaxError as e:
            logger.error("Failed to parse XML: %s", e)
            raise
    
    def get_custom_field_definitions(self) -> List[CustomField]:
        """Get all custom field definitions with caching."""
        logger.info("Fetching custom field definitions")
        try:
            response = self.api_client.get('customfield.api/definition')
            definitions_xml = self._parse_xml(response.text)
            definitions = []
            
            for definition in self.custom_field_xpath(definitions_xml):
                custom_field = CustomField(definition)
                definitions.append(custom_field)
                logger.debug("Found custom field definition: %s", custom_field.to_dict())
            
            logger.info("Retrieved %d custom field definitions", len(definitions))
            return definitions
            
        except Exception as e:
            logger.error("Failed to get custom field definitions: %s", e)
            raise
    
    def get_field_value(self, field: etree._Element) -> str:
        """Extract the value from a custom field XML element using XPath."""
        try:
            values = self.value_xpath(field)
            if values:
                value = values[0]
                if value.lower() in ('true', 'false'):
                    return value.lower()
                return value
            return ""
        except Exception as e:
            logger.error("Failed to extract field value: %s", e)
            return ""
    
    def get_contact_custom_fields(self, contact_uuid: str) -> List[Dict[str, str]]:
        """Get custom fields for a contact with caching."""
        try:
            # Check cache first
            if contact_uuid in self.custom_fields_cache:
                return self.custom_fields_cache[contact_uuid]
            
            response = self.api_client.get(f'client.api/contact/{contact_uuid}/customfield')
            custom_fields_xml = self._parse_xml(response.text)
            custom_fields = []
            
            for field in custom_fields_xml.findall('.//CustomField'):
                names = self.name_xpath(field)
                if names:
                    name = names[0]
                    field_value = self.get_field_value(field)
                    custom_fields.append({
                        'name': name,
                        'value': field_value
                    })
            
            # Cache the result
            self.custom_fields_cache[contact_uuid] = custom_fields
            return custom_fields
            
        except Exception as e:
            logger.error("Error getting custom fields for contact %s: %s", 
                        contact_uuid, str(e))
            return []

    def get_client_by_name(self, client_name: str) -> Optional[Client]:
        """Get a specific client by name using the search endpoint.
        
        Args:
            client_name: The exact name of the client to find.
            
        Returns:
            Optional[Client]: The client if found, None otherwise.
        """
        try:
            response = self.api_client.get('client.api/search', {
                'query': client_name,
                'detailed': 'true'
            })
            clients_xml = self._parse_xml(response.text)
            
            for client_elem in self.client_xpath(clients_xml):
                client = Client(client_elem)
                if client.name == client_name:
                    return client
            return None
            
        except Exception as e:
            logger.error("Failed to get client by name %s: %s", client_name, str(e))
            return None
    
    def process_contact(self, contact: Contact, client: Client, 
                       linkedin_field: CustomField) -> Optional[Dict]:
        """Process a single contact."""
        try:
            custom_fields = self.get_contact_custom_fields(contact.uuid)
            contact.custom_fields = custom_fields
            
            # Check if LinkedIn field exists and has a value
            has_linkedin_url = False
            for field in custom_fields:
                if field['name'].upper() == linkedin_field.name.upper():
                    value = field['value']
                    if value and value.strip():  # If field exists and has non-empty value
                        has_linkedin_url = True
                        contact.linkedin_url = value
                    break
            
            # Only include contacts that don't have a LinkedIn URL
            if has_linkedin_url:
                logger.debug(f"Contact {contact.name} already has LinkedIn URL: {contact.linkedin_url}")
                return None
            
            custom_fields_dict = {
                field['name']: field['value'] for field in custom_fields
            }
            
            logger.info(f"Found contact without LinkedIn URL: {contact.name} ({client.name})")
            return {
                **contact.to_dict(),
                'client_name': client.name,
                'custom_fields': custom_fields_dict
            }
            
        except Exception as e:
            logger.error("Failed to process contact %s: %s", contact.name, str(e))
            return None
    
    def fetch_profiles(self, limit: Optional[int] = None, start_page: int = 1,
                      client_name: Optional[str] = None, contact_name: Optional[str] = None,
                      progress_callback: Optional[Callable] = None) -> List[Dict]:
        """Fetch LinkedIn profiles with improved performance and memory usage.
        
        Args:
            limit: Optional maximum number of profiles to fetch.
            start_page: Page number to start from when fetching all clients.
            client_name: Optional client name to fetch contacts for a specific client.
            contact_name: Optional contact name to filter contacts by.
            progress_callback: Optional callback function to report progress.
            
        Returns:
            List[Dict]: List of contact profiles with their LinkedIn information.
        """
        logger.info("Starting profile fetch: limit=%s, start_page=%d, client=%s, contact=%s",
                   limit, start_page, client_name, contact_name)
        
        custom_fields = self.get_custom_field_definitions()
        linkedin_field = next((f for f in custom_fields if f.name and 
                             'LINKEDIN' in f.name.upper() and 
                             f.use_contact == 'true'), None)
        
        if not linkedin_field:
            logger.warning("No LinkedIn field definition found for contacts")
            return []
        
        logger.info("Using LinkedIn field: %s", linkedin_field.name)
        
        linkedin_profiles = []
        contacts_processed = 0

        try:
            # If client_name is provided, use optimized path
            if client_name:
                client = self.get_client_by_name(client_name)
                if not client:
                    logger.warning("Client not found: %s", client_name)
                    return []
                
                # Filter contacts if contact_name provided
                contacts = client.contacts
                if contact_name:
                    contacts = [c for c in contacts if contact_name.lower() in c.name.lower()]
                
                # Process contacts up to limit
                if limit:
                    contacts = contacts[:limit]
                
                # Process contacts in parallel
                futures = []
                for contact in contacts:
                    futures.append(
                        self.executor.submit(
                            self.process_contact,
                            contact,
                            client,
                            linkedin_field
                        )
                    )
                
                # Collect results as they complete
                for future in futures:
                    result = future.result()
                    if result:
                        linkedin_profiles.append(result)
                        if progress_callback:
                            progress_callback()
                
            else:
                # Original implementation for fetching all clients
                page = start_page
                has_more = True
                
                while has_more:
                    response = self.api_client.get('client.api/list', {
                        'page': page,
                        'pagesize': self.page_size,
                        'detailed': 'true'
                    })
                    
                    clients_xml = self._parse_xml(response.text)
                    total_records = int(clients_xml.find('.//TotalRecords').text)
                    current_page = int(clients_xml.find('.//Page').text)
                    
                    # Collect all contacts first
                    all_contacts = []
                    for client_elem in self.client_xpath(clients_xml):
                        client = Client(client_elem)
                        
                        if contact_name:
                            client.contacts = [c for c in client.contacts 
                                            if contact_name.lower() in c.name.lower()]
                        
                        if client.contacts:
                            for contact in client.contacts:
                                if limit and contacts_processed >= limit:
                                    has_more = False
                                    break
                                all_contacts.append((contact, client))
                                contacts_processed += 1
                        
                        if not has_more:
                            break
                    
                    # Process contacts in parallel
                    futures = []
                    for contact, client in all_contacts:
                        futures.append(
                            self.executor.submit(
                                self.process_contact,
                                contact,
                                client,
                                linkedin_field
                            )
                        )
                    
                    # Collect results as they complete
                    for future in futures:
                        result = future.result()
                        if result:
                            linkedin_profiles.append(result)
                            if progress_callback:
                                progress_callback()
                    
                    # Check pagination
                    if contact_name and linkedin_profiles:
                        has_more = False
                    else:
                        has_more = ((current_page * self.page_size) < total_records and 
                                  (not limit or contacts_processed < limit))
                        page += 1
            
        except Exception as e:
            logger.error("Error fetching profiles: %s", str(e))
            raise
        
        logger.info("Completed profile fetch: processed %d contacts", len(linkedin_profiles))
        return linkedin_profiles
    
    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
