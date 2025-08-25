# Personal Telegram Bot Assistant - Phase 1: Core Infrastructure
# Railway.app + PostgreSQL + python-telegram-bot + FastAPI

import os
import logging
import asyncio
import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

# FastAPI for potential web endpoints
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

# Telegram Bot
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Security & Auth
import hashlib
import hmac
from functools import wraps

# ==============================================================================
# CONFIGURATION & ENVIRONMENT VARIABLES
# ==============================================================================

class Config:
    """Centralized configuration management"""
    
    # Railway Environment Variables
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL")  # Railway PostgreSQL

    # These should be in your SystemConfig class
    ENABLE_FINANCE = os.getenv("ENABLE_FINANCE", "true").lower() == "true"
    ENABLE_BUSINESS = os.getenv("ENABLE_BUSINESS", "false").lower() == "true"  # Disabled by default
    ENABLE_MONITORING = os.getenv("ENABLE_MONITORING", "true").lower() == "true"
    ENABLE_AI = os.getenv("ENABLE_AI", "false").lower() == "true"  # Disabled by default
    ENABLE_BI = os.getenv("ENABLE_BI", "true").lower() == "true"

    # Security
    ALLOWED_USER_IDS = [int(x) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip()]
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this")

    # Optional 2FA
    ENABLE_2FA = os.getenv("ENABLE_2FA", "false").lower() == "true"
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # FastAPI
    PORT = int(os.getenv("PORT", 8000))

# ==============================================================================
# LOGGING SETUP
# ==============================================================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL.upper())
)
logger = logging.getLogger(__name__)

# ==============================================================================
# DATABASE CONNECTION MANAGER
# ==============================================================================

class DatabaseManager:
    """Handles PostgreSQL connections and operations"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool = None
    
    async def initialize(self):
        """Initialize connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool initialized")
            await self.create_tables()
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def create_tables(self):
        """Create necessary tables for Phase 1"""
        async with self.pool.acquire() as conn:
            # Users table for authentication
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_user_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    is_authorized BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_login TIMESTAMP WITH TIME ZONE
                )
            ''')
            
            # Bot logs table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS bot_logs (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    command VARCHAR(255),
                    message TEXT,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                )
            ''')
            
            # System metrics (for future phases)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id SERIAL PRIMARY KEY,
                    metric_type VARCHAR(100) NOT NULL,
                    metric_value FLOAT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    metadata JSONB
                )
            ''')
            
            # Expenses (Phase 2 preparation)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    description TEXT,
                    date DATE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    receipt_path VARCHAR(500)
                )
            ''')
            
            # Income (Phase 2 preparation)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS income (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    source VARCHAR(100) NOT NULL,
                    description TEXT,
                    date DATE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            logger.info("Database tables created/verified")
    
    async def log_command(self, user_id: int, command: str, message: str, success: bool = True, error: str = None):
        """Log bot commands for monitoring"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO bot_logs (user_id, command, message, success, error_message)
                VALUES ($1, $2, $3, $4, $5)
            ''', user_id, command, message, success, error)
    
    async def get_user(self, telegram_user_id: int) -> Optional[Dict]:
        """Get user from database"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT * FROM users WHERE telegram_user_id = $1',
                telegram_user_id
            )
            return dict(row) if row else None
    
    async def create_or_update_user(self, telegram_user_id: int, username: str = None, 
                                   first_name: str = None, last_name: str = None) -> Dict:
        """Create or update user"""
        async with self.pool.acquire() as conn:
            # Check if authorized
            is_authorized = telegram_user_id in Config.ALLOWED_USER_IDS
            
            await conn.execute('''
                INSERT INTO users (telegram_user_id, username, first_name, last_name, is_authorized, last_login)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (telegram_user_id)
                DO UPDATE SET 
                    username = $2,
                    first_name = $3,
                    last_name = $4,
                    last_login = NOW()
            ''', telegram_user_id, username, first_name, last_name, is_authorized)
            
            return await self.get_user(telegram_user_id)

# ==============================================================================
# AUTHENTICATION & SECURITY
# ==============================================================================

