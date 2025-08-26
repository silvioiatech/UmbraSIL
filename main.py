import os
import sys
import logging
import psutil
import platform
import asyncio
from aiohttp import web
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# Bot Configuration
BOT_VERSION = "1.0.0"
BOT_AUTHOR = "silvioiatech"
BOT_NAME = "UmbraSIL"

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class BotMetrics:
    """Track bot performance metrics"""
    
    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.command_count = 0
        self.error_count = 0
        self.active_users: Dict[int, datetime] = {}
        self.response_times: List[float] = []
    
    def log_command(self, response_time: float):
        self.command_count += 1
        self.response_times.append(response_time)
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]
    
    def log_error(self, error: str):
        self.error_count += 1
    
    def log_user_activity(self, user_id: int):
        self.active_users[user_id] = datetime.now(timezone.utc)
    
    def get_uptime(self) -> timedelta:
        return datetime.now(timezone.utc) - self.start_time
    
    def get_success_rate(self) -> float:
        if self.command_count == 0:
            return 100.0
        return ((self.command_count - self.error_count) / self.command_count) * 100

class SimpleAuth:
    """Simple authentication system"""
    
    def __init__(self):
        # Get allowed users from environment
        allowed_ids = os.getenv("ALLOWED_USER_IDS", "8286836821")
        self.allowed_users = [int(x.strip()) for x in allowed_ids.split(",") if x.strip()]
    
    async def authenticate_user(self, user_id: int) -> bool:
        return user_id in self.allowed_users

class UmbraSILBot:
    """Main bot class - simplified and working"""
    
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
        
        # Initialize components
        self.metrics = BotMetrics()
        self.auth = SimpleAuth()
        
        # Create application
        self.application = Application.builder().token(self.token).build()
        
        # Setup handlers immediately
        self.setup_handlers()
        
        logger.info("UmbraSIL Bot initialized successfully")
    
    def setup_handlers(self):
        """Setup all bot handlers"""
        # Core handlers with auth
        self.application.add_handler(CommandHandler("start", self.require_auth(self.start_command)))
        self.application.add_handler(CommandHandler("help", self.require_auth(self.help_command)))
        self.application.add_handler(CommandHandler("status", self.require_auth(self.status_command)))
        self.application.add_handler(CommandHandler("menu", self.require_auth(self.main_menu_command)))
        self.application.add_handler(CallbackQueryHandler(self.require_auth(self.button_handler)))
        
        # Error handler
        self.application.add_error_handler(self.handle_error)
        
        logger.info("All handlers setup completed")

    def require_auth(self, func):
        """Authentication decorator"""
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not update.effective_user:
                return
                
            user_id = update.effective_user.id
            if not await self.auth.authenticate_user(user_id):
                if update.message:
                    await update.message.reply_text("🚫 Access denied. You are not authorized to use this bot.")
                elif update.callback_query:
                    await update.callback_query.answer("🚫 Access denied", show_alert=True)
                return
                
            return await func(update, context)
        return wrapper

    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            uptime = self.metrics.get_uptime()
            success_rate = self.metrics.get_success_rate()
            
            return {
                "system": {
                    "platform": platform.platform(),
                    "python": platform.python_version(),
                    "uptime": str(uptime).split('.')[0]
                },
                "resources": {
                    "cpu": f"{cpu_percent}%",
                    "memory": f"{memory.percent}%",
                    "disk": f"{disk.percent}%"
                },
                "performance": {
                    "success_rate": f"{success_rate:.1f}%",
                    "commands_handled": self.metrics.command_count
                }
            }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        self.metrics.log_user_activity(user.id)
        
        welcome_text = f"""
🤖 **Welcome {user.first_name}!**

I'm UmbraSIL, your personal assistant bot with comprehensive business management capabilities.

🔥 **Core Features**:
💰 **Finance Management** - Track expenses & income
⚙️ **Business Operations** - Manage workflows & systems  
📊 **System Monitoring** - Real-time health & alerts
🤖 **AI Assistant** - Natural language processing

Use the buttons below to get started!
"""
        keyboard = [
            [
                InlineKeyboardButton("📚 Commands", callback_data="show_help"),
                InlineKeyboardButton("📊 Status", callback_data="show_status")
            ],
            [
                InlineKeyboardButton("💰 Finance", callback_data="menu_finance"),
                InlineKeyboardButton("⚙️ Business", callback_data="menu_business")
            ],
            [
                InlineKeyboardButton("📊 Monitoring", callback_data="menu_monitoring"),
                InlineKeyboardButton("🤖 AI Assistant", callback_data="menu_ai")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )        
        self.metrics.log_command(1.0)

    async def show_health_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed health check"""
        try:
            # Get detailed system info
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get process info
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # Determine health status
            health_status = "✅ HEALTHY"
            if cpu_percent > 80 or memory.percent > 80 or disk.percent > 90:
                health_status = "⚠️ WARNING"
            if cpu_percent > 95 or memory.percent > 95 or disk.percent > 95:
                health_status = "🚨 CRITICAL"
            
            health_text = f"""
❤️ **System Health Check**

🟢 **Overall Status**: {health_status}

💻 **System Resources**
• CPU Usage: `{cpu_percent:.1f}%`
• Memory: `{memory.percent:.1f}%` ({memory.used // 1024**2} MB / {memory.total // 1024**2} MB)
• Disk: `{disk.percent:.1f}%` ({disk.used // 1024**3} GB / {disk.total // 1024**3} GB)

🤖 **Bot Process**
• Memory Usage: `{process_memory.rss // 1024**2} MB`
• Uptime: `{self.metrics.get_uptime()}`
• Commands Handled: `{self.metrics.command_count}`

🔄 **Last Updated**: {datetime.now().strftime('%H:%M:%S')}
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="health_check"),
                    InlineKeyboardButton("🔙 Back", callback_data="menu_monitoring")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                health_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            await update.callback_query.edit_message_text(
                "❌ Error getting health status",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="menu_monitoring")
                ]])
            )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
