# bot/core/security.py
import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from .config import SystemConfig
from .logger import logger

def require_auth(func):
    """Decorator to require authentication for bot commands"""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Check if user is authorized
        if user_id not in SystemConfig.ALLOWED_USER_IDS:
            logger.warning(f"Unauthorized access attempt from user {user_id}")
            await update.message.reply_text(
                "🚫 Access denied. You are not authorized to use this bot."
            )
            await self.db.log_command(
                user_id, func.__name__, "Unauthorized access attempt", False, "User not in whitelist"
            )
            return
        
        # Update user info
        user = update.effective_user
        await self.db.create_or_update_user(
            user.id, user.username, user.first_name, user.last_name
        )
        
        return await func(self, update, context)
    
    return wrapper
