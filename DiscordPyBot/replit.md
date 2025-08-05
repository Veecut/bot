# KeilScanner Discord Bot

## Overview

KeilScanner is a Discord bot that integrates with the Roblox platform to find and analyze gamepasses by username. The bot provides functionality to search for Roblox gamepasses and calculate prices with tax options, making it useful for users who need to quickly access gamepass information and pricing calculations for Roblox items.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Bot Framework
- **Discord.py Library**: Uses the modern discord.py library with slash commands support
- **Command System**: Implements both traditional prefix commands (`!`) and modern slash commands (`/`)
- **Event-Driven Architecture**: Built on Discord.py's event system with setup hooks and ready events

### API Integration Layer
- **Roblox API Client**: Custom `RobloxAPI` class handles all interactions with Roblox web services
- **Rate Limiting**: Implements client-side rate limiting with minimum 100ms intervals between requests
- **Session Management**: Uses aiohttp for async HTTP requests with proper session lifecycle management
- **Error Handling**: Structured error handling for API failures and timeouts

### Application Structure
- **Modular Design**: Separated into distinct modules (bot.py, roblox_api.py, main.py)
- **Async/Await Pattern**: Fully asynchronous architecture using Python's asyncio
- **Configuration Management**: Environment-based configuration using python-dotenv

### Bot Features
- **Gamepass Discovery**: Searches for Roblox gamepasses by username
- **Price Calculations**: Calculates prices with Roblox tax considerations
- **Activity Status**: Sets dynamic bot presence showing current functionality

## External Dependencies

### Discord Platform
- **Discord Bot API**: Integrates with Discord's bot API for command handling and messaging
- **Slash Commands**: Uses Discord's application command system for modern user interactions

### Roblox Platform
- **Roblox API**: Connects to multiple Roblox API endpoints:
  - `api.roblox.com` - Main API services
  - `catalog.roblox.com/v1` - Catalog and item information
  - `users.roblox.com/v1` - User profile and data services

### Python Libraries
- **discord.py**: Primary Discord API wrapper
- **aiohttp**: Async HTTP client for external API calls
- **python-dotenv**: Environment variable management

### Configuration
- **Environment Variables**: Requires `DISCORD_BOT_TOKEN` for bot authentication
- **Runtime Environment**: Designed to run in containerized or cloud environments