**📚 Command Reference**

**Core Commands**
/start - Initialize bot
/help - Show this help
/status - System status
/menu - Main menu

💡 **Quick Tips**
• Use buttons for easy navigation
• All modules are being actively developed
• More features coming soon!

🆘 **Need Help?**
Contact the developer or check documentation.
"""
        keyboard = [
            [
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
                InlineKeyboardButton("📊 Status", callback_data="show_status")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        status = await self.get_system_status()
        
        status_text = f"""
📊 **System Status Report**

🖥️ **System Info**
• Platform: `{status['system']['platform']}`
• Python: `{status['system']['python']}`
• Uptime: `{status['system']['uptime']}`

📊 **Resources**
• CPU: `{status['resources']['cpu']}`
• Memory: `{status['resources']['memory']}`
• Disk: `{status['resources']['disk']}`

⚡ **Performance**
• Success Rate: `{status['performance']['success_rate']}`
• Commands: `{status['performance']['commands_handled']}`

🚀 **Status**: All systems operational!
"""
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh_status"),
                InlineKeyboardButton("🏠 Menu", callback_data="main_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            status_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def main_menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command"""
        keyboard = [
            [
                InlineKeyboardButton("💰 Finance", callback_data="menu_finance"),
                InlineKeyboardButton("⚙️ Business", callback_data="menu_business")
            ],
            [
                InlineKeyboardButton("📊 Monitoring", callback_data="menu_monitoring"),
                InlineKeyboardButton("🤖 AI Assistant", callback_data="menu_ai")
            ],
            [
                InlineKeyboardButton("📊 Status", callback_data="show_status"),
                InlineKeyboardButton("❓ Help", callback_data="show_help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = "🏠 **Main Menu**\nSelect a module or action:"
        
        if update.message:
            await update.message.reply_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        try:
            callback_data = query.data
            
            # Main navigation
            if callback_data == "main_menu":
                await self.main_menu_command(update, context)
            elif callback_data == "show_help":
                await self.show_help_callback(update, context)
            elif callback_data == "show_status" or callback_data == "refresh_status":
                await self.show_status_callback(update, context)
            
            # Module menus
            elif callback_data.startswith("menu_"):
                module_name = callback_data.split("_")[1]
                await self.show_module_menu(update, context, module_name)
            
            # Finance features
            elif callback_data in ["add_expense", "add_income", "show_balance", "finance_report"]:
                await query.edit_message_text(
                    "💰 **Finance Feature**\n\nThis feature is coming soon! Stay tuned for updates.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Back", callback_data="menu_finance")
                    ]])
                )
            
            # Business features  
            elif callback_data in ["n8n_clients", "docker_status", "vps_status", "system_metrics"]:
                await query.edit_message_text(
                    "⚙️ **Business Feature**\n\nThis feature is coming soon! Stay tuned for updates.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Back", callback_data="menu_business")
                    ]])
                )
            
            # Monitoring features
            elif callback_data in ["view_alerts", "view_logs"]:
                await query.edit_message_text(
                    "📊 **Monitoring Feature**\n\nThis feature is coming soon! Stay tuned for updates.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Back", callback_data="menu_monitoring")
                    ]])
                )
            
            # Working health check feature
            elif callback_data == "health_check":
                await self.show_health_check(update, context)
            
            # AI features
            elif callback_data in ["ask_ai", "clear_context", "voice_mode", "ai_settings"]:
                await query.edit_message_text(
                    "🤖 **AI Feature**\n\nThis feature is coming soon! Stay tuned for updates.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Back", callback_data="menu_ai")
                    ]])
                )
            
            # Unknown action
            else:
                await query.edit_message_text(
                    f"⚠️ **Unknown Action**\n\nThe action '{callback_data}' is not implemented yet.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
                    ]])
                )
                
        except Exception as e:
            logger.error(f"Button handler error: {e}")
            self.metrics.log_error(str(e))
            await query.edit_message_text(
                "❌ An error occurred. Please try again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
                ]])
            )

    async def show_help_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help via callback"""
        help_text = """
