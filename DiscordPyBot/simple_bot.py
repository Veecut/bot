"""
Simplified KeilScanner Discord Bot
Fixed version with proper slash command registration
"""

import discord
from discord.ext import commands
from discord import app_commands
import math
import asyncio
import aiohttp
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv
from roblox_api import RobloxAPI

# Load environment variables
load_dotenv()

class SimpleBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            description='KeilScanner - Find Roblox gamepasses with tax calculations'
        )
        
        # Initialize Roblox API
        self.roblox_api = RobloxAPI()
    
    async def setup_hook(self):
        """Setup hook called when bot is starting up"""
        print("Setting up bot...")
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Called when bot is ready"""
        print(f'{self.user} has connected to Discord!')
        print(f'Bot is in {len(self.guilds)} guilds')
        
        # Set activity
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="for /getlink commands"
            )
        )

# Create bot instance
bot = SimpleBot()

@bot.tree.command(name="getlink", description="Find a Roblox gamepass by username and price")
@app_commands.describe(
    username="Roblox username to search for",
    price="Target price in Robux",
    tax_option="Tax calculation method (CT or NCT)"
)
@app_commands.choices(tax_option=[
    app_commands.Choice(name="CT (Covered Tax)", value="ct"),
    app_commands.Choice(name="NCT (Not Covered Tax)", value="nct")
])
async def getlink_command(interaction: discord.Interaction, username: str, price: int, tax_option: app_commands.Choice[str] = None):
    """Find Roblox gamepass with tax calculations"""
    
    print(f"Command received: /getlink {username} {price} {tax_option}")
    
    try:
        # Respond immediately to avoid timeout
        await interaction.response.send_message("🔍 Searching for gamepasses...", ephemeral=True)
        # Default to NCT
        if tax_option is None:
            tax_value = "nct"
            tax_display = "NCT (Not Covered Tax)"
        else:
            tax_value = tax_option.value
            tax_display = tax_option.name
        
        # Calculate target price based on tax option
        if tax_value == 'nct':
            target_price = int(price * 0.7)
        else:
            target_price = price
        
        # Search for user and gamepasses using Roblox API
        user_data = await bot.roblox_api.get_user_by_username(username)
        if not user_data:
            await interaction.edit_original_response(content=f"❌ User not found: **{username}**\nPlease check the spelling and try again.")
            return
        
        user_id = user_data['id']
        gamepasses = await bot.roblox_api.get_user_gamepasses(user_id)
        
        if not gamepasses:
            await interaction.edit_original_response(content=f"❌ No gamepasses found for **{username}**")
            return
        
        # Find the best matching gamepass by price
        best_match = None
        best_diff = float('inf')
        
        for gamepass in gamepasses:
            if not gamepass.get('price') or gamepass['price'] <= 0:
                continue
                
            price_diff = abs(gamepass['price'] - target_price)
            if price_diff < best_diff:
                best_diff = price_diff
                best_match = gamepass
        
        if not best_match:
            await interaction.edit_original_response(content=f"❌ No suitable gamepass found for **{username}** with target price {target_price} Robux")
            return
        
        # Format response as requested
        gamepass_link = f"https://www.roblox.com/game-pass/{best_match['id']}/{best_match['name'].replace(' ', '-')}"
        response = f"1. {gamepass_link}\nPrice: {best_match['price']}"
        
        await interaction.edit_original_response(content=response)
        print(f"Response sent for command: /getlink {username} {price}")
        
    except Exception as e:
        print(f"Error in getlink command: {e}")
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if token:
        print("Starting simplified bot...")
        bot.run(token)
    else:
        print("ERROR: No Discord bot token found!")