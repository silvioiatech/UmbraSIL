# Ultra-minimal Telegram bot for Railway
# - polling only
# - no database
# - tiny built-in HTTP server so Railway sees an open port
# - /debug_id works for everyone (to grab your numeric ID)
# - /start, /help, /menu gated by ALLOWED_USER_IDS (optional)

import os
import logging
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

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
    PORT = int(os.getenv("PORT", "8080"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    # Comma-separated integers; empty means "no whitelist"
    _raw_ids = [x.strip() for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip()]
    ALLOWED_USER_IDS = []
    for x in _raw_ids:
        try:
            ALLOWED_USER_IDS.append(int(x))
        except ValueError:
            pass

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
)
logger = logging.getLogger("umbra-min")

# -----------------------------
# Tiny HTTP server (stdlib only)
# -----------------------------
class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # silence default console noise
    def log_message(self, *_args):
        return

def start_health_server():
    srv = HTTPServer(("0.0.0.0", Config.PORT), _HealthHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    logger.info(f"Health server listening on 0.0.0.0:{Config.PORT}")

# -----------------------------
# Auth helper (whitelist)
# -----------------------------
def is_allowed(user_id: int) -> bool:
    # empty whitelist means allow everyone
    if not Config.ALLOWED_USER_IDS:
        return True
    return user_id in Config.ALLOWED_USER_IDS

# -----------------------------
# Handlers
# -----------------------------
async def debug_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id if update and update.effective_user else "unknown"
    await update.effective_message.reply_text(f"Your Telegram user id: {uid}")

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        await update.effective_message.reply_text("🚫 Access denied.")
        return
    await update.effective_message.reply_text("🤖 Bot online! Try /menu or just say hi.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        await update.effective_message.reply_text("🚫 Access denied.")
        return
    await update.effective_message.reply_text("Commands: /debug_id /start /help /menu")

async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        await update.effective_message.reply_text("🚫 Access denied.")
        return
    kb = [[
        InlineKeyboardButton("Ping", callback_data="ping"),
        InlineKeyboardButton("Status", callback_data="status"),
    ]]
    await update.effective_message.reply_text("🎛️ Menu", reply_markup=InlineKeyboardMarkup(kb))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if not is_allowed(uid):
        await q.edit_message_text("🚫 Access denied.")
        return
    if q.data == "ping":
        await q.edit_message_text("pong")
    elif q.data == "status":
        await q.edit_message_text("📊 Bot alive and receiving updates ✅")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # echo anything typed; no auth check so you can see activity while diagnosing
    text = (update.effective_message.text or "").strip()
    await update.effective_message.reply_text(f"echo: {text}")

# -----------------------------
# Main runner
# -----------------------------
async def main():
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.error("Missing TELEGRAM_BOT_TOKEN env.")
        return

    # start tiny health server so Railway web service is happy
    start_health_server()

    # build bot
    app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

    # register handlers
    app.add_handler(CommandHandler("debug_id", debug_id))  # ALWAYS allowed
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("menu", menu_cmd))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # make sure no webhook blocks polling
    await app.bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook deleted (if any). Starting polling…")
    logger.info(f"Whitelist: {Config.ALLOWED_USER_IDS or 'disabled (allow all)'}")

    # run polling
    await app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())
