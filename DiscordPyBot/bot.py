"""
KeilScanner Discord Bot
A Discord bot that finds Roblox gamepasses by username and calculates prices with tax options
"""

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio
import math
from typing import Optional, List, Dict, Any, Union
from roblox_api import RobloxAPI

class KeilScannerBot(commands.Bot):
    """Main Discord bot class for KeilScanner"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            description='A Discord bot that finds Roblox gamepasses by username with tax calculations'
        )
        
        self.roblox_api = RobloxAPI()
    
    async def setup_hook(self):
        """Setup hook called when bot is starting up"""
        if self.user:
            print(f"Setting up {self.user} (ID: {self.user.id})")
        else:
            print("Setting up bot...")
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Called when bot is ready and connected to Discord"""
        print(f'{self.user} has connected to Discord!')
        print(f'Bot is in {len(self.guilds)} guilds')
        
        # List available commands
        commands = [cmd.name for cmd in self.tree.get_commands()]
        print(f'Available slash commands: {commands}')
        
        # Set bot activity status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="for /getlink commands"
        )
        await self.change_presence(activity=activity)
    
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle slash command errors"""
        print(f"Slash command error: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ Command error: {error}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Command error: {error}", ephemeral=True)
    
    async def on_command_error(self, ctx, error):
        """Global error handler for commands"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        
        print(f"Command error: {error}")
        
        if ctx.interaction:
            if not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(
                    "❌ An error occurred while processing your command.",
                    ephemeral=True
                )