def require_auth(func):
    """Decorator to require authentication for bot commands"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Check if user is authorized
        if user_id not in Config.ALLOWED_USER_IDS:
            await update.message.reply_text(
                "🚫 Access denied. You are not authorized to use this bot."
            )
            await db_manager.log_command(
                user_id, func.__name__, "Unauthorized access attempt", False, "User not in whitelist"
            )
            return
        
        # Update user info
        user = update.effective_user
        await db_manager.create_or_update_user(
            user.id, user.username, user.first_name, user.last_name
        )
        
        return await func(update, context)
    
    return wrapper

# ==============================================================================
# TELEGRAM BOT HANDLERS
# ==============================================================================

class PersonalBotAssistant:
    """Main bot class with modular structure"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.application = None
    
    def setup_handlers(self):
        """Setup all command and message handlers"""
        if not self.application:
            raise RuntimeError("Application not initialized")
        
        # Basic commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("menu", self.main_menu_command))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Message handler for text messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    @require_auth
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        user = update.effective_user
        welcome_text = f"""
🤖 **Personal Bot Assistant** - Phase 1 Active!

Welcome {user.first_name}! 👋

This bot will be your digital shadow for:
💰 Finance Management
⚙️ Business Workflows  
📊 VPS Monitoring
🧠 AI Assistant

Currently in **Phase 1** - Core Infrastructure ✅

Use /menu to see available options or /help for commands.
        """
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
        await self.db.log_command(user.id, "start", "User started bot", True)
    
    @require_auth
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command handler"""
        help_text = """
📚 **Available Commands:**

🔧 **Core Commands:**
/start - Welcome message
/help - Show this help
/status - Bot status
/menu - Main menu

💰 **Finance (Phase 2 - Coming Soon):**
/add_expense - Add expense
/add_income - Add income  
/expenses_month - Monthly report

⚙️ **Business (Phase 3 - Coming Soon):**
/clients - Manage clients
/monitor - System monitoring

🧠 **AI Assistant (Phase 5 - Coming Soon):**
Natural language commands will work here!
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
        await self.db.log_command(update.effective_user.id, "help", "Help requested", True)
    
    @require_auth
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Status command handler"""
        try:
            # Check database connection
            async with self.db.pool.acquire() as conn:
                await conn.fetchval('SELECT 1')
            
            db_status = "✅ Connected"
        except Exception as e:
            db_status = f"❌ Error: {str(e)[:50]}..."
        
        status_text = f"""
📊 **Bot Status Report**

🤖 **Bot:** ✅ Online
💾 **Database:** {db_status}
🔐 **Auth:** ✅ Enabled (Whitelist: {len(Config.ALLOWED_USER_IDS)} users)
🛡️ **2FA:** {"✅ Enabled" if Config.ENABLE_2FA else "❌ Disabled"}

📈 **Current Phase:** 1 - Core Infrastructure
🚀 **Next Phase:** 2 - Finance Management

⏰ **Uptime:** Just started
🏗️ **Environment:** Railway.app
        """
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
        await self.db.log_command(update.effective_user.id, "status", "Status checked", True)
    
    @require_auth
    async def main_menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Main menu with inline keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("💰 Finances", callback_data="menu_finance"),
                InlineKeyboardButton("⚙️ Business", callback_data="menu_business")
            ],
            [
                InlineKeyboardButton("📊 Monitoring", callback_data="menu_monitoring"),
                InlineKeyboardButton("🧠 AI Assistant", callback_data="menu_ai")
            ],
            [
                InlineKeyboardButton("ℹ️ Status", callback_data="menu_status"),
                InlineKeyboardButton("❓ Help", callback_data="menu_help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎛️ **Main Menu** - Choose a category:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        await self.db.log_command(update.effective_user.id, "menu", "Main menu opened", True)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        user_id = query.from_user.id
        
        # Check authorization
        if user_id not in Config.ALLOWED_USER_IDS:
            await query.answer("🚫 Access denied", show_alert=True)
            return
        
        await query.answer()  # Acknowledge the callback
        
        callback_data = query.data
        
        if callback_data == "menu_finance":
            await query.edit_message_text(
                "💰 **Finance Management**\n\n"
                "Coming in Phase 2! Will include:\n"
                "• Expense tracking\n"
                "• Income management\n" 
                "• OCR receipts\n"
                "• Financial reports\n\n"
                "Use /menu to go back.",
                parse_mode='Markdown'
            )
        elif callback_data == "menu_business":
            await query.edit_message_text(
                "⚙️ **Business Workflows**\n\n"
                "Coming in Phase 3! Will include:\n"
                "• n8n client management\n"
                "• VPS connections\n"
                "• Docker monitoring\n\n"
                "Use /menu to go back.",
                parse_mode='Markdown'
            )
        elif callback_data == "menu_monitoring":
            await query.edit_message_text(
                "📊 **System Monitoring**\n\n"
                "Coming in Phase 4! Will include:\n"
                "• VPS metrics\n"
                "• Alert system\n"
                "• Health reports\n\n"
                "Use /menu to go back.",
                parse_mode='Markdown'
            )
        elif callback_data == "menu_ai":
            await query.edit_message_text(
                "🧠 **AI Assistant**\n\n"
                "Coming in Phase 5! Will include:\n"
                "• GPT-4 + Claude integration\n"
                "• Natural language commands\n"
                "• Voice transcription\n\n"
                "Use /menu to go back.",
                parse_mode='Markdown'
            )
        elif callback_data == "menu_status":
            await self.status_command(query, context)
        elif callback_data == "menu_help":
            await self.help_command(query, context)
        
        await self.db.log_command(user_id, f"callback_{callback_data}", "Menu callback", True)
    
    @require_auth
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (for future AI integration)"""
        message_text = update.message.text.lower()
        
        # Simple responses for Phase 1
        if any(word in message_text for word in ['hello', 'hi', 'hey']):
            await update.message.reply_text(
                "👋 Hello! I'm your Personal Bot Assistant.\n"
                "Use /menu to see what I can do!"
            )
        elif any(word in message_text for word in ['status', 'health']):
            await self.status_command(update, context)
        else:
            await update.message.reply_text(
                "🤔 I don't understand that yet.\n"
                "In Phase 5, I'll have AI capabilities!\n"
                "For now, use /help or /menu."
            )
        
        await self.db.log_command(
            update.effective_user.id, 
            "message", 
            f"Processed: {message_text[:100]}", 
            True
        )

