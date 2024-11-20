"""OAuth2 authentication for WorkflowMax API."""

import json
import time
import secrets
import webbrowser
from typing import Optional, Dict, Tuple
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlencode, parse_qs, urlparse
import requests
from cryptography.fernet import Fernet
import jwt

from ..core.exceptions import (
    AuthenticationError,
    TokenExpiredError,
    TokenRefreshError,
    ConfigurationError
)
from ..core.logging import get_logger, with_logging
from ..core.utils import Timer
from ..config import config

logger = get_logger('workflowmax.api.auth')

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handler for OAuth2 callback requests."""
    
    def do_GET(self):
        """Handle GET request to callback URL."""
        try:
            # Parse query parameters
            query = urlparse(self.path).query
            params = parse_qs(query)
            
            if 'error' in params:
                error = params['error'][0]
                error_description = params.get('error_description', ['Unknown error'])[0]
                self.server.oauth_response = {
                    'error': error,
                    'error_description': error_description
                }
            elif 'code' in params and 'state' in params:
                self.server.oauth_response = {
                    'code': params['code'][0],
                    'state': params['state'][0]
                }
            else:
                self.server.oauth_response = {
                    'error': 'invalid_response',
                    'error_description': 'Missing required parameters'
                }
            
            # Send response to browser
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            response_html = """
            <html>
            <head><title>Authentication Complete</title></head>
            <body>
                <h1>Authentication Complete</h1>
                <p>You can close this window and return to the application.</p>
                <script>window.close();</script>
            </body>
            </html>
            """
            self.wfile.write(response_html.encode())
            
        except Exception as e:
            logger.error("Error in callback handler", error=str(e))
            self.server.oauth_response = {
                'error': 'server_error',
                'error_description': str(e)
            }
    
    def log_message(self, format, *args):
        """Override to prevent logging to stderr."""
        pass

class OAuthManager:
    """Manager for OAuth2 authentication."""
    
    def __init__(self):
        """Initialize OAuth manager."""
        self.auth_config = config.auth
        self._encryption_key: Optional[bytes] = None
        
        if self.auth_config.token_storage.encryption_key:
            self._encryption_key = Fernet.generate_key()
    
    def _generate_state(self) -> str:
        """Generate secure state parameter.
        
        Returns:
            Random state string
        """
        return secrets.token_urlsafe(32)
    
    def _encrypt_token_info(self, token_info: Dict) -> bytes:
        """Encrypt token information.
        
        Args:
            token_info: Token information to encrypt
            
        Returns:
            Encrypted token data
            
        Raises:
            ConfigurationError: If encryption key not configured
        """
        if not self._encryption_key:
            raise ConfigurationError("Encryption key not configured")
            
        f = Fernet(self._encryption_key)
        return f.encrypt(json.dumps(token_info).encode())
    
    def _decrypt_token_info(self, encrypted_data: bytes) -> Dict:
        """Decrypt token information.
        
        Args:
            encrypted_data: Encrypted token data
            
        Returns:
            Decrypted token information
            
        Raises:
            ConfigurationError: If encryption key not configured
        """
        if not self._encryption_key:
            raise ConfigurationError("Encryption key not configured")
            
        f = Fernet(self._encryption_key)
        return json.loads(f.decrypt(encrypted_data))
    
    def _save_token_info(self, token_info: Dict):
        """Save token information to file.
        
        Args:
            token_info: Token information to save
            
        Raises:
            ConfigurationError: If token storage not configured
        """
        if not self.auth_config.token_storage.enabled:
            return
            
        storage_path = self.auth_config.token_storage.file_path
        if not storage_path:
            raise ConfigurationError("Token storage path not configured")
            
        try:
            # Encrypt if configured
            if self._encryption_key:
                data = self._encrypt_token_info(token_info)
                mode = 'wb'
            else:
                data = json.dumps(token_info)
                mode = 'w'
            
            with open(storage_path, mode) as f:
                f.write(data)
                
            logger.debug("Saved token information")
            
        except Exception as e:
            logger.error("Failed to save token information", error=str(e))
            raise ConfigurationError(f"Failed to save token information: {str(e)}")
    
    def _load_token_info(self) -> Optional[Dict]:
        """Load token information from file.
        
        Returns:
            Token information if found and valid
            
        Raises:
            ConfigurationError: If token storage not configured
        """
        if not self.auth_config.token_storage.enabled:
            return None
            
        storage_path = self.auth_config.token_storage.file_path
        if not storage_path or not storage_path.exists():
            return None
            
        try:
            # Read and decrypt if configured
            if self._encryption_key:
                with open(storage_path, 'rb') as f:
                    encrypted_data = f.read()
                data = self._decrypt_token_info(encrypted_data)
            else:
                with open(storage_path) as f:
                    data = json.loads(f.read())
            
            # Handle legacy token format
            if 'tokens' not in data and 'access_token' in data:
                # Extract org_id from access token
                token_data = jwt.decode(data['access_token'], options={"verify_signature": False})
                org_ids = token_data.get('org_ids', [])
                org_id = org_ids[0] if org_ids else None
                
                data = {
                    'tokens': data,
                    'org_id': org_id,
                    'expires_at': time.time() + data.get('expires_in', 3600)
                }
                
            return data
                    
        except Exception as e:
            logger.error("Failed to load token information", error=str(e))
            return None
    
    def _refresh_token(self, refresh_token: str) -> Dict:
        """Refresh access token.
        
        Args:
            refresh_token: Refresh token to use
            
        Returns:
            New token information
            
        Raises:
            TokenRefreshError: If refresh fails
        """
        try:
            response = requests.post(
                self.auth_config.oauth2_endpoints.token_url,
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': refresh_token,
                    'client_id': self.auth_config.oauth2_credentials.client_id,
                    'client_secret': self.auth_config.oauth2_credentials.client_secret.get_secret_value()
                }
            )
            
            if response.ok:
                token_info = response.json()
                # Extract org_id from access token
                token_data = jwt.decode(token_info['access_token'], options={"verify_signature": False})
                org_ids = token_data.get('org_ids', [])
                org_id = org_ids[0] if org_ids else None
                
                token_info = {
                    'tokens': token_info,
                    'org_id': org_id,
                    'expires_at': time.time() + token_info.get('expires_in', 3600)
                }
                self._save_token_info(token_info)
                return token_info
            else:
                raise TokenRefreshError(
                    f"Token refresh failed: {response.status_code} {response.reason}"
                )
                
        except Exception as e:
            raise TokenRefreshError(f"Token refresh failed: {str(e)}")
    
    @with_logging
    def authenticate(self, force_refresh: bool = False) -> Tuple[Dict, str]:
        """Perform OAuth2 authentication.
        
        Args:
            force_refresh: Whether to force token refresh
            
        Returns:
            Tuple of (tokens, organization_id)
            
        Raises:
            AuthenticationError: If authentication fails
        """
        with Timer("OAuth2 authentication"):
            # Check for stored tokens
            if not force_refresh:
                token_info = self._load_token_info()
                if token_info:
                    # Check if refresh needed
                    expires_at = token_info.get('expires_at', 0)
                    if time.time() < expires_at - self.auth_config.token_refresh.refresh_threshold:
                        return token_info['tokens'], token_info['org_id']
                    
                    # Try to refresh
                    try:
                        new_token_info = self._refresh_token(
                            token_info['tokens']['refresh_token']
                        )
                        return new_token_info['tokens'], new_token_info['org_id']
                    except TokenRefreshError:
                        logger.warning("Token refresh failed, proceeding with new authentication")
            
            # Start new authentication flow
            state = self._generate_state()
            
            # Build authorization URL
            auth_params = {
                'response_type': 'code',
                'client_id': self.auth_config.oauth2_credentials.client_id,
                'redirect_uri': str(self.auth_config.oauth2_endpoints.redirect_uri),
                'scope': self.auth_config.oauth2_credentials.scope,
                'state': state
            }
            
            auth_url = (
                f"{self.auth_config.oauth2_endpoints.authorize_url}?"
                f"{urlencode(auth_params)}"
            )
            
            # Extract port from redirect URI
            redirect_uri = urlparse(str(self.auth_config.oauth2_endpoints.redirect_uri))
            port = redirect_uri.port or 8000  # Default to 8000 if no port specified
            
            # Start local server for callback
            server = HTTPServer(('localhost', port), OAuthCallbackHandler)
            server.oauth_response = None
            
            try:
                # Open browser for authentication
                webbrowser.open(auth_url)
                
                # Wait for callback
                while server.oauth_response is None:
                    server.handle_request()
                
                response = server.oauth_response
                
                # Check for errors
                if 'error' in response:
                    raise AuthenticationError(
                        f"Authentication failed: {response['error_description']}"
                    )
                
                # Verify state
                if response['state'] != state:
                    raise AuthenticationError("Invalid state parameter")
                
                # Exchange code for tokens
                token_response = requests.post(
                    self.auth_config.oauth2_endpoints.token_url,
                    data={
                        'grant_type': 'authorization_code',
                        'code': response['code'],
                        'redirect_uri': str(self.auth_config.oauth2_endpoints.redirect_uri),
                        'client_id': self.auth_config.oauth2_credentials.client_id,
                        'client_secret': self.auth_config.oauth2_credentials.client_secret.get_secret_value()
                    }
                )
                
                if not token_response.ok:
                    raise AuthenticationError(
                        f"Token exchange failed: {token_response.status_code} "
                        f"{token_response.reason}"
                    )
                
                # Process token response
                token_info = token_response.json()
                # Extract org_id from access token
                token_data = jwt.decode(token_info['access_token'], options={"verify_signature": False})
                org_ids = token_data.get('org_ids', [])
                org_id = org_ids[0] if org_ids else None
                
                if not org_id:
                    raise AuthenticationError("Organization ID not found in token")
                
                # Structure token info
                token_info = {
                    'tokens': token_info,
                    'org_id': org_id,
                    'expires_at': time.time() + token_info.get('expires_in', 3600)
                }
                
                # Save token information
                self._save_token_info(token_info)
                
                return token_info['tokens'], org_id
                
            finally:
                server.server_close()
