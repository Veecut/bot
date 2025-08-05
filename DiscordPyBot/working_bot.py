"""
Working KeilScanner Discord Bot
Clean implementation that avoids interaction timeouts
"""

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio
import math
import os
from dotenv import load_dotenv

load_dotenv()

class WorkingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix='!',
            intents=intents
        )
        
        self.session = None
    
    async def setup_hook(self):
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} commands")
        except Exception as e:
            print(f"Sync failed: {e}")
    
    async def on_ready(self):
        print(f'{self.user} connected to Discord!')
        print(f'Bot is in {len(self.guilds)} guilds')
    
    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                headers={'User-Agent': 'keilscanner-bot/1.0'}
            )
        return self.session
    
    async def find_roblox_user(self, username):
        """Find Roblox user by username"""
        session = await self.get_session()
        url = "https://users.roblox.com/v1/usernames/users"
        
        try:
            async with session.post(url, json={"usernames": [username]}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('data') and len(data['data']) > 0:
                        return data['data'][0]
        except Exception as e:
            print(f"Error finding user {username}: {e}")
        return None
    
    async def get_user_gamepasses(self, user_id):
        """Get gamepasses for a user"""
        session = await self.get_session()
        
        # Try multiple endpoints to find gamepasses
        urls_to_try = [
            f"https://games.roblox.com/v1/games/list-by-owner?userId={user_id}&sortOrder=Asc&limit=50",
            f"https://catalog.roblox.com/v1/search/items?category=GamePass&creatorTargetId={user_id}&limit=50"
        ]
        
        gamepasses = []
        
        for url in urls_to_try:
            try:
                print(f"Trying URL: {url}")
                async with session.get(url) as resp:
                    print(f"Response status: {resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"Response data keys: {list(data.keys()) if data else 'None'}")
                        
                        # Handle different response formats
                        items = data.get('data', [])
                        if not items and 'games' in data:
                            items = data['games']
                        
                        print(f"Found {len(items)} items")
                        
                        # Look for gamepasses in the response
                        for item in items:
                            print(f"Item: {item.get('name', 'No name')} - Type: {item.get('itemType', 'No type')} - Price: {item.get('price', 'No price')}")
                            
                            # Check if this looks like a gamepass with a price
                            if (item.get('itemType') == 'GamePass' or 'gamepass' in item.get('name', '').lower()) and item.get('price'):
                                gamepasses.append({
                                    'id': item.get('id'),
                                    'name': item.get('name', 'Unknown'),
                                    'price': item.get('price')
                                })
                        
                        if gamepasses:
                            break  # Found some, no need to try other URLs
                            
            except Exception as e:
                print(f"Error with URL {url}: {e}")
                continue
        
        print(f"Total gamepasses found: {len(gamepasses)}")
        return gamepasses

bot = WorkingBot()

@bot.tree.command(name="getlink", description="Find Roblox gamepass by username and price")
@app_commands.describe(
    username="Roblox username",
    price="Target price in Robux",
    tax_option="Tax calculation (CT or NCT)"
)
@app_commands.choices(tax_option=[
    app_commands.Choice(name="CT (Covered Tax)", value="ct"),
    app_commands.Choice(name="NCT (Not Covered Tax)", value="nct")
])
async def getlink(interaction: discord.Interaction, username: str, price: int, tax_option: app_commands.Choice[str] = None):
    print(f"Command: /getlink {username} {price} {tax_option}")
    
    # Respond immediately
    await interaction.response.send_message("🔍 Searching...", ephemeral=True)
    
    try:
        # Calculate target price
        tax_val = tax_option.value if tax_option else "nct"
        target_price = int(price * 0.7) if tax_val == "nct" else price
        
        # Find user
        user_data = await bot.find_roblox_user(username)
        if not user_data:
            await interaction.edit_original_response(content=f"❌ User not found: {username}")
            return
        
        # Get gamepasses
        gamepasses = await bot.get_user_gamepasses(user_data['id'])
        if not gamepasses:
            await interaction.edit_original_response(content=f"❌ No gamepasses found for {username}")
            return
        
        # Find best match
        best_match = None
        best_diff = float('inf')
        
        for gp in gamepasses:
            diff = abs(gp['price'] - target_price)
            if diff < best_diff:
                best_diff = diff
                best_match = gp
        
        if not best_match:
            await interaction.edit_original_response(content=f"❌ No suitable gamepass found")
            return
        
        # Format response
        clean_name = best_match['name'].replace(' ', '-').replace('/', '').replace('\\', '')
        link = f"https://www.roblox.com/game-pass/{best_match['id']}/{clean_name}"
        response = f"1. {link}\nPrice: {best_match['price']}"
        
        await interaction.edit_original_response(content=response)
        print(f"Success: Found gamepass {best_match['id']} for {username}")
        
    except Exception as e:
        print(f"Command error: {e}")
        await interaction.edit_original_response(content=f"❌ Error occurred: {str(e)}")

if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if token:
        bot.run(token)
    else:
        print("No token found")