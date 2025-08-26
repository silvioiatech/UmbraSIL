#!/usr/bin/env python3
"""
Alternative main.py implementation for Railway deployment
This version avoids the asyncio event loop conflicts
"""

import os
import sys
import logging
import signal
from dotenv import load_dotenv
from telegram.ext import Application

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import the Bot class from the main file
# We'll modify the main.py to use a different approach

def main():
    """Simple main function that uses the built-in polling"""
    try:
        # Get token
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
        
        logger.info("Starting UmbraSIL Bot...")
        
        # Create application
        application = Application.builder().token(token).build()
        
        # Import and setup handlers (we'll need to refactor this)
        # For now, let's create a minimal working version
        
        # Run the bot
        application.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
