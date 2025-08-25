# Minimal diagnostic Telegram bot for Railway (no DB) + FastAPI health
# Purpose: prove updates reach the bot and replies work.

import os
import logging
import asyncio
import uvicorn
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# -----------------------------
# Config
# -----------------------------
class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    PORT = int(os.getenv("PORT", 8000))
    # Keep whitelist but don't block debug_id or plain messages while diagnosing
    ALLOWED_USER_IDS = [int(x) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip()]

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
)
logger = logging.getLogger("diag-bot")

# -----------------------------
# FastAPI (keeps Railway port open)
# -----------------------------
fastapi_app = FastAPI(title="Diag Bot API", version="1.0.0")
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

@fastapi_app.get("/")
async def root():
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}

@fastapi_app.get("/health")
async def health():
    return {"status": "healthy", "ts": datetime.now(timezone.utc).isoformat()}

# -----------------------------
# Telegram Handlers
# -----------------------------
async def debug_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id if update and update.effective_user else "unknown"
    logger.info(f"/debug_id from user {uid}")
    await update.effective_message.reply_text(f"Your Telegram user id: {uid}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    logger.info(f"/start from {uid}")
    await update.effective_message.reply_text("🤖 Bot online! Send me any text and I’ll echo it.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    logger.info(f"/help from {uid}")
    await update.effective_message.reply_text("Commands: /start /help /debug_id /menu")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    logger.info(f"/menu from {uid}")
    keyboard = [[
        InlineKeyboardButton("Ping", callback_data="ping"),
        InlineKeyboardButton("Status", callback_data="status"),
    ]]
    await update.effective_message.reply_text("🎛️ Menu", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    logger.info(f"callback '{q.data}' from {uid}")
    if q.data == "ping":
        await q.edit_message_text("pong")
    elif q.data == "status":
        await q.edit_message_text("📊 Bot alive and receiving updates ✅")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = (update.effective_message.text or "").strip()
    logger.info(f"message from {uid}: {text!r}")
    await update.effective_message.reply_text(f"echo: {text}")

# -----------------------------
# Main runner
# -----------------------------
async def main():
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.error("Missing TELEGRAM_BOT_TOKEN")
        return

    # Start FastAPI so Railway detects a listening port
    uv_config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=Config.PORT, log_level="info", loop="asyncio")
    uv_server = uvicorn.Server(uv_config)
    asyncio.create_task(uv_server.serve())

    # Build Telegram app
    app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("debug_id", debug_id))  # unauthenticated on purpose
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))  # echo any text

    # Make sure polling will receive updates (clear any webhook)
    await app.bot.delete_webhook(drop_pending_updates=True)
    logger.info("Deleted webhook (if any). Starting polling…")

    # Run polling (blocks until process stops)
    await app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())
