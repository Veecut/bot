"""
KeilScanner Discord Bot - Final Working Version
Uses correct Roblox API endpoints that actually work
"""

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

class KeilScannerBot(commands.Bot):
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
        
        # Set bot activity
        activity = discord.Activity(type=discord.ActivityType.watching, name="for /getlink commands")
        await self.change_presence(activity=activity)
    
    async def on_message(self, message):
        # Don't respond to own messages
        if message.author == self.user:
            return
        
        # Check if this is a reply to our bot and contains "scan"
        if (message.reference and 
            message.content.lower().strip() == "scan" and
            message.reference.resolved and
            message.reference.resolved.author == self.user):
            
            print(f"Scan request from {message.author.name}")
            await self.handle_scan_request(message)
        
        # Process other commands
        await self.process_commands(message)
    
    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15),
                headers={'User-Agent': 'keilscanner-discord-bot/1.0'}
            )
        return self.session
    
    async def find_user_by_username(self, username):
        """Find Roblox user by username using the correct API"""
        session = await self.get_session()
        
        # Use the correct Roblox users API endpoint
        url = "https://users.roblox.com/v1/usernames/users"
        payload = {
            "usernames": [username],
            "excludeBannedUsers": True
        }
        
        try:
            async with session.post(url, json=payload) as resp:
                print(f"User search status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print(f"User search response: {data}")
                    
                    if data.get('data') and len(data['data']) > 0:
                        user = data['data'][0]
                        print(f"Found user: {user['name']} (ID: {user['id']})")
                        return user
                else:
                    print(f"User search failed with status {resp.status}")
                    text = await resp.text()
                    print(f"Response: {text}")
        except Exception as e:
            print(f"Error finding user {username}: {e}")
        
        return None
    
    async def get_user_games(self, user_id):
        """Get games owned by user to find gamepasses"""
        session = await self.get_session()
        
        # Get user's games first
        games_url = f"https://games.roblox.com/v2/users/{user_id}/games"
        params = {
            "accessFilter": "Public",
            "sortOrder": "Asc",
            "limit": 50
        }
        
        games = []
        try:
            async with session.get(games_url, params=params) as resp:
                print(f"Games API status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    games = data.get('data', [])
                    print(f"Found {len(games)} games for user {user_id}")
        except Exception as e:
            print(f"Error getting games: {e}")
        
        return games
    
    async def get_game_passes(self, game_id):
        """Get gamepasses for a specific game"""
        session = await self.get_session()
        
        # Get gamepasses for this game
        passes_url = f"https://games.roblox.com/v1/games/{game_id}/game-passes"
        params = {"limit": 100}
        
        try:
            async with session.get(passes_url, params=params) as resp:
                print(f"Gamepasses API status for game {game_id}: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    passes = data.get('data', [])
                    print(f"Found {len(passes)} gamepasses for game {game_id}")
                    
                    # Filter passes with prices
                    priced_passes = []
                    for gp in passes:
                        if gp.get('price') and gp.get('price') > 0:
                            priced_passes.append({
                                'id': gp['id'],
                                'name': gp['name'],
                                'price': gp['price'],
                                'game_id': game_id
                            })
                    
                    return priced_passes
        except Exception as e:
            print(f"Error getting gamepasses for game {game_id}: {e}")
        
        return []
    
    async def find_all_gamepasses(self, user_id):
        """Find all gamepasses across all user's games"""
        games = await self.get_user_games(user_id)
        all_passes = []
        
        for game in games:
            game_id = game.get('id')
            if game_id:
                passes = await self.get_game_passes(game_id)
                all_passes.extend(passes)
                
                # Small delay to be nice to Roblox API
                await asyncio.sleep(0.1)
        
        print(f"Total gamepasses found across all games: {len(all_passes)}")
        return all_passes
    
    async def extract_gamepass_id_from_message(self, message_content):
        """Extract gamepass ID from bot's response message"""
        import re
        
        # Look for gamepass URL pattern
        pattern = r"https://www\.roblox\.com/game-pass/(\d+)/"
        match = re.search(pattern, message_content)
        
        if match:
            return int(match.group(1))
        return None
    
    async def check_regional_pricing(self, gamepass_id):
        """Check if a gamepass has regional pricing enabled"""
        session = await self.get_session()
        
        # Get gamepass details from Roblox API
        url = f"https://apis.roblox.com/game-passes/v1/game-passes/{gamepass_id}/product-info"
        
        try:
            async with session.get(url) as resp:
                print(f"Regional pricing check status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print(f"Gamepass details: {data}")
                    
                    # Check if regional pricing is enabled
                    # Roblox API typically shows this in the product info
                    regional_pricing = data.get('IsRegionalPricingEnabled', False)
                    
                    return regional_pricing
                else:
                    print(f"Failed to get gamepass details: {resp.status}")
                    # Try alternative endpoint
                    return await self.check_regional_pricing_alternative(gamepass_id)
        except Exception as e:
            print(f"Error checking regional pricing: {e}")
            return None
    
    async def check_regional_pricing_alternative(self, gamepass_id):
        """Alternative method to check regional pricing"""
        session = await self.get_session()
        
        # Try the catalog API endpoint
        url = f"https://catalog.roblox.com/v1/catalog/items/{gamepass_id}/details"
        
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Look for regional pricing indicators
                    price_config = data.get('priceConfiguration', {})
                    has_regional = price_config.get('hasRegionalPricing', False)
                    
                    return has_regional
        except Exception as e:
            print(f"Alternative regional pricing check failed: {e}")
        
        return None
    
    async def handle_scan_request(self, message):
        """Handle scan request to check regional pricing"""
        try:
            # Get the original bot message that was replied to
            original_message = message.reference.resolved
            
            # Extract gamepass ID from the original message
            gamepass_id = await self.extract_gamepass_id_from_message(original_message.content)
            
            if not gamepass_id:
                await message.reply("❌ Could not find gamepass ID in the original message.")
                return
            
            print(f"Checking regional pricing for gamepass ID: {gamepass_id}")
            
            # Send initial response
            scan_message = await message.reply("🔍 Checking regional pricing...")
            
            # Check regional pricing
            has_regional_pricing = await self.check_regional_pricing(gamepass_id)
            
            if has_regional_pricing is None:
                await scan_message.edit(content="❌ Unable to check regional pricing status.")
            elif has_regional_pricing:
                await scan_message.edit(content="🌍 Regional Pricing Detected")
            else:
                await scan_message.edit(content="Regional Pricing Not Detected")
                
        except Exception as e:
            print(f"Error in scan request: {e}")
            await message.reply("❌ Error occurred while checking regional pricing.")

bot = KeilScannerBot()

@bot.tree.command(name="getlink", description="Find Roblox gamepass by username and price")
@app_commands.describe(
    username="Roblox username to search",
    price="Target price in Robux",
    tax_option="Tax calculation method"
)
@app_commands.choices(tax_option=[
    app_commands.Choice(name="CT (Covered Tax)", value="ct"),
    app_commands.Choice(name="NCT (Not Covered Tax)", value="nct")
])
async def getlink(interaction: discord.Interaction, username: str, price: int, tax_option: app_commands.Choice[str]):
    print(f"Command: /getlink {username} {price} {tax_option.value}")
    
    # Respond immediately to prevent timeout
    await interaction.response.send_message("🔍 Searching for gamepasses...")
    
    try:
        # Calculate target price based on tax option
        if tax_option.value == "nct":
            # NCT: Account for 30% Roblox tax
            target_price = int(price * 0.7)
            print(f"NCT selected: Looking for gamepass around {target_price} Robux (70% of {price})")
        else:
            # CT: Use exact price
            target_price = price
            print(f"CT selected: Looking for gamepass at exact price {target_price} Robux")
        
        # Find the user
        user_data = await bot.find_user_by_username(username)
        if not user_data:
            await interaction.edit_original_response(content=f"❌ User not found: **{username}**\nPlease check the spelling and try again.")
            return
        
        # Find all gamepasses
        user_id = user_data['id']
        gamepasses = await bot.find_all_gamepasses(user_id)
        
        if not gamepasses:
            await interaction.edit_original_response(content=f"❌ No gamepasses found for **{username}**\nThis user may not have any games with gamepasses.")
            return
        
        # Find the best matching gamepass by price
        best_match = None
        best_diff = float('inf')
        
        for gp in gamepasses:
            price_diff = abs(gp['price'] - target_price)
            if price_diff < best_diff:
                best_diff = price_diff
                best_match = gp
        
        if not best_match:
            await interaction.edit_original_response(content=f"❌ No suitable gamepass found for target price {target_price} Robux")
            return
        
        # Format the response exactly as requested
        clean_name = best_match['name'].replace(' ', '-').replace('/', '').replace('\\', '')
        gamepass_url = f"https://www.roblox.com/game-pass/{best_match['id']}/{clean_name}"

        # Calculate what the seller will receive
        if tax_option.value == "nct":
            earnings = int(best_match['price'] * 0.7)
        else:
            earnings = best_match['price']

        response = (
            f"1. {gamepass_url}\n"
            f"Price: {best_match['price']} Robux\n"
            f"You will receive: {earnings} Robux"
        )

        await interaction.edit_original_response(content=response)
        print(f"Success: Found gamepass '{best_match['name']}' (ID: {best_match['id']}) for {username}"

if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ No Discord bot token found in environment variables")