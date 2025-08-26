import logging
from datetime import datetime
from functools import wraps
from typing import Optional, Callable, List
import os

# Configure logging
logger = logging.getLogger(__name__)

class BotError(Exception):
    """Base class for bot errors"""
    pass

class DatabaseError(BotError):
    """Database related errors"""
    pass

class AuthenticationError(BotError):
    """Authentication related errors"""
    pass

class DatabaseManager:
    """Database management class"""
    
    def __init__(self):
        self.connected = True
    
    async def initialize(self):
        """Initialize database connection"""
        self.connected = True
        logger.info("Database initialized")
    
    async def check_connection(self) -> bool:
        """Check database connection"""
        return self.connected

class SecurityManager:
    """Security management class"""
    
    def __init__(self):
        self.authenticated = False
        # Get allowed users from environment or use default
        allowed_ids = os.getenv("ALLOWED_USER_IDS", "8286836821")
        self.allowed_users = [int(x.strip()) for x in allowed_ids.split(",") if x.strip()]
    
    async def authenticate_user(self, user_id: int) -> bool:
        """Authenticate a user"""
        return user_id in self.allowed_users

def require_auth(func: Callable):
    """Decorator to require authentication for commands"""
    @wraps(func)
    async def wrapper(self, update, context, *args, **kwargs):
        if not update.effective_user:
            return
        
        user_id = update.effective_user.id
        if not await self.security.authenticate_user(user_id):
            if update.message:
                await update.message.reply_text(
                    "🚫 You are not authorized to use this command."
                )
            elif update.callback_query:
                await update.callback_query.answer("🚫 Access denied", show_alert=True)
            return
        return await func(self, update, context, *args, **kwargs)
    return wrapper
