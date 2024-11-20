import os
import json
import webbrowser
import argparse
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import jwt
from urllib.parse import urlencode, parse_qs
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from datetime import datetime, timezone
import time
from typing import Dict, List, Optional, Tuple, Any
import csv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import yaml

# Set up logging
logger = logging.getLogger('workflowmax')
logger.setLevel(logging.INFO)

# Create console handler with formatting
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Load environment variables
load_dotenv()

# OAuth 2.0 Configuration
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("CLIENT_ID and CLIENT_SECRET must be set in .env file")

REDIRECT_URI = 'http://localhost:8000/callback'
AUTH_URL = 'https://oauth.workflowmax2.com/oauth/authorize'
TOKEN_URL = 'https://oauth.workflowmax2.com/oauth/token'
API_BASE_URL = 'https://api.workflowmax2.com'
CACHE_FILE = '.oauth_cache.json'

class WorkflowMaxAPIError(Exception):
    """Base exception for WorkflowMax API errors"""
    pass

class AuthenticationError(WorkflowMaxAPIError):
    """Raised when authentication fails"""
    pass

class RateLimitError(WorkflowMaxAPIError):
    """Raised when API rate limit is hit"""
    pass

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle the OAuth callback"""
        if self.path.startswith('/callback'):
            try:
                # Extract authorization code from query parameters
                query_components = parse_qs(self.path.split('?')[1])
                code = query_components['code'][0]
                
                # Exchange code for tokens
                token_data = {
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': REDIRECT_URI,
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET
                }
                
                response = requests.post(TOKEN_URL, data=token_data, timeout=30)
                response.raise_for_status()
                
                self.server.tokens = response.json()
                
                # Decode JWT to get org_id
                decoded = jwt.decode(self.server.tokens['access_token'], options={"verify_signature": False})
                
                # Get the first org_id from the array
                if 'org_ids' in decoded and decoded['org_ids']:
                    self.server.org_id = decoded['org_ids'][0]
                    logger.info(f"Using organization ID: {self.server.org_id}")
                else:
                    raise Exception("No organization ID found in token")
                
                # Send success response to browser
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"Authorization successful! You can close this window.")
                
            except Exception as e:
                logger.error(f"Error during OAuth callback: {str(e)}")
                self.send_response(500)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(f"Error during authorization: {str(e)}".encode())
            finally:
                # Stop the server
                self.server.running = False

    def log_message(self, format, *args):
        """Suppress logging of HTTP requests"""
        pass

class APIClient:
    """WorkflowMax API client with retry and rate limiting handling"""
    
    def __init__(self, base_url: str, max_retries: int = 3):
        self.base_url = base_url
        self.tokens = None
        self.org_id = None
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        # Create session with retry strategy
        self.session = requests.Session()
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        # Rate limiting
        self.requests_per_second = 2
        self.last_request_time = 0

    def authenticate(self):
        """Handle the OAuth authentication flow"""
        # Try to load cached credentials first
        if self.load_cached_credentials():
            return

        # If no valid cached credentials, start OAuth flow
        server = HTTPServer(('localhost', 8000), OAuthCallbackHandler)
        server.running = True
        server.tokens = None
        server.org_id = None
        
        # Open browser for authorization
        auth_url = self.get_authorization_url()
        logger.info("Opening browser for authorization...")
        webbrowser.open(auth_url)
        
        # Wait for callback
        logger.info("Waiting for authorization...")
        while server.running:
            server.handle_request()
        
        if not server.tokens:
            raise AuthenticationError("Authentication failed. No tokens received.")
        if not server.org_id:
            raise AuthenticationError("Authentication failed. No organization ID received.")
        
        self.tokens = server.tokens
        self.org_id = server.org_id
        
        # Cache the credentials
        self.save_credentials_to_cache()
        
        logger.info("Authentication successful!")

    def load_cached_credentials(self) -> bool:
        """Load cached OAuth credentials if they exist and are not expired"""
        try:
            if not os.path.exists(CACHE_FILE):
                return False

            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)

            self.tokens = cache.get('tokens')
            self.org_id = cache.get('org_id')

            if not self.tokens or not self.org_id:
                return False

            # Check if token is expired
            decoded = jwt.decode(self.tokens['access_token'], options={"verify_signature": False})
            exp_timestamp = decoded.get('exp', 0)
            current_timestamp = datetime.now(timezone.utc).timestamp()

            if current_timestamp >= exp_timestamp:
                logger.info("Cached credentials have expired")
                return False

            logger.info("Using cached credentials")
            return True

        except Exception as e:
            logger.error(f"Error loading cached credentials: {str(e)}")
            return False

    def save_credentials_to_cache(self):
        """Save OAuth credentials to cache file"""
        try:
            cache = {
                'tokens': self.tokens,
                'org_id': self.org_id
            }
            with open(CACHE_FILE, 'w') as f:
                json.dump(cache, f)
        except Exception as e:
            logger.error(f"Error caching credentials: {str(e)}")

    def get_authorization_url(self) -> str:
        """Generate the authorization URL"""
        params = {
            'response_type': 'code',
            'client_id': CLIENT_ID,
            'redirect_uri': REDIRECT_URI,
            'scope': 'openid profile email workflowmax offline_access',
            'state': 'random_state',  # In production, use a secure random string
            'prompt': 'consent'
        }
        return f"{AUTH_URL}?{urlencode(params)}"
    
    def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < 1.0 / self.requests_per_second:
            time.sleep((1.0 / self.requests_per_second) - time_since_last_request)
        self.last_request_time = time.time()
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> requests.Response:
        """Make a GET request with rate limiting and error handling"""
        if not self.tokens or not self.org_id:
            raise AuthenticationError("Not authenticated")

        self._rate_limit()
        try:
            headers = {
                'Authorization': f"Bearer {self.tokens['access_token']}",
                'account_id': self.org_id,
                'Accept': 'application/xml'
            }
            response = self.session.get(
                f"{self.base_url}/{endpoint}",
                headers=headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                raise RateLimitError("API rate limit exceeded")
            elif e.response.status_code == 401:
                raise AuthenticationError("Authentication failed")
            else:
                raise WorkflowMaxAPIError(f"API request failed: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise WorkflowMaxAPIError(f"Request failed: {str(e)}")

def get_text_from_xml(element: Optional[ET.Element], tag_name: str) -> Optional[str]:
    """Helper function to safely extract text from XML elements"""
    if element is None:
        return None
    tag = element.find(tag_name)
    return tag.text if tag is not None else None

def has_contact_info(contact: ET.Element) -> bool:
    """Check if contact has any contact information"""
    email = get_text_from_xml(contact, 'Email')
    phone = get_text_from_xml(contact, 'Phone')
    mobile = get_text_from_xml(contact, 'Mobile')
    position = get_text_from_xml(contact, 'Position')
    return any([email, phone, mobile, position])

class LinkedInProfileFetcher:
    """Main class for fetching LinkedIn profiles from WorkflowMax"""
    
    def __init__(self, api_client: APIClient, config: Dict):
        self.api_client = api_client
        self.config = config
        self.custom_fields_cache: Dict[str, List[Dict[str, str]]] = {}
    
    def get_custom_field_definitions(self) -> List[Dict[str, str]]:
        """Get all custom field definitions with caching"""
        response = self.api_client.get('customfield.api/definition')
        logger.info("Custom field definitions response:")
        logger.info(response.text)
        
        definitions_xml = ET.fromstring(response.text)
        definitions = []
        
        for definition in definitions_xml.findall('.//CustomFieldDefinition'):
            def_info = {
                'uuid': get_text_from_xml(definition, 'UUID'),
                'name': get_text_from_xml(definition, 'Name'),
                'type': get_text_from_xml(definition, 'Type'),
                'usage': get_text_from_xml(definition, 'Usage'),
                'use_contact': get_text_from_xml(definition, 'UseContact')
            }
            definitions.append(def_info)
            logger.info(f"Found definition: {def_info}")
        
        return definitions
    
    def get_contact_custom_fields(self, contact_uuid: str) -> List[Dict[str, str]]:
        """Get custom fields for a contact"""
        try:
            if contact_uuid in self.custom_fields_cache:
                logger.info(f"Using cached custom fields for contact {contact_uuid}")
                return self.custom_fields_cache[contact_uuid]
            
            logger.info(f"Fetching custom fields for contact {contact_uuid}")
            endpoint = f'client.api/contact/{contact_uuid}/customfield'
            logger.info(f"Using endpoint: {endpoint}")
            
            response = self.api_client.get(endpoint)
            logger.info("Custom fields response:")
            logger.info(response.text)
            
            custom_fields_xml = ET.fromstring(response.text)
            custom_fields = []
            
            for field in custom_fields_xml.findall('.//CustomField'):
                name = get_text_from_xml(field, 'Name')
                value = get_text_from_xml(field, 'Value')
                link_url = get_text_from_xml(field, 'LinkURL')
                
                if name:
                    field_value = link_url if link_url else value
                    custom_fields.append({
                        'name': name,
                        'value': field_value
                    })
                    logger.info(f"Found custom field: {name} = {field_value}")
            
            if not custom_fields:
                logger.info("No custom fields found in response")
            
            self.custom_fields_cache[contact_uuid] = custom_fields
            return custom_fields
            
        except Exception as e:
            logger.error(f"Error getting custom fields for contact {contact_uuid}: {str(e)}")
            if isinstance(e, requests.exceptions.HTTPError):
                logger.error(f"Response status code: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
            return []
    
    def process_contact(self, contact: ET.Element, client: Dict[str, str], linkedin_field: Dict[str, str]) -> Optional[Dict]:
        """Process a single contact"""
        try:
            if not has_contact_info(contact):
                return None
                
            contact_name = get_text_from_xml(contact, 'Name')
            contact_uuid = get_text_from_xml(contact, 'UUID')
            
            if not contact_uuid:
                logger.warning(f"No UUID found for contact: {contact_name}")
                return None
            
            logger.info(f"\nProcessing contact: {contact_name} (UUID: {contact_uuid})")
            
            # Get custom fields for this contact
            custom_fields = self.get_contact_custom_fields(contact_uuid)
            
            # Find LinkedIn profile field (case insensitive)
            linkedin_url = None
            for field in custom_fields:
                if field['name'].upper() == linkedin_field['name'].upper():
                    linkedin_url = field['value']
                    logger.info(f"Found LinkedIn URL: {linkedin_url}")
                    break
            
            contact_info = {
                'name': contact_name,
                'email': get_text_from_xml(contact, 'Email'),
                'phone': get_text_from_xml(contact, 'Phone'),
                'mobile': get_text_from_xml(contact, 'Mobile'),
                'position': get_text_from_xml(contact, 'Position'),
                'is_primary': get_text_from_xml(contact, 'IsPrimary'),
                'client_name': client['name'],
                'linkedin_url': linkedin_url,
                'custom_fields': [(f['name'], f['value']) for f in custom_fields]
            }
            
            logger.info(f"LinkedIn URL found: {'Yes' if linkedin_url else 'No'}")
            return contact_info
            
        except Exception as e:
            logger.error(f"Error processing contact {contact_name}: {str(e)}")
            return None
    
    def fetch_profiles(self, limit: Optional[int] = None, start_page: int = 1,
                      client_name: Optional[str] = None, contact_name: Optional[str] = None) -> List[Dict]:
        """Fetch LinkedIn profiles with parallel processing"""
        custom_fields = self.get_custom_field_definitions()
        linkedin_field = next((f for f in custom_fields if f['name'] and 
                             'LINKEDIN' in f['name'].upper() and 
                             f['use_contact'] == 'true'), None)
        
        if not linkedin_field:
            logger.warning("No LinkedIn field definition found for contacts!")
            return []
        
        logger.info(f"Found LinkedIn field definition: {linkedin_field['name']}")
        
        linkedin_profiles = []
        contacts_processed = 0
        page = start_page
        page_size = 100
        has_more = True
        
        with tqdm(desc="Processing contacts", unit="contact") as pbar:
            while has_more:
                try:
                    response = self.api_client.get('client.api/list', {
                        'page': page,
                        'pagesize': page_size,
                        'detailed': 'true'
                    })
                    
                    clients_xml = ET.fromstring(response.text)
                    
                    # Get pagination info before processing contacts
                    total_records = int(clients_xml.find('.//TotalRecords').text)
                    current_page = int(clients_xml.find('.//Page').text)
                    
                    clients = []
                    
                    for client in clients_xml.findall('.//Client'):
                        current_client = {
                            'name': get_text_from_xml(client, 'Name'),
                            'uuid': get_text_from_xml(client, 'UUID'),
                            'contacts': []
                        }
                        
                        # Filter contacts by name if specified
                        for contact in client.findall('.//Contact'):
                            contact_name_elem = get_text_from_xml(contact, 'Name')
                            if not contact_name or (contact_name_elem and contact_name.lower() in contact_name_elem.lower()):
                                current_client['contacts'].append(contact)
                        
                        if (not client_name or current_client['name'] == client_name) and current_client['contacts']:
                            clients.append(current_client)
                    
                    # Process contacts in parallel
                    with ThreadPoolExecutor(max_workers=self.config.get('max_workers', 5)) as executor:
                        futures = []
                        for client in clients:
                            logger.info(f"Processing client: {client['name']}")
                            for contact in client['contacts']:
                                if limit and contacts_processed >= limit:
                                    has_more = False
                                    break
                                    
                                futures.append(
                                    executor.submit(
                                        self.process_contact,
                                        contact,
                                        client,
                                        linkedin_field
                                    )
                                )
                                contacts_processed += 1
                                
                            if not has_more:
                                break
                        
                        for future in as_completed(futures):
                            result = future.result()
                            if result:
                                linkedin_profiles.append(result)
                                pbar.update(1)
                    
                    # If searching by contact name and found matches, no need to continue pagination
                    if contact_name and linkedin_profiles:
                        has_more = False
                    else:
                        # Check pagination
                        has_more = (current_page * page_size) < total_records and (not limit or contacts_processed < limit)
                        page += 1
                    
                    logger.info(f"Processed page {current_page} of {(total_records + page_size - 1) // page_size}")
                    
                except Exception as e:
                    logger.error(f"Error processing page {page}: {str(e)}")
                    raise
        
        return linkedin_profiles

def save_results(profiles: List[Dict], output_format: str):
    """Save results in specified format"""
    base_filename = 'linkedin_profiles'
    
    if output_format == 'json':
        with open(f'{base_filename}.json', 'w') as f:
            json.dump(profiles, f, indent=2)
    elif output_format == 'csv':
        if profiles:
            fieldnames = ['name', 'email', 'phone', 'mobile', 'position', 
                         'is_primary', 'client_name', 'linkedin_url']
            with open(f'{base_filename}.csv', 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for profile in profiles:
                    # Exclude custom_fields from CSV output
                    row = {k: v for k, v in profile.items() if k in fieldnames}
                    writer.writerow(row)

def load_config() -> Dict:
    """Load configuration from file"""
    config_file = 'config.yml'
    default_config = {
        'max_workers': 5,
        'max_retries': 3,
        'requests_per_second': 2
    }
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                return {**default_config, **(config or {})}
    except Exception as e:
        logger.warning(f"Error loading config file: {str(e)}")
    
    return default_config

def main():
    parser = argparse.ArgumentParser(description='Fetch LinkedIn profiles from WorkflowMax contacts')
    parser.add_argument('--limit', type=int, help='Maximum number of contacts to process')
    parser.add_argument('--start', type=int, default=1, help='Page number to start from')
    parser.add_argument('--client', type=str, help='Only process contacts from this client')
    parser.add_argument('--contact', type=str, help='Search for a specific contact by name')
    parser.add_argument('--format', choices=['json', 'csv'], default='json',
                       help='Output format (default: json)')
    args = parser.parse_args()

    try:
        # Load configuration
        config = load_config()
        
        # Initialize API client
        api_client = APIClient(API_BASE_URL, max_retries=config['max_retries'])
        
        # Authenticate
        api_client.authenticate()
        
        # Initialize profile fetcher
        fetcher = LinkedInProfileFetcher(api_client, config)
        
        logger.info(f"Fetching LinkedIn profiles" +
                   (f" for contact '{args.contact}'" if args.contact else 
                    f" for {args.limit if args.limit else 'all'} contacts") +
                   (f" from client '{args.client}'" if args.client else "") +
                   f" starting from page {args.start}...")
        
        profiles = fetcher.fetch_profiles(
            limit=args.limit,
            start_page=args.start,
            client_name=args.client,
            contact_name=args.contact
        )
        
        # Save results in specified format
        save_results(profiles, args.format)
        
        logger.info(f"\nSummary:")
        logger.info(f"Total contacts processed: {len(profiles)}")
        profiles_with_linkedin = sum(1 for p in profiles if p['linkedin_url'])
        logger.info(f"LinkedIn profiles found: {profiles_with_linkedin}")
        logger.info(f"Contacts without LinkedIn: {len(profiles) - profiles_with_linkedin}")
        logger.info(f"Results saved to linkedin_profiles.{args.format}")
        
    except AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
    except RateLimitError as e:
        logger.error(f"Rate limit error: {str(e)}")
    except WorkflowMaxAPIError as e:
        logger.error(f"API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
