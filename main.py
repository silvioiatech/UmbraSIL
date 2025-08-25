import os
import sys
import logging
import asyncio
import psutil
import platform
from aiohttp import web

# Add these to the Bot class initialization
async def health_check(self, request):
    """Handle health check requests"""
    try:
        # Verify critical services
        db_status = await self.db.check_connection()
        return web.Response(
            text="OK",
            status=200 if db_status else 503
        )
    except Exception:
        return web.Response(text="Service Unavailable", status=503)

async def setup_healthcheck(self):
    """Setup health check server"""
    app = web.Application()
    app.router.add_get('/', self.health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(
        runner, 
        host='0.0.0.0', 
        port=int(os.getenv('PORT', '8080'))
    )
    await site.start()
    logger.info(f"Health check server running on port {os.getenv('PORT', '8080')}")
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from decimal import Decimal
from dotenv import load_dotenv
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    BotCommand,
    Message
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from bot.core import (
    DatabaseManager,
    SecurityManager,
    require_auth,
    logger,
    BotError,
    DatabaseError,
    AuthenticationError
)
from bot.modules.finance import FinanceManager
from bot.modules.business import BusinessManager
from bot.modules.monitoring import MonitoringManager
from bot.modules.ai import AIManager, AIConfig

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
        self.last_error: Optional[str] = None
        self.active_users: Dict[int, datetime] = {}
        self.response_times: List[float] = []
    
    def log_command(self, response_time: float):
        """Log command execution"""
        self.command_count += 1
        self.response_times.append(response_time)
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]
    
    def log_error(self, error: str):
        """Log error occurrence"""
        self.error_count += 1
        self.last_error = error
    
    def log_user_activity(self, user_id: int):
        """Log user activity"""
        self.active_users[user_id] = datetime.now(timezone.utc)
    
    def get_average_response_time(self) -> float:
        """Get average response time"""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    def get_active_users_count(self) -> int:
        """Get count of active users in last 24h"""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        return sum(1 for time in self.active_users.values() if time > cutoff)
    
    def get_uptime(self) -> timedelta:
        """Get bot uptime"""
        return datetime.now(timezone.utc) - self.start_time
    
    def get_success_rate(self) -> float:
        """Get command success rate"""
        if self.command_count == 0:
            return 100.0
        return ((self.command_count - self.error_count) / self.command_count) * 100

