#!/usr/bin/env python3
"""
Discord Bot Entry Point
Starts the keilscanner Discord bot
"""

import asyncio
import os
from dotenv import load_dotenv
from bot import create_bot

def main():
    """Main entry point for the Discord bot"""
    # Load environment variables
    load_dotenv()
    
    # Get Discord bot token from environment
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("ERROR: DISCORD_BOT_TOKEN not found in environment variables!")
        print("Please set your Discord bot token in the .env file or environment.")
        return
    
    # Create and run the bot
    bot = create_bot()
    
    try:
        print("Starting keilscanner Discord bot...")
        bot.run(token)
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"ERROR: Failed to start bot: {e}")

if __name__ == "__main__":
    main()
