import requests
import json
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class PodioService:
    """
    Podio service class based on proven implementation from old project
    """
    
    def __init__(self, auth_method='app_token', **kwargs):
        # Use your correct credentials
        self.client_id = kwargs.get('client_id', 'ogx-api')
        self.client_secret = kwargs.get('client_secret', '3kKrIxJarIExCyaO5dz8ITEwmreW9aDIXByOPrsJqulYJbe9qdANmEUHK3kE1gLG')
        
        # Get app-specific parameters
        self.app_id = kwargs.get('app_id')
        self.app_token = kwargs.get('app_token')
        
        # Optional username/password for password auth
        self.username = kwargs.get('username', 'mahmoud.fouda2@aiesec.net')
        self.password = kwargs.get('password', 'Mahmoud_2002')
        
        # Authentication state
        self.access_token = None
        self.refresh_token = None
        self.token_expires = 0
        
        # Store authentication method
        self.auth_method = auth_method
        
        # Use proven Podio API URL
        self.base_url = "https://api.podio.com"
        
        logger.info(f"PodioService initialized with {auth_method} authentication for app {self.app_id}")
        
        # Authenticate immediately if using app token
        if auth_method == 'app_token' and self.app_id and self.app_token:
            self.authenticate()
        
    def authenticate(self):
        """Authenticate with Podio using app token (proven method)"""
        try:
            auth_data = {
                'grant_type': 'app',
                'app_id': self.app_id,
                'app_token': self.app_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            auth_url = f"{self.base_url}/oauth/token"
            response = requests.post(auth_url, data=auth_data, verify=True, timeout=10)
            
            if response.status_code == 200:
                auth_result = response.json()
                self.access_token = auth_result.get('access_token')
                self.refresh_token = auth_result.get('refresh_token')
                self.token_expires = int(time.time()) + auth_result.get('expires_in', 0)
                logger.info("✅ Successfully authenticated with app token")
                return True
            else:
                logger.error(f"❌ App token authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ App token authentication error: {str(e)}")
            return False
    
    def ensure_authenticated(self):
        """Ensure we have a valid access token"""
        if not self.access_token or time.time() > self.token_expires - 60:
            logger.info("Access token missing or expired, authenticating...")
            if not self.authenticate():
                raise Exception("Failed to authenticate with Podio")
        return self.access_token

    def _get_headers(self):
        """Get appropriate headers for API requests"""
        self.ensure_authenticated()
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def create_item(self, app_id, fields):
        """Create a new item in a Podio app using proven method"""
        try:
            self.ensure_authenticated()
            
            # Use the exact format from the proven implementation
            url = f"{self.base_url}/item/app/{app_id}"
            data = {'fields': fields}
            headers = self._get_headers()
            
            logger.info(f"Creating Podio item in app {app_id}")
            response = requests.post(url, json=data, headers=headers, timeout=15, verify=True)
            
            if response.status_code in [200, 201]:
                result = response.json()
                item_id = result.get('item_id')
                logger.info(f"✅ Successfully created item with ID: {item_id}")
                return True, result
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"❌ Failed to create item: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"❌ Error creating Podio item: {str(e)}")
            return False, str(e)
    
    def get_items(self, app_id, limit=100, offset=0):
        """
        Get items from a Podio app
        
        Args:
            app_id: Podio app ID to get items from
            limit: Maximum number of items to retrieve
            offset: Number of items to skip
            
        Returns:
            tuple: (success: bool, result: items_list or error_message)
        """
        url = f"{self.base_url}/item/app/{app_id}/"
        headers = self._get_headers()
        
        params = {
            'limit': limit,
            'offset': offset,
            'sort_by': 'created_on',
            'sort_desc': True
        }
        
        try:
            logger.info(f"Getting items from Podio app {app_id} (limit: {limit}, offset: {offset})")
            
            # Try the request with retries for timeout issues
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Increase timeout to 60 seconds for large requests
                    response = requests.get(url, headers=headers, params=params, timeout=60)
                    break  # Success, exit retry loop
                except requests.exceptions.Timeout as e:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 10  # Wait 10, 20, 30 seconds
                        logger.warning(f"Request timed out (attempt {attempt + 1}/{max_retries}), retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Request failed after {max_retries} attempts due to timeout")
                        raise
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    logger.info(f"DEBUG: Full response structure: {type(response_data)}")
                    logger.info(f"DEBUG: Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Not a dict'}")
                    
                    # Handle different possible response structures
                    if isinstance(response_data, list):
                        # Response is directly a list of items
                        items = response_data
                    elif isinstance(response_data, dict):
                        # Response is an object, try to find the items
                        items = response_data.get('items', response_data.get('filtered', response_data))
                        if items == response_data and 'items' not in response_data and 'filtered' not in response_data:
                            # If response_data itself doesn't have items/filtered keys, it might be malformed
                            logger.warning(f"Unexpected response structure: {response_data}")
                            items = []
                    else:
                        logger.error(f"Unexpected response type: {type(response_data)}")
                        items = []
                    
                    logger.info(f"✅ Retrieved {len(items)} items from Podio app {app_id}")
                    # Debug: log the structure of the first item with error handling
                    if items:
                        try:
                            logger.info(f"Sample item structure: {items[0]}")
                        except Exception as item_log_error:
                            logger.warning(f"Could not log first item structure: {item_log_error}")
                    return True, items
                except Exception as json_error:
                    error_msg = f"JSON parsing error: {str(json_error)}"
                    logger.error(f"❌ Failed to parse JSON response from app {app_id}: {error_msg}")
                    return False, error_msg
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"❌ Failed to get items from app {app_id}: {error_msg}")
                return False, error_msg
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_all_items(self, app_id, max_items=None):
        """
        Get all items from a Podio app using pagination
        
        Args:
            app_id: Podio app ID to get items from
            max_items: Maximum number of items to fetch (None for all)
            
        Returns:
            tuple: (success: bool, result: items_list or error_message)
        """
        all_items = []
        offset = 0
        limit = 100  # Reduced from 500 to avoid timeouts with large requests
        
        try:
            logger.info(f"Starting paginated fetch for app {app_id}, max_items: {max_items}")
            
            while True:
                # Calculate limit for this request
                if max_items and len(all_items) + limit > max_items:
                    remaining = max_items - len(all_items)
                    if remaining <= 0:
                        break
                    current_limit = remaining
                else:
                    current_limit = limit
                
                logger.info(f"Fetching batch: offset={offset}, limit={current_limit}")
                
                # Get this batch of items
                success, items = self.get_items(app_id, limit=current_limit, offset=offset)
                
                if not success:
                    logger.error(f"Failed to fetch batch at offset {offset}: {items}")
                    return False, items
                
                # If no items returned, we've reached the end
                if not items or len(items) == 0:
                    logger.info(f"No more items found at offset {offset}, stopping pagination")
                    break
                
                # Add items to our collection
                all_items.extend(items)
                logger.info(f"Collected {len(items)} items in this batch, total so far: {len(all_items)}")
                
                # If we got fewer items than requested, we've reached the end
                if len(items) < current_limit:
                    logger.info(f"Got {len(items)} items (less than limit {current_limit}), pagination complete")
                    break
                
                # Move to next batch
                offset += len(items)
                
                # Check if we've reached our max_items limit
                if max_items and len(all_items) >= max_items:
                    logger.info(f"Reached max_items limit of {max_items}")
                    all_items = all_items[:max_items]  # Trim to exact count
                    break
                
                # Small delay to be nice to the API
                time.sleep(0.2)
            
            logger.info(f"✅ Successfully retrieved {len(all_items)} total items from app {app_id}")
            return True, all_items
            
        except Exception as e:
            error_msg = f"Error during paginated fetch: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def test_connection(self, app_id=None):
        """Test the Podio API connection using proven OAuth flow"""
        try:
            self.ensure_authenticated()
            
            # Test with app endpoint if available
            if app_id:
                url = f"{self.base_url}/app/{app_id}"
            else:
                url = f"{self.base_url}/user/status"
            
            headers = self._get_headers()
            logger.info(f"Testing connection with authenticated headers")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Podio API connection successful")
                return True, response.json()
            else:
                logger.error(f"❌ Podio API connection failed: {response.status_code} - {response.text}")
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            logger.error(f"❌ Podio API connection error: {str(e)}")
            return False, str(e)

    def get_app_info(self, app_id):
        """Get information about a Podio app"""
        try:
            url = f"{self.base_url}/app/{app_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, str(e)