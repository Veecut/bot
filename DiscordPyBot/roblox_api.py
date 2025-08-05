"""
Roblox API Integration
Handles all interactions with the Roblox web API
"""

import aiohttp
import asyncio
import math
from typing import Optional, List, Dict, Any
import json

class RobloxAPI:
    """Handles Roblox API requests with rate limiting and error handling"""
    
    def __init__(self):
        self.base_url = "https://api.roblox.com"
        self.catalog_url = "https://catalog.roblox.com/v1"
        self.users_url = "https://users.roblox.com/v1"
        self.session = None
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # Minimum 100ms between requests
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                'User-Agent': 'keilscanner-bot/1.0',
                'Accept': 'application/json'
            }
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
        return self.session
    
    async def _rate_limit(self):
        """Simple rate limiting to avoid overwhelming the API"""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = asyncio.get_event_loop().time()
    
    async def _make_request(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Make an HTTP request to the Roblox API with error handling
        
        Args:
            url: Full URL to request
            params: Optional query parameters
        
        Returns:
            JSON response as dictionary, or None if request failed
        """
        await self._rate_limit()
        
        try:
            session = await self._get_session()
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    return None  # Not found
                elif response.status == 429:
                    # Rate limited, wait and retry once
                    print("Rate limited by Roblox API, waiting...")
                    await asyncio.sleep(2)
                    
                    async with session.get(url, params=params) as retry_response:
                        if retry_response.status == 200:
                            return await retry_response.json()
                        else:
                            print(f"Retry failed with status {retry_response.status}")
                            return None
                else:
                    print(f"API request failed with status {response.status}")
                    return None
                    
        except asyncio.TimeoutError:
            print("Request timed out")
            return None
        except Exception as e:
            print(f"Request error: {e}")
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get Roblox user data by username
        
        Args:
            username: Roblox username to search for
        
        Returns:
            User data dictionary with id, name, displayName, etc., or None if not found
        """
        url = f"{self.users_url}/usernames/users"
        params = {
            'usernames': username,
            'excludeBannedUsers': 'true'
        }
        
        response = await self._make_request(url, params)
        
        if response and response.get('data') and len(response['data']) > 0:
            return response['data'][0]
        
        return None
    
    async def get_user_gamepasses(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all gamepasses created by a user
        
        Args:
            user_id: Roblox user ID
        
        Returns:
            List of gamepass dictionaries with id, name, price, etc.
        """
        all_gamepasses = []
        cursor = ""
        max_pages = 10  # Prevent infinite loops
        pages_fetched = 0
        
        while pages_fetched < max_pages:
            url = f"{self.catalog_url}/search/items/details"
            params = {
                'Category': 'GamePass',
                'CreatorTargetId': user_id,
                'CreatorType': 'User',
                'SortType': 'Relevance',
                'limit': 30  # Maximum items per page
            }
            
            if cursor:
                params['cursor'] = cursor
            
            response = await self._make_request(url, params)
            
            if not response or not response.get('data'):
                break
            
            # Process gamepasses from this page
            for item in response['data']:
                if item.get('itemType') == 'GamePass' and item.get('price'):
                    gamepass = {
                        'id': item.get('id'),
                        'name': item.get('name', 'Unknown Gamepass'),
                        'price': item.get('price'),
                        'iconImageId': item.get('iconImageId'),
                        'creatorId': item.get('creatorTargetId'),
                        'creatorName': item.get('creatorName')
                    }
                    all_gamepasses.append(gamepass)
            
            # Check if there are more pages
            cursor = response.get('nextPageCursor')
            if not cursor:
                break
            
            pages_fetched += 1
        
        # Sort by price for easier matching
        all_gamepasses.sort(key=lambda x: x.get('price', 0))
        
        return all_gamepasses
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

# Utility functions for price calculations
def calculate_nct_price(input_price: int) -> int:
    """
    Calculate the actual gamepass price for NCT (not covered tax)
    Roblox takes 30% tax, so seller receives 70%
    
    Args:
        input_price: The price the buyer wants to pay
    
    Returns:
        The gamepass price needed to receive input_price after tax
    """
    return math.floor(input_price * 0.7)

def calculate_ct_price(input_price: int) -> int:
    """
    Calculate the gamepass price for CT (covered tax)
    No calculation needed - search for exact price
    
    Args:
        input_price: The exact gamepass price to search for
    
    Returns:
        The same input price
    """
    return input_price

def format_price_explanation(tax_option: str, input_price: int, target_price: int) -> str:
    """
    Create a formatted explanation of the price calculation
    
    Args:
        tax_option: 'CT' or 'NCT'
        input_price: Original price entered by user
        target_price: Calculated target price
    
    Returns:
        Formatted explanation string
    """
    if tax_option.upper() == 'NCT':
        return f"NCT: {input_price} Robux → searching for ~{target_price} Robux gamepass (70% after tax)"
    else:
        return f"CT: searching for exactly {input_price} Robux gamepass"
