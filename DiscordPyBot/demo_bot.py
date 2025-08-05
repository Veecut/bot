"""
Demo Discord Bot to test the improved slash command format
"""

import discord
from discord.ext import commands
from discord import app_commands

class DemoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            description='Demo bot showing improved slash command format'
        )
    
    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        print(f'Bot is ready with improved slash commands!')
        
        # Set bot activity
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="for /getlink commands"
        )
        await self.change_presence(activity=activity)

# Improved slash command with dropdown choices
@app_commands.describe(
    username="Roblox username to search for gamepasses",
    price="Target price in Robux",
    tax_option="Tax calculation method (optional, defaults to NCT)"
)
@app_commands.choices(tax_option=[
    app_commands.Choice(name="CT (Covered Tax)", value="ct"),
    app_commands.Choice(name="NCT (Not Covered Tax)", value="nct")
])
async def getlink(interaction: discord.Interaction, username: str, price: int, tax_option: app_commands.Choice[str] = None):
    """Find a Roblox gamepass by username and price with tax calculations"""
    
    # Defer response
    await interaction.response.defer()
    
    # Default to NCT if no option selected
    if tax_option is None:
        tax_value = "nct"
        tax_display = "NCT (Not Covered Tax)"
    else:
        tax_value = tax_option.value
        tax_display = tax_option.name
    
    # Calculate target price
    if tax_value == 'nct':
        target_price = int(price * 0.7)
        explanation = f"Searching for ~{target_price} Robux gamepass (70% after 30% tax)"
    else:
        target_price = price
        explanation = f"Searching for exactly {price} Robux gamepass"
    
    # Create response embed
    embed = discord.Embed(
        title="🔍 Gamepass Search",
        description=f"Searching for **{username}**'s gamepasses",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="📊 Search Parameters",
        value=f"**Username:** {username}\n**Price:** {price} Robux\n**Tax Option:** {tax_display}",
        inline=False
    )
    
    embed.add_field(
        name="🧮 Calculation",
        value=explanation,
        inline=False
    )
    
    embed.add_field(
        name="ℹ️ Note",
        value="This is a demo showing the improved command format!\nThe real bot will search Roblox for actual gamepasses.",
        inline=False
    )
    
    embed.set_footer(text="keilscanner demo • Improved slash command format")
    
    await interaction.followup.send(embed=embed)

def create_demo_bot():
    """Create the demo bot with slash command"""
    bot = DemoBot()
    
    # Add the slash command
    bot.tree.add_command(
        app_commands.Command(
            name="getlink",
            description="Find a Roblox gamepass by username and price with tax calculations",
            callback=getlink
        )
    )
    
    return bot

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    token = os.getenv('DISCORD_BOT_TOKEN')
    
    if token:
        bot = create_demo_bot()
        bot.run(token)
    else:
        print("No token found - demo bot code ready!")