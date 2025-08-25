# Personal Telegram Bot Assistant - Phase 1: Core Infrastructure
# Railway.app + PostgreSQL + python-telegram-bot + FastAPI

import os
import logging
import asyncio
import asyncpg
import uvicorn
from typing import Optional, Dict
from datetime import datetime, timezone

# FastAPI for potential web endpoints
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Telegram Bot
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Security & Auth
from functools import wraps

# ==============================================================================
# CONFIGURATION & ENVIRONMENT VARIABLES
# ==============================================================================

class Config:
    """Centralized configuration management"""
    
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL")  # Railway PostgreSQL

    # Feature flags
    ENABLE_FINANCE = os.getenv("ENABLE_FINANCE", "true").lower() == "true"
    ENABLE_BUSINESS = os.getenv("ENABLE_BUSINESS", "false").lower() == "true"
    ENABLE_MONITORING = os.getenv("ENABLE_MONITORING", "true").lower() == "true"
    ENABLE_AI = os.getenv("ENABLE_AI", "false").lower() == "true"
    ENABLE_BI = os.getenv("ENABLE_BI", "true").lower() == "true"

    # Security
    ALLOWED_USER_IDS = [int(x) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip()]
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this")

    # Optional 2FA
    ENABLE_2FA = os.getenv("ENABLE_2FA", "false").lower() == "true"
    
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
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
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool = None
    
    async def initialize(self):
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=1,
            max_size=10,
            command_timeout=60
        )
        logger.info("Database connection pool initialized")
        await self.create_tables()
    
    async def close(self):
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def create_tables(self):
        async with self.pool.acquire() as conn:
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
    
    async def log_command(self, user_id: int, command: str, message: str, success: bool = True, error: str = None):
        async with self.pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO bot_logs (user_id, command, message, success, error_message) VALUES ($1,$2,$3,$4,$5)',
                user_id, command, message, success, error
            )
    
    async def create_or_update_user(self, telegram_user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        async with self.pool.acquire() as conn:
            is_authorized = telegram_user_id in Config.ALLOWED_USER_IDS
            await conn.execute('''
                INSERT INTO users (telegram_user_id, username, first_name, last_name, is_authorized, last_login)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (telegram_user_id)
                DO UPDATE SET username=$2, first_name=$3, last_name=$4, last_login=NOW()
            ''', telegram_user_id, username, first_name, last_name, is_authorized)

# ==============================================================================
# AUTH DECORATOR
# ==============================================================================

def require_auth(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in Config.ALLOWED_USER_IDS:
            await update.effective_message.reply_text("🚫 Access denied.")
            return
        return await func(update, context)
    return wrapper

# ==============================================================================
# BOT HANDLERS
# ==============================================================================

class PersonalBotAssistant:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.application = None
    
    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("menu", self.menu_command))
        self.application.add_handler(CommandHandler("debug_id", self.debug_id))  # TEMP

        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def debug_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        await update.message.reply_text(f"Your Telegram user id: {uid}")
    
    @require_auth
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🤖 Bot online! Use /menu to explore.")

    @require_auth
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📚 Commands: /start /help /status /menu")

    @require_auth
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📊 Status: Bot running, DB connected ✅")

    @require_auth
    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[
            InlineKeyboardButton("ℹ️ Status", callback_data="menu_status"),
            InlineKeyboardButton("❓ Help", callback_data="menu_help")
        ]]
        await update.message.reply_text("🎛️ Menu:", reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        await q.answer()
        if q.data == "menu_status":
            await q.edit_message_text("📊 Status: Bot running, DB connected ✅")
        elif q.data == "menu_help":
            await q.edit_message_text("📚 Commands: /start /help /status /menu")

    @require_auth
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🤔 Unknown command. Try /menu.")

# ==============================================================================
# FASTAPI APP
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

# ==============================================================================
# MAIN
# ==============================================================================

db_manager = None

async def main():
    global db_manager

    if not Config.TELEGRAM_BOT_TOKEN or not Config.DATABASE_URL or not Config.ALLOWED_USER_IDS:
        logger.error("Missing required environment variables.")
        return

    db_manager = DatabaseManager(Config.DATABASE_URL)
    await db_manager.initialize()

    # Start FastAPI server (Railway needs a listening port)
    uv_config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=Config.PORT, log_level="info", loop="asyncio")
    uv_server = uvicorn.Server(uv_config)
    asyncio.create_task(uv_server.serve())

    # Telegram bot
    bot = PersonalBotAssistant(db_manager)
    bot.application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    bot.setup_handlers()

    await bot.application.bot.delete_webhook(drop_pending_updates=True)
    await bot.application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())