class Bot:
    """Main bot class"""
    
    def __init__(self):
        """Initialize bot and its components"""
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("No token provided")
        
        # Initialize metrics
        self.metrics = BotMetrics()
        
        try:
            # Initialize core components
            self.db = DatabaseManager()
            self.security = SecurityManager()
            
            # Initialize modules
            self.finance = FinanceManager(self.db)
            self.business = BusinessManager(self.db)
            self.monitoring = MonitoringManager(self.db)
            self.ai = AIManager(self.db)
            
            # Create application
            self.application = Application.builder().token(self.token).build()
            
            logger.info("Bot initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
                async def get_system_status(self) -> Dict[str, Any]:
        """Get detailed system status"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            avg_response = self.metrics.get_average_response_time()
            uptime = self.metrics.get_uptime()
            success_rate = self.metrics.get_success_rate()
            
            return {
                "system": {
                    "platform": platform.platform(),
                    "python": platform.python_version(),
                    "uptime": str(uptime).split('.')[0],
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                },
                "resources": {
                    "cpu": f"{cpu_percent}%",
                    "memory": f"{memory.percent}%",
                    "disk": f"{disk.percent}%"
                },
                "performance": {
                    "avg_response": f"{avg_response:.2f}s",
                    "success_rate": f"{success_rate:.1f}%",
                    "commands_handled": self.metrics.command_count,
                    "active_users_24h": self.metrics.get_active_users_count()
                },
                "modules": {
                    "finance": self.finance.is_operational(),
                    "business": self.business.is_operational(),
                    "monitoring": self.monitoring.is_operational(),
                    "ai": self.ai.is_operational()
                },
                "database": await self.db.check_connection(),
                "last_error": self.metrics.last_error
            }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}

    @require_auth
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not update.message or not update.effective_user:
            return
            
        start_time = datetime.now()
        self.metrics.log_user_activity(update.effective_user.id)
        
        status = await self.get_system_status()
        
        status_text = f"""
🖥️ **System Status**

🕒 **System Info**
• Platform: `{status['system']['platform']}`
• Python: `{status['system']['python']}`
• Uptime: `{status['system']['uptime']}`
• Time: `{status['system']['timestamp']}`

📊 **Resources**
• CPU Usage: `{status['resources']['cpu']}`
• Memory Usage: `{status['resources']['memory']}`
• Disk Usage: `{status['resources']['disk']}`

⚡ **Performance**
• Avg Response: `{status['performance']['avg_response']}`
• Success Rate: `{status['performance']['success_rate']}`
• Commands: `{status['performance']['commands_handled']}`
• Active Users: `{status['performance']['active_users_24h']}`

📡 **Modules**
• Finance: {'✅' if status['modules']['finance'] else '❌'}
• Business: {'✅' if status['modules']['business'] else '❌'}
• Monitoring: {'✅' if status['modules']['monitoring'] else '❌'}
• AI Assistant: {'✅' if status['modules']['ai'] else '❌'}

🗄️ **Database**
• Status: {'✅ Connected' if status['database'] else '❌ Disconnected'}
"""
        if status.get('last_error'):
            status_text += f"\n⚠️ **Last Error**\n`{status['last_error']}`"
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh_status"),
                InlineKeyboardButton("📊 Details", callback_data="status_details")
            ],
            [
                InlineKeyboardButton("📝 Logs", callback_data="view_logs"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            status_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        end_time = datetime.now()
        self.metrics.log_command((end_time - start_time).total_seconds())

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        if not update.effective_user or not update.message:
            return
            
        user_id = update.effective_user.id
        first_name = update.effective_user.first_name
        
        start_time = datetime.now()
        self.metrics.log_user_activity(user_id)
        
        if not await self.security.authenticate_user(user_id):
            await update.message.reply_text(
                "🚫 Sorry, you are not authorized to use this bot."
            )
            return
                    welcome_msg = f"""
🤖 **Welcome {first_name}!**

I'm your personal assistant bot with advanced AI capabilities.

🔥 **Core Features**:

💰 **Finance Management**
• Track expenses & income
• OCR receipt processing
• Financial reporting
• Budget tracking

⚙️ **Business Operations**
• n8n workflow management
• VPS monitoring
• Docker container control
• Client management

📊 **System Monitoring**
• Real-time metrics
• Intelligent alerts
• Health reporting
• Log analysis

🧠 **AI Assistant**
• Natural language processing
• Voice message handling
• Context-aware responses
• Multi-model support (GPT-4 & Claude)

📈 **Business Intelligence**
• Predictive analytics
• Trend detection
• Automated reporting
• Data visualization

Use /help for commands
Use /status for system health
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
                InlineKeyboardButton("🤖 AI Assistant", callback_data="menu_ai"),
                InlineKeyboardButton("📈 Analytics", callback_data="menu_bi")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="show_settings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_msg,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        end_time = datetime.now()
        self.metrics.log_command((end_time - start_time).total_seconds())
    
    @require_auth
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        if not update.message or not update.effective_user:
            return
            
        start_time = datetime.now()
        self.metrics.log_user_activity(update.effective_user.id)
        
        help_text = """
📚 **Command Reference**

🔧 **Core Commands**
/start - Initialize bot
/help - Show this help
/status - System status
/menu - Main menu
/settings - Bot configuration

💰 **Finance Management**
/expense - Add expense
/income - Add income
/balance - Show balance
/report - Generate report
/budget - Budget status
/receipt - Process receipt

⚙️ **Business Operations**
/client - Manage n8n clients
/docker - Docker container status
/vps - VPS monitoring
/workflow - n8n workflow status
/backup - Manage backups

📊 **Monitoring**
/metrics - System metrics
/alerts - View active alerts
/health - Health check
/logs - System logs
/incidents - Incident reports

🧠 **AI Assistant**
/ask - Ask AI assistant
/voice - Voice message mode
/clear - Clear AI context
/mode - Switch AI model
/learn - Train on new data

📈 **Analytics**
/analyze - Data analysis
/forecast - Generate forecast
/trends - Show trends
/export - Export data
/visualize - Create charts

⚙️ **Settings**
/notify - Alert settings
/timezone - Set timezone
/language - Change language
/profile - User settings
/security - Security options

Need help? Just ask the AI assistant!
Use: /ask help with [topic]
"""
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh_help"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
            ],
            [
                InlineKeyboardButton("📚 Tutorial", callback_data="show_tutorial"),
                InlineKeyboardButton("❓ FAQ", callback_data="show_faq")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        end_time = datetime.now()
        self.metrics.log_command((end_time - start_time).total_seconds())
            async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        if not update.callback_query or not update.effective_user:
            return
            
        start_time = datetime.now()
        self.metrics.log_user_activity(update.effective_user.id)
        
        query = update.callback_query
        await query.answer()
        
        try:
            if query.data == "refresh_status":
                await self.status_command(update, context)
            elif query.data == "show_help":
                await self.help(update, context)
            elif query.data == "main_menu":
                await self.show_main_menu(update, context)
            elif query.data.startswith("menu_"):
                module = query.data.split("_")[1]
                await self.show_module_menu(update, context, module)
            elif query.data == "show_settings":
                await self.show_settings(update, context)
            elif query.data == "view_logs":
                await self.show_logs(update, context)
            elif query.data == "show_tutorial":
                await self.show_tutorial(update, context)
            elif query.data == "show_faq":
                await self.show_faq(update, context)
            
            end_time = datetime.now()
            self.metrics.log_command((end_time - start_time).total_seconds())
            
        except Exception as e:
            logger.error(f"Error in button handler: {e}")
            self.metrics.log_error(str(e))
            await query.message.reply_text(
                "⚠️ An error occurred processing your request. Please try again."
            )
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main menu"""
        if not update.callback_query:
            return
            
        keyboard = [
            [
                InlineKeyboardButton("💰 Finance", callback_data="menu_finance"),
                InlineKeyboardButton("⚙️ Business", callback_data="menu_business")
            ],
            [
                InlineKeyboardButton("📊 Monitoring", callback_data="menu_monitoring"),
                InlineKeyboardButton("🤖 AI", callback_data="menu_ai")
            ],
            [
                InlineKeyboardButton("📈 Analytics", callback_data="menu_bi"),
                InlineKeyboardButton("⚡ Quick Actions", callback_data="menu_quick")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="show_settings"),
                InlineKeyboardButton("❓ Help", callback_data="show_help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            "🏠 **Main Menu**\nSelect a module or action:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_module_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, module: str):
        """Show specific module menu"""
        if not update.callback_query:
            return
            
        menus = {
            "finance": self.finance.get_menu(),
            "business": self.business.get_menu(),
            "monitoring": self.monitoring.get_menu(),
            "ai": self.ai.get_menu(),
            "bi": self.business.get_analytics_menu(),
            "quick": self.get_quick_actions_menu()
        }
        
        menu = menus.get(module, {"text": "Menu not available", "keyboard": []})
        
        # Always add back button
        if menu["keyboard"]:
            menu["keyboard"].append([
                InlineKeyboardButton("🔙 Back", callback_data="main_menu")
            ])
        
        await update.callback_query.edit_message_text(
            text=menu["text"],
            reply_markup=InlineKeyboardMarkup(menu["keyboard"]),
            parse_mode='Markdown'
        )
    
    def get_quick_actions_menu(self) -> Dict[str, Any]:
        """Get quick actions menu"""
        return {
            "text": "⚡ **Quick Actions**\nFrequently used commands:",
            "keyboard": [
                [
                    InlineKeyboardButton("💰 Add Expense", callback_data="quick_expense"),
                    InlineKeyboardButton("📊 Status", callback_data="quick_status")
                ],
                [
                    InlineKeyboardButton("🤖 Ask AI", callback_data="quick_ai"),
                    InlineKeyboardButton("📈 Today's Report", callback_data="quick_report")
                ]
            ]
        }
    
    async def show_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show settings menu"""
        if not update.callback_query:
            return
            
        keyboard = [
            [
                InlineKeyboardButton("🔔 Notifications", callback_data="settings_notifications"),
                InlineKeyboardButton("🌍 Language", callback_data="settings_language")
            ],
            [
                InlineKeyboardButton("🕒 Timezone", callback_data="settings_timezone"),
                InlineKeyboardButton("🔐 Security", callback_data="settings_security")
            ],
            [
                InlineKeyboardButton("⚙️ AI Settings", callback_data="settings_ai"),
                InlineKeyboardButton("📊 Display", callback_data="settings_display")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="main_menu")
            ]
        ]
        
        await update.callback_query.edit_message_text(
            "⚙️ **Settings**\nConfigure bot preferences:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
            async def show_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent system logs"""
        if not update.callback_query:
            return
            
        try:
            # Get last 10 significant log entries
            logs = await self.monitoring.get_recent_logs(limit=10)
            
            log_text = "📋 **Recent System Logs**\n\n"
            for log in logs:
                log_text += f"• {log['timestamp']}: {log['message']}\n"
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="view_logs"),
                    InlineKeyboardButton("📥 Download", callback_data="download_logs")
                ],
                [
                    InlineKeyboardButton("🔙 Back", callback_data="show_status")
                ]
            ]
            
            await update.callback_query.edit_message_text(
                log_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error showing logs: {e}")
            self.metrics.log_error(str(e))
            await update.callback_query.edit_message_text(
                "⚠️ Error retrieving logs. Please try again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="show_status")
                ]])
            )
    
    async def show_tutorial(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show interactive tutorial"""
        if not update.callback_query:
            return
            
        tutorials = {
            "basic": "🔰 **Basic Usage**\nLearn core bot features...",
            "finance": "💰 **Finance Module**\nManage expenses and income...",
            "business": "⚙️ **Business Operations**\nHandle n8n and Docker...",
            "ai": "🤖 **AI Assistant**\nInteract with AI features..."
        }
        
        keyboard = [
            [
                InlineKeyboardButton("🔰 Basics", callback_data="tutorial_basic"),
                InlineKeyboardButton("💰 Finance", callback_data="tutorial_finance")
            ],
            [
                InlineKeyboardButton("⚙️ Business", callback_data="tutorial_business"),
                InlineKeyboardButton("🤖 AI", callback_data="tutorial_ai")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="show_help")
            ]
        ]
        
        await update.callback_query.edit_message_text(
            "📚 **Tutorial**\nSelect a topic to learn more:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def show_faq(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show frequently asked questions"""
        if not update.callback_query:
            return
            
        faq_text = """
❓ **Frequently Asked Questions**

**Q: How do I start using the bot?**
A: Use /start to begin and follow the interactive menu.

**Q: How does the AI assistant work?**
A: Use /ask followed by your question. The AI supports text and voice.

**Q: How secure is my data?**
A: All data is encrypted and stored securely. Only you can access it.

**Q: Can I export my data?**
A: Yes, use /export in any module to download your data.

**Q: How do I set up alerts?**
A: Use /settings → Notifications to configure alerts.
"""
        keyboard = [
            [
                InlineKeyboardButton("📚 Tutorial", callback_data="show_tutorial"),
                InlineKeyboardButton("🆘 Support", callback_data="show_support")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="show_help")
            ]
        ]
        
        await update.callback_query.edit_message_text(
            faq_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def setup_commands(self):
        """Setup bot commands for menu button"""
        commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show help message"),
            BotCommand("status", "Show system status"),
            BotCommand("menu", "Show main menu"),
            BotCommand("ask", "Ask AI assistant"),
            BotCommand("expense", "Add expense"),
            BotCommand("income", "Add income"),
            BotCommand("balance", "Show balance"),
            BotCommand("client", "Manage clients"),
            BotCommand("metrics", "Show metrics"),
            BotCommand("settings", "Bot settings")
        ]
        
        await self.application.bot.set_my_commands(commands)
        logger.info("Bot commands configured")
            async def handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors in updates"""
        try:
            if update and update.effective_user:
                user_id = update.effective_user.id
                self.metrics.log_user_activity(user_id)
            
            error = context.error
            logger.error(f"Update {update} caused error: {error}")
            self.metrics.log_error(str(error))
            
            # Handle specific errors
            if isinstance(error, AuthenticationError):
                await self._handle_auth_error(update, error)
            elif isinstance(error, DatabaseError):
                await self._handle_db_error(update, error)
            elif isinstance(error, BotError):
                await self._handle_bot_error(update, error)
            else:
                await self._handle_generic_error(update, error)
                
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
    
    async def _handle_auth_error(self, update: Update, error: AuthenticationError):
        """Handle authentication errors"""
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "🚫 Authentication failed. Please verify your access."
            )
    
    async def _handle_db_error(self, update: Update, error: DatabaseError):
        """Handle database errors"""
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Database operation failed. Your data is safe, please try again later."
            )
            
        # Attempt database recovery
        try:
            await self.db.verify_connection()
        except Exception as e:
            logger.error(f"Database recovery failed: {e}")
    
    async def _handle_bot_error(self, update: Update, error: BotError):
        """Handle bot-specific errors"""
        if update and update.effective_message:
            await update.effective_message.reply_text(
                f"⚠️ Operation failed: {str(error)}\nPlease try again or contact support."
            )
    
    async def _handle_generic_error(self, update: Update, error: Exception):
        """Handle unknown errors"""
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An unexpected error occurred. Our team has been notified."
            )
    
    async def setup(self):
        """Setup bot handlers and modules"""
        try:
            # Core handlers
            self.application.add_handler(CommandHandler("start", self.start))
            self.application.add_handler(CommandHandler("help", self.help))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(CommandHandler("menu", self.show_main_menu))
            self.application.add_handler(CallbackQueryHandler(self.button_handler))
            
            # Error handler
            self.application.add_error_handler(self.handle_error)
            
            # Setup module handlers
            await asyncio.gather(
                self.finance.setup_handlers(self.application),
                self.business.setup_handlers(self.application),
                self.monitoring.setup_handlers(self.application),
                self.ai.setup_handlers(self.application)
            )
            
            # Setup commands
            await self.setup_commands()
            
            # Initialize database
            await self.db.initialize()
            
            # Verify all connections
            await self._verify_connections()
            
            logger.info("Bot setup completed successfully")
        except Exception as e:
            logger.error(f"Error during bot setup: {e}")
            raise
    
    async def _verify_connections(self):
        """Verify all external connections"""
        try:
            # Check database
            if not await self.db.check_connection():
                raise DatabaseError("Database connection failed")
            
            # Check AI services
            if not await self.ai.check_services():
                logger.warning("AI services partially unavailable")
            
            # Check monitoring
            if not await self.monitoring.check_services():
                logger.warning("Monitoring services partially unavailable")
            
            logger.info("All connections verified")
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            raise
    
    async def run(self):
        """Run the bot"""
        try:
            logger.info("Starting bot...")
            
            # Setup
            await self.setup()
            
            # Initialize application
            await self.application.initialize()
            
            # Start application
            await self.application.start()
            
            # Run polling
            await self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
            logger.info("Bot is running")
        except Exception as e:
            logger.error(f"Critical error running bot: {e}")
            self.metrics.log_error(str(e))
            raise
        finally:
            # Ensure clean shutdown
            await self.application.stop()

if __name__ == "__main__":
    try:
        # Set higher recursion limit for async operations
        sys.setrecursionlimit(10000)
        
        # Create and run bot
        bot = Bot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)