📚 **Command Reference**

🔧 **Core Commands**
/start - Initialize bot
/help - Show this help
/status - System status
/menu - Main menu

💡 **Quick Tips**
• Use buttons for easy navigation
• All modules are being actively developed
• More features coming soon!

🆘 **Need Help?**
Contact support or check documentation.
"""
        keyboard = [
            [
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
                InlineKeyboardButton("📊 Status", callback_data="show_status")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def show_status_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show status via callback"""
        status = await self.get_system_status()
        
        status_text = f"""
📊 **System Status Report**

⚡ **Performance**
• Success Rate: `{status['performance']['success_rate']}`
• Commands Handled: `{status['performance']['commands_handled']}`
• Uptime: `{status['system']['uptime']}`

📊 **Resources**
• CPU: `{status['resources']['cpu']}`
• Memory: `{status['resources']['memory']}`

🚀 All systems operational!
"""
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh_status"),
                InlineKeyboardButton("🏠 Menu", callback_data="main_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            status_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def show_module_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, module_name: str):
        """Show module-specific menu"""
        menus = {
            "finance": {
                "text": "💰 **Finance Management**\n\nTrack your financial activities:",
                "keyboard": [
                    [
                        InlineKeyboardButton("💸 Add Expense", callback_data="add_expense"),
                        InlineKeyboardButton("💰 Add Income", callback_data="add_income")
                    ],
                    [
                        InlineKeyboardButton("📊 Balance", callback_data="show_balance"),
                        InlineKeyboardButton("📈 Report", callback_data="finance_report")
                    ]
                ]
            },
            "business": {
                "text": "⚙️ **Business Operations**\n\nManage your business workflows:",
                "keyboard": [
                    [
                        InlineKeyboardButton("🏭 n8n Clients", callback_data="n8n_clients"),
                        InlineKeyboardButton("🐳 Docker", callback_data="docker_status")
                    ],
                    [
                        InlineKeyboardButton("🖥️ VPS Status", callback_data="vps_status"),
                        InlineKeyboardButton("📊 Metrics", callback_data="system_metrics")
                    ]
                ]
            },
            "monitoring": {
                "text": "📊 **System Monitoring**\n\nMonitor system health and performance:",
                "keyboard": [
                    [
                        InlineKeyboardButton("🚨 Alerts", callback_data="view_alerts"),
                        InlineKeyboardButton("📈 Metrics", callback_data="system_metrics")
                    ],
                    [
                        InlineKeyboardButton("❤️ Health", callback_data="health_check"),
                        InlineKeyboardButton("📋 Logs", callback_data="view_logs")
                    ]
                ]
            },
            "ai": {
                "text": "🤖 **AI Assistant**\n\nInteract with AI capabilities:",
                "keyboard": [
                    [
                        InlineKeyboardButton("💬 Ask Question", callback_data="ask_ai"),
                        InlineKeyboardButton("🧹 Clear Context", callback_data="clear_context")
                    ],
                    [
                        InlineKeyboardButton("🎤 Voice Mode", callback_data="voice_mode"),
                        InlineKeyboardButton("⚙️ Settings", callback_data="ai_settings")
                    ]
                ]
            }
        }
        
        menu = menus.get(module_name)
        if not menu:
            await update.callback_query.edit_message_text(
                "❌ Module not found",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
                ]])
            )
            return
        
        # Add back button
        keyboard = menu["keyboard"][:]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
        
        await update.callback_query.edit_message_text(
            menu["text"],
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        error = context.error
        logger.error(f"Update {update} caused error: {error}")
        self.metrics.log_error(str(error))
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ An error occurred. Please try again or use /start to restart."
                )
            except:
                pass

# Simple health check server
async def health_check(request):
    """Simple health check endpoint for Railway"""
    return web.Response(text='{"status":"healthy","service":"umbrasil-bot"}', 
                       content_type='application/json', 
                       status=200)

async def setup_health_server():
    """Setup health check server"""
    app = web.Application()
    app.router.add_get('/', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv('PORT', '8080'))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"Health check server running on port {port}")
    return runner

def main():
    """Main function to run the bot"""
    async def run_bot_with_health():
        """Run both health server and bot together"""
        try:
            # Start health check server first
            health_runner = await setup_health_server()
            
            # Create and run bot
            logger.info("🚀 Starting UmbraSIL Bot...")
            bot = UmbraSILBot()
            
            # Use the built-in run_polling which handles event loops properly
            await bot.application.initialize()
            await bot.application.start()
            await bot.application.updater.start_polling()
            
            logger.info("✅ Bot is running successfully!")
            
            # Keep running until interrupted
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("Bot stop requested")
            
        except Exception as e:
            logger.critical(f"Fatal error: {e}")
            raise
        finally:
            # Cleanup
            try:
                await bot.application.updater.stop()
                await bot.application.stop()
                await bot.application.shutdown()
                await health_runner.cleanup()
                logger.info("Cleanup completed")
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
    
    try:
        asyncio.run(run_bot_with_health())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
