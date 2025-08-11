"""
Google OAuth2 authentication service for Gmail and Calendar APIs.
Handles secure authentication and token management.
"""

import os
import json
import pickle
from typing import Optional, List
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from loguru import logger

from ..core.config import get_settings


class GoogleAuthService:
    """Handles Google OAuth2 authentication for Gmail and Calendar APIs."""
    
    # Required OAuth2 scopes
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar.events',
    ]
    
    def __init__(self):
        """Initialize the Google authentication service."""
        settings = get_settings()
        if not settings:
            logger.warning("Settings not available, authentication may fail")
            self.client_id = None
            self.client_secret = None
            self.redirect_uri = "http://localhost:8080/callback"
        else:
            self.client_id = settings.google_client_id
            self.client_secret = settings.google_client_secret
            self.redirect_uri = settings.google_redirect_uri
        
        self.credentials_file = Path("data/google_credentials.json")
        self.token_file = Path("data/google_token.pickle")
        
        # Ensure data directory exists
        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.credentials: Optional[Credentials] = None
        self._gmail_service = None
        self._calendar_service = None
    
    def create_credentials_file(self) -> str:
        """
        Create the Google OAuth2 credentials file.
        This should be called during setup with valid client credentials.
        
        Returns:
            Path to the created credentials file
        """
        if not all([self.client_id, self.client_secret]):
            raise ValueError("Google Client ID and Secret are required")
        
        credentials_data = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri],
                "javascript_origins": ["http://localhost:8080"]
            }
        }
        
        with open(self.credentials_file, 'w') as f:
            json.dump(credentials_data, f, indent=2)
        
        logger.info(f"Created credentials file: {self.credentials_file}")
        return str(self.credentials_file)
    
    def authenticate(self, force_reauth: bool = False) -> bool:
        """
        Authenticate with Google APIs using OAuth2 flow.
        
        Args:
            force_reauth: If True, force re-authentication even if valid token exists
        
        Returns:
            True if authentication successful, False otherwise
        """
        # Load existing token if available and not forcing reauth
        if not force_reauth and self.token_file.exists():
            try:
                with open(self.token_file, 'rb') as token_file:
                    self.credentials = pickle.load(token_file)
                    
                if self.credentials and self.credentials.valid:
                    logger.info("Using existing valid credentials")
                    return True
                    
                # Try to refresh expired credentials
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    try:
                        self.credentials.refresh(Request())
                        self._save_credentials()
                        logger.info("Refreshed expired credentials")
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to refresh credentials: {e}")
                        
            except Exception as e:
                logger.warning(f"Failed to load existing credentials: {e}")
        
        # Perform OAuth2 flow
        return self._perform_oauth_flow()
    
    def _perform_oauth_flow(self) -> bool:
        """Perform the OAuth2 authentication flow."""
        try:
            # Ensure credentials file exists
            if not self.credentials_file.exists():
                self.create_credentials_file()
            
            # Create OAuth2 flow
            flow = Flow.from_client_secrets_file(
                str(self.credentials_file),
                scopes=self.SCOPES
            )
            flow.redirect_uri = self.redirect_uri
            
            # Get authorization URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            logger.info("Please visit this URL to authorize the application:")
            logger.info(auth_url)
            
            # Start local server to handle callback
            import webbrowser
            import urllib.parse as urlparse
            from http.server import HTTPServer, BaseHTTPRequestHandler
            import threading
            import time
            
            # Shared variable to store the authorization code
            auth_code_container = {'code': None, 'error': None}
            
            class CallbackHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    # Parse the callback URL
                    parsed_url = urlparse.urlparse(self.path)
                    query_params = urlparse.parse_qs(parsed_url.query)
                    
                    if 'code' in query_params:
                        auth_code_container['code'] = query_params['code'][0]
                        # Send success response
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(b'''<!DOCTYPE html>
                        <html>
                        <head><title>Authentication Successful</title></head>
                        <body>
                            <h1>Authentication Successful!</h1>
                            <p>You can now close this window and return to the AI Email Manager.</p>
                            <script>setTimeout(() => window.close(), 3000);</script>
                        </body>
                        </html>''')
                    elif 'error' in query_params:
                        auth_code_container['error'] = query_params['error'][0]
                        # Send error response
                        self.send_response(400)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(b'''<!DOCTYPE html>
                        <html>
                        <head><title>Authentication Error</title></head>
                        <body>
                            <h1>Authentication Error</h1>
                            <p>Authentication was denied or failed. Please try again.</p>
                            <script>setTimeout(() => window.close(), 5000);</script>
                        </body>
                        </html>''')
                    
                def log_message(self, format, *args):
                    # Suppress log messages
                    pass
            
            # Start local server on port 8080
            server = HTTPServer(('localhost', 8080), CallbackHandler)
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            try:
                # Open browser
                webbrowser.open(auth_url)
                logger.info("Opened browser for authentication...")
                
                # Wait for callback (with timeout)
                timeout = 120  # 2 minutes
                start_time = time.time()
                
                while auth_code_container['code'] is None and auth_code_container['error'] is None:
                    if time.time() - start_time > timeout:
                        logger.error("Authentication timeout - please try again")
                        return False
                    time.sleep(0.5)
                
                if auth_code_container['error']:
                    logger.error(f"Authentication error: {auth_code_container['error']}")
                    return False
                
                if not auth_code_container['code']:
                    logger.error("No authorization code received")
                    return False
                
                # Exchange authorization code for credentials
                flow.fetch_token(code=auth_code_container['code'])
                self.credentials = flow.credentials
                
                # Save credentials
                self._save_credentials()
                
                logger.info("Authentication successful!")
                return True
                
            finally:
                # Shutdown server
                server.shutdown()
            
        except Exception as e:
            logger.error(f"OAuth2 flow failed: {e}")
            return False
    
    def _save_credentials(self):
        """Save credentials to file."""
        try:
            with open(self.token_file, 'wb') as token_file:
                pickle.dump(self.credentials, token_file)
            logger.debug("Credentials saved successfully")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        return (self.credentials is not None and 
                self.credentials.valid and 
                not self.credentials.expired)
    
    def revoke_authentication(self):
        """Revoke current authentication and delete stored tokens."""
        if self.credentials:
            try:
                self.credentials.revoke(Request())
                logger.info("Credentials revoked successfully")
            except Exception as e:
                logger.warning(f"Failed to revoke credentials: {e}")
        
        # Delete stored tokens
        if self.token_file.exists():
            self.token_file.unlink()
            logger.info("Token file deleted")
        
        self.credentials = None
        self._gmail_service = None
        self._calendar_service = None
    
    def get_gmail_service(self):
        """Get authenticated Gmail API service."""
        if not self.is_authenticated():
            raise ValueError("Not authenticated. Call authenticate() first.")
        
        if self._gmail_service is None:
            try:
                self._gmail_service = build(
                    'gmail', 'v1', 
                    credentials=self.credentials
                )
                logger.debug("Gmail service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gmail service: {e}")
                raise
        
        return self._gmail_service
    
    def get_calendar_service(self):
        """Get authenticated Calendar API service."""
        if not self.is_authenticated():
            raise ValueError("Not authenticated. Call authenticate() first.")
        
        if self._calendar_service is None:
            try:
                self._calendar_service = build(
                    'calendar', 'v3', 
                    credentials=self.credentials
                )
                logger.debug("Calendar service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Calendar service: {e}")
                raise
        
        return self._calendar_service
    
    def test_gmail_connection(self) -> bool:
        """Test Gmail API connection."""
        try:
            service = self.get_gmail_service()
            # Try to get user profile
            profile = service.users().getProfile(userId='me').execute()
            logger.info(f"Gmail connection test successful. Email: {profile.get('emailAddress')}")
            return True
        except Exception as e:
            logger.error(f"Gmail connection test failed: {e}")
            return False
    
    def test_calendar_connection(self) -> bool:
        """Test Calendar API connection."""
        try:
            service = self.get_calendar_service()
            # Try to get calendar list
            calendar_list = service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])
            logger.info(f"Calendar connection test successful. Found {len(calendars)} calendars")
            return True
        except Exception as e:
            logger.error(f"Calendar connection test failed: {e}")
            return False
    
    def get_user_info(self) -> dict:
        """Get basic user information."""
        try:
            gmail_service = self.get_gmail_service()
            profile = gmail_service.users().getProfile(userId='me').execute()
            
            return {
                'email': profile.get('emailAddress'),
                'messages_total': profile.get('messagesTotal', 0),
                'threads_total': profile.get('threadsTotal', 0),
                'history_id': profile.get('historyId')
            }
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return {}


# Global authentication instance
_auth_service = None

def get_auth_service() -> GoogleAuthService:
    """Get the global authentication service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = GoogleAuthService()
    return _auth_service
