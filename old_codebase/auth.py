"""OAuth2 authentication handling for WorkflowMax API client."""

import os
import json
import webbrowser
import secrets
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import jwt
from datetime import datetime, timezone
from urllib.parse import urlencode, parse_qs
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from .config import Config
from .exceptions import (
    AuthenticationError,
    TokenExpiredError,
    TokenRefreshError,
    ConfigurationError
)
from .logging_config import get_logger

logger = get_logger('workflowmax.auth')

@dataclass
class TokenInfo:
    """Container for token information."""
    access_token: str
    refresh_token: str
    expires_at: float
    org_id: str

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handler for OAuth2 callback requests."""
    
    def do_GET(self):
        """Handle the OAuth callback."""
        if self.path.startswith('/callback'):
            try:
                # Extract and validate query parameters
                query_components = parse_qs(self.path.split('?')[1])
                
                if 'error' in query_components:
                    error_msg = query_components.get('error_description', ['Unknown error'])[0]
                    raise AuthenticationError(f"OAuth error: {error_msg}")
                
                if 'state' not in query_components:
                    raise AuthenticationError("Missing state parameter")
                    
                if query_components['state'][0] != self.server.state:
                    raise AuthenticationError("Invalid state parameter")
                
                if 'code' not in query_components:
                    raise AuthenticationError("Missing authorization code")
                
                code = query_components['code'][0]
                config = Config()
                
                # Exchange code for tokens
                token_data = {
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': config.oauth.redirect_uri,
                    'client_id': config.client_id,
                    'client_secret': config.client_secret
                }
                
                response = requests.post(config.oauth.token_url, data=token_data, timeout=30)
                response.raise_for_status()
                
                tokens = response.json()
                
                # Validate and decode JWT
                try:
                    decoded = jwt.decode(
                        tokens['access_token'],
                        options={"verify_signature": False}
                    )
                except jwt.InvalidTokenError as e:
                    raise AuthenticationError(f"Invalid token: {str(e)}")
                
                # Get organization ID
                if 'org_ids' not in decoded or not decoded['org_ids']:
                    raise AuthenticationError("No organization ID found in token")
                
                # Store token info
                self.server.token_info = TokenInfo(
                    access_token=tokens['access_token'],
                    refresh_token=tokens.get('refresh_token', ''),
                    expires_at=time.time() + tokens.get('expires_in', 3600),
                    org_id=decoded['org_ids'][0]
                )
                
                # Send success response
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
                self.server.running = False

    def log_message(self, format, *args):
        """Suppress logging of HTTP requests."""
        pass

class OAuthManager:
    """Manages OAuth2 authentication flow and token storage."""
    
    def __init__(self):
        """Initialize the OAuth manager."""
        self.config = Config()
        self.token_info: Optional[TokenInfo] = None
        
    def _generate_state(self) -> str:
        """Generate a secure random state parameter.
        
        Returns:
            str: Random state string
        """
        return secrets.token_urlsafe(32)
    
    def _save_token_info(self, token_info: TokenInfo):
        """Save token information to cache file.
        
        Args:
            token_info: Token information to save
        """
        try:
            cache = {
                'access_token': token_info.access_token,
                'refresh_token': token_info.refresh_token,
                'expires_at': token_info.expires_at,
                'org_id': token_info.org_id
            }
            with open(self.config.oauth.cache_file, 'w') as f:
                json.dump(cache, f)
            logger.debug("Saved token info to cache")
        except Exception as e:
            logger.error(f"Error saving token cache: {str(e)}")
    
    def _load_token_info(self) -> Optional[TokenInfo]:
        """Load token information from cache file.
        
        Returns:
            Optional[TokenInfo]: Token information if valid cache exists
        """
        try:
            if not os.path.exists(self.config.oauth.cache_file):
                return None

            with open(self.config.oauth.cache_file, 'r') as f:
                cache = json.load(f)

            token_info = TokenInfo(
                access_token=cache['access_token'],
                refresh_token=cache['refresh_token'],
                expires_at=cache['expires_at'],
                org_id=cache['org_id']
            )

            # Check if token is expired or will expire soon (within 5 minutes)
            if time.time() >= (token_info.expires_at - 300):
                logger.info("Cached token is expired or will expire soon")
                return None

            logger.info("Using cached token")
            return token_info

        except Exception as e:
            logger.error(f"Error loading token cache: {str(e)}")
            return None
    
    def _refresh_token(self, refresh_token: str) -> TokenInfo:
        """Refresh the access token.
        
        Args:
            refresh_token: The refresh token to use
            
        Returns:
            TokenInfo: New token information
            
        Raises:
            TokenRefreshError: If token refresh fails
        """
        try:
            token_data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': self.config.client_id,
                'client_secret': self.config.client_secret
            }
            
            response = requests.post(
                self.config.oauth.token_url,
                data=token_data,
                timeout=30
            )
            response.raise_for_status()
            
            tokens = response.json()
            
            # Decode and validate new token
            try:
                decoded = jwt.decode(
                    tokens['access_token'],
                    options={"verify_signature": False}
                )
            except jwt.InvalidTokenError as e:
                raise TokenRefreshError(f"Invalid refreshed token: {str(e)}")
            
            if 'org_ids' not in decoded or not decoded['org_ids']:
                raise TokenRefreshError("No organization ID in refreshed token")
            
            token_info = TokenInfo(
                access_token=tokens['access_token'],
                refresh_token=tokens.get('refresh_token', refresh_token),
                expires_at=time.time() + tokens.get('expires_in', 3600),
                org_id=decoded['org_ids'][0]
            )
            
            self._save_token_info(token_info)
            logger.info("Successfully refreshed token")
            
            return token_info
            
        except Exception as e:
            raise TokenRefreshError(f"Token refresh failed: {str(e)}")
    
    def authenticate(self, force_refresh: bool = False) -> Tuple[Dict, str]:
        """Handle the OAuth authentication flow.
        
        Args:
            force_refresh: Whether to force token refresh
            
        Returns:
            Tuple[Dict, str]: Tuple of (tokens dict, organization ID)
            
        Raises:
            AuthenticationError: If authentication fails
        """
        # Try to load cached token info
        if not force_refresh:
            token_info = self._load_token_info()
            if token_info:
                return {
                    'access_token': token_info.access_token,
                    'refresh_token': token_info.refresh_token
                }, token_info.org_id
        
        # Try to refresh token if we have one
        if self.token_info and self.token_info.refresh_token:
            try:
                token_info = self._refresh_token(self.token_info.refresh_token)
                return {
                    'access_token': token_info.access_token,
                    'refresh_token': token_info.refresh_token
                }, token_info.org_id
            except TokenRefreshError:
                logger.warning("Token refresh failed, falling back to full authentication")
        
        # Start new OAuth flow
        server = HTTPServer(('localhost', 8000), OAuthCallbackHandler)
        server.running = True
        server.token_info = None
        server.state = self._generate_state()
        
        # Generate authorization URL
        params = {
            'response_type': 'code',
            'client_id': self.config.client_id,
            'redirect_uri': self.config.oauth.redirect_uri,
            'scope': self.config.oauth.scope,
            'state': server.state,
            'prompt': 'consent'
        }
        auth_url = f"{self.config.oauth.auth_url}?{urlencode(params)}"
        
        # Open browser for authorization
        logger.info("Opening browser for authorization...")
        webbrowser.open(auth_url)
        
        # Wait for callback
        logger.info("Waiting for authorization...")
        while server.running:
            server.handle_request()
        
        if not server.token_info:
            raise AuthenticationError("Authentication failed. No tokens received.")
        
        self.token_info = server.token_info
        self._save_token_info(self.token_info)
        
        logger.info("Authentication successful!")
        return {
            'access_token': self.token_info.access_token,
            'refresh_token': self.token_info.refresh_token
        }, self.token_info.org_id