# ==============================================================================
# FASTAPI APPLICATION (Optional web endpoints)
# ==============================================================================

fastapi_app = FastAPI(title="Personal Bot Assistant API", version="1.0.0")

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@fastapi_app.get("/")
async def root():
    return {"message": "Personal Bot Assistant API - Phase 1", "status": "active"}

@fastapi_app.get("/health")
async def health_check():
    try:
        # Check database
        async with db_manager.pool.acquire() as conn:
            await conn.fetchval('SELECT 1')
        db_healthy = True
    except:
        db_healthy = False
    
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
        "phase": 1,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ==============================================================================
# MAIN APPLICATION RUNNER
# ==============================================================================

# Global database manager
db_manager = None

async def main():
    """Main application entry point"""
    global db_manager
    
    # Validate configuration
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is required")
        return
    
    if not Config.DATABASE_URL:
        logger.error("DATABASE_URL environment variable is required")
        return
    
    if not Config.ALLOWED_USER_IDS:
        logger.error("ALLOWED_USER_IDS environment variable is required")
        return
    
    try:
        # Initialize database
        db_manager = DatabaseManager(Config.DATABASE_URL)
        await db_manager.initialize()
        
        # Initialize bot
        bot = PersonalBotAssistant(db_manager)
        bot.application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        bot.setup_handlers()
        
        # Start bot
        logger.info("Starting Personal Bot Assistant - Phase 1")
        logger.info(f"Authorized users: {Config.ALLOWED_USER_IDS}")
        
        # Run the bot
        await bot.application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        raise
    finally:
        if db_manager:
            await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())

# ==============================================================================
# REQUIREMENTS.txt (for Railway deployment)
# ==============================================================================

"""
# Add this to requirements.txt:

fastapi==0.104.1
uvicorn[standard]==0.24.0
python-telegram-bot==20.7
asyncpg==0.29.0
python-dotenv==1.0.0
"""

# ==============================================================================
# RAILWAY DEPLOYMENT INSTRUCTIONS
# ==============================================================================

"""
🚀 RAILWAY DEPLOYMENT STEPS:

1. **Create Railway Project:**
   - Connect your GitHub repo
   - Enable auto-deploy from main branch

2. **Add PostgreSQL Database:**
   - Go to your project dashboard
   - Click "New" → "Database" → "PostgreSQL"
   - Railway will provide DATABASE_URL automatically

3. **Set Environment Variables:**
   - TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
   - ALLOWED_USER_IDS=123456789,987654321  (comma-separated)
   - SECRET_KEY=your-super-secret-key-here
   - ENABLE_2FA=false  (optional)
   - LOG_LEVEL=INFO
   - PORT=8000

4. **Deploy:**
   - Push to GitHub
   - Railway will auto-deploy
   - Check logs for any issues

5. **Test:**
   - Start your bot with /start
   - Try /menu and /status commands
   - Verify database connectivity

🔒 SECURITY CHECKLIST:
- ✅ User ID whitelist implemented
- ✅ Environment variables secured
- ✅ Database connection pooling
- ✅ Command logging for monitoring
- ✅ Error handling and validation

📝 NEXT STEPS (Phase 2):
- Add expense/income CRUD operations
- Integrate Google Vision API for OCR
- Create financial reporting with matplotlib
- Add CSV export functionality
"""