# Slash command for getting gamepass links
@app_commands.describe(
    username="Roblox username to search for gamepasses",
    price="Target price in Robux",
    tax_option="Tax calculation method"
)
@app_commands.choices(tax_option=[
    app_commands.Choice(name="CT (Covered Tax)", value="ct"),
    app_commands.Choice(name="NCT (Not Covered Tax)", value="nct")
])
async def getlink(interaction: discord.Interaction, username: str, price: int, tax_option: Optional[app_commands.Choice[str]] = None):
    """Find a Roblox gamepass by username and price with tax calculations"""
    
    print(f"Command received: /getlink {username} {price} {tax_option}")
    
    # Defer the response as this might take some time
    await interaction.response.defer()
    
    try:
        # Validate inputs
        if not username.strip():
            await interaction.followup.send("❌ Please provide a valid username.", ephemeral=True)
            return
        
        # Default to NCT if no tax option provided
        if tax_option is None:
            tax_value = "nct"
        else:
            tax_value = tax_option.value.lower()
        
        if tax_value not in ['ct', 'nct']:
            await interaction.followup.send(
                "❌ Invalid tax option. Please choose CT or NCT.",
                ephemeral=True
            )
            return
        
        if price <= 0:
            await interaction.followup.send("❌ Price must be a positive number.", ephemeral=True)
            return
        
        # Calculate target price based on tax option
        if tax_value == 'nct':
            # Not covered tax: calculate actual gamepass price (minus 30% Roblox tax)
            target_price = math.floor(price * 0.7)
            tax_explanation = f"NCT: {price} Robux → searching for ~{target_price} Robux gamepass (70% after tax)"
        else:
            # Covered tax: search for exact price
            target_price = price
            tax_explanation = f"CT: searching for exactly {price} Robux gamepass"
        
        # Get bot instance to access RobloxAPI
        bot = interaction.client
        if not hasattr(bot, 'roblox_api'):
            await interaction.followup.send("❌ Bot configuration error. Please try again later.", ephemeral=True)
            return
        
        roblox_api = getattr(bot, 'roblox_api')
        
        # Search for user and gamepasses
        user_data = await roblox_api.get_user_by_username(username)
        if not user_data:
            embed = discord.Embed(
                title="❌ User Not Found",
                description=f"Could not find Roblox user: **{username}**\n\nPlease check the spelling and try again.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        user_id = user_data['id']
        display_name = user_data.get('displayName', username)
        
        # Get user's gamepasses
        gamepasses = await roblox_api.get_user_gamepasses(user_id)
        if not gamepasses:
            embed = discord.Embed(
                title="❌ No Gamepasses Found",
                description=f"User **{display_name}** (@{username}) has no gamepasses available.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Find the best matching gamepass
        best_match = find_best_price_match(gamepasses, target_price)
        
        if not best_match:
            embed = discord.Embed(
                title="❌ No Matching Gamepass",
                description=f"Could not find a suitable gamepass for **{display_name}** (@{username})\n\n"
                          f"**Calculation:** {tax_explanation}\n"
                          f"**Available gamepasses:** {len(gamepasses)} found",
                color=discord.Color.red()
            )
            
            # Show some available gamepasses for reference
            if gamepasses:
                gamepass_list = []
                for gp in gamepasses[:5]:  # Show first 5
                    gamepass_list.append(f"• {gp['name']}: {gp['price']} Robux")
                
                if len(gamepasses) > 5:
                    gamepass_list.append(f"• ... and {len(gamepasses) - 5} more")
                
                embed.add_field(
                    name="Available Gamepasses",
                    value="\n".join(gamepass_list),
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            return
        
        # Create success embed
        gamepass = best_match['gamepass']
        price_diff = abs(gamepass['price'] - target_price)
        accuracy = max(0, 100 - (price_diff / target_price * 100))
        
        embed = discord.Embed(
            title="✅ Gamepass Found",
            description=f"Found matching gamepass for **{display_name}** (@{username})",
            color=discord.Color.green()
        )
        
        # Add gamepass details
        embed.add_field(
            name="🎮 Gamepass",
            value=f"**{gamepass['name']}**\n[View Gamepass](https://www.roblox.com/game-pass/{gamepass['id']})",
            inline=True
        )
        
        embed.add_field(
            name="💰 Price",
            value=f"**{gamepass['price']} Robux**\n{tax_explanation}",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Match Accuracy",
            value=f"**{accuracy:.1f}%**\n(±{price_diff} Robux)",
            inline=True
        )
        
        # Add thumbnail if available
        if gamepass.get('iconImageId'):
            embed.set_thumbnail(url=f"https://www.roblox.com/asset-thumbnail/image?assetId={gamepass['iconImageId']}&width=150&height=150&format=png")
        
        # Add footer
        embed.set_footer(text=f"keilscanner • Found from {len(gamepasses)} available gamepasses")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        print(f"Error in getlink command: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description="An unexpected error occurred while processing your request. Please try again later.",
            color=discord.Color.red()
        )
        try:
            await interaction.followup.send(embed=embed)
        except:
            # If followup fails, try editing the original response
            await interaction.edit_original_response(embed=embed)

def find_best_price_match(gamepasses: List[Dict[str, Any]], target_price: int) -> Optional[Dict[str, Any]]:
    """
    Find the gamepass with the closest price to the target price
    
    Args:
        gamepasses: List of gamepass dictionaries
        target_price: Target price to match
    
    Returns:
        Dictionary with 'gamepass' and 'accuracy' keys, or None if no suitable match
    """
    if not gamepasses:
        return None
    
    best_match = None
    best_diff = float('inf')
    
    for gamepass in gamepasses:
        if not gamepass.get('price') or gamepass['price'] <= 0:
            continue
            
        price_diff = abs(gamepass['price'] - target_price)
        
        # Prefer exact matches, then closer prices
        if price_diff < best_diff:
            best_diff = price_diff
            best_match = {
                'gamepass': gamepass,
                'price_diff': price_diff
            }
    
    # Return the best match if it's reasonably close (within 50% of target price)
    if best_match and best_diff <= (target_price * 0.5):
        return best_match
    
    return None

# Create bot instance and add the slash command
def create_bot():
    """Create and configure the bot instance"""
    bot = KeilScannerBot()
    
    # Add the slash command to the bot
    bot.tree.add_command(
        app_commands.Command(
            name="getlink",
            description="Find a Roblox gamepass by username and price with tax calculations",
            callback=getlink
        )
    )
    
    return bot
