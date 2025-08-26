import os
import sys
import logging
import asyncio
import psutil
import platform
from aiohttp import web
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
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

# Bot Configuration
BOT_VERSION = "1.0.0"
BOT_CREATED_AT = "2025-08-26 00:19:28"
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

# Mock imports for modules that don't exist yet
class MockModule:
    def __init__(self, name):
        self.name = name
        
    def is_operational(self):
        return True
        
    async def setup_handlers(self, application):
        pass
        
    def get_menu(self):
        return {
            "text": f"{self.name} Module Menu",
            "keyboard": []
        }

class MockDatabaseManager:
    async def initialize(self):
        pass
        
    async def check_connection(self):
        return True

class MockSecurityManager:
    async def authenticate_user(self, user_id):
        allowed_users = [8286836821]  # Replace with your Telegram ID
        return user_id in allowed_users

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
        self.command_count += 1
        self.response_times.append(response_time)
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]
    
    def log_error(self, error: str):
        self.error_count += 1
        self.last_error = error
    
    def log_user_activity(self, user_id: int):
        self.active_users[user_id] = datetime.now(timezone.utc)
    
    def get_average_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    def get_active_users_count(self) -> int:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        return sum(1 for time in self.active_users.values() if time > cutoff)
    
    def get_uptime(self) -> timedelta:
        return datetime.now(timezone.utc) - self.start_time
    
    def get_success_rate(self) -> float:
        if self.command_count == 0:
            return 100.0
        return ((self.command_count - self.error_count) / self.command_count) * 100

class SimpleModule:
    """Simplified module implementation"""
    
    def __init__(self, name: str):
        self.name = name
        self.operational = True
        
    def is_operational(self) -> bool:
        return self.operational
        
    async def setup_handlers(self, application):
        logger.info(f"{self.name} module handlers setup completed")
        
    def get_menu(self) -> Dict[str, Any]:
        menus = {
            "Finance": {
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
            "Business": {
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
            "Monitoring": {
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
            "AI": {
                "text": "🤖 **AI Assistant**\n\nInteract with AI capabilities:",
                "keyboard": [
                    [
                        InlineKeyboardButton("💬 Ask Question", callback_data="ask_ai"),
                        InlineKeyboardButton("🧹 Clear Context", callback_data="clear_context")
                    ],
                    [
                        InlineKeyboardButton("🎤 Voice Mode", callback_data="voice_mode"),
                        InlineKeyboardButton("⚙️ AI Settings", callback_data="ai_settings")
                    ]
                ]
            }
        }
        return menus.get(self.name, {
            "text": f"{self.name} Module (Coming Soon)",
            "keyboard": []
        })

class SimpleAuth:
    """Simple authentication system"""
    
    def __init__(self):
        self.allowed_users = [8286836821]  # Replace with your actual Telegram user ID
    
    async def authenticate_user(self, user_id: int) -> bool:
        return user_id in self.allowed_users

class SimpleDatabase:
    """Simple database mock"""
    
    def __init__(self):
        self.connected = True
        
    async def initialize(self):
        logger.info("Database initialized")
        
    async def check_connection(self) -> bool:
        return self.connected

class Bot:
    """Main bot class with fixed implementation"""
    
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
        
        # Initialize components
        self.metrics = BotMetrics()
        self.auth = SimpleAuth()
        self.db = SimpleDatabase()
        
<<<<<<< HEAD
        # Initialize modules
        self.finance = SimpleModule("Finance")
        self.business = SimpleModule("Business")
        self.monitoring = SimpleModule("Monitoring")
        self.ai = SimpleModule("AI")
        
        # Create application
        self.application = Application.builder().token(self.token).build()
        
        logger.info("Bot initialized successfully")

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
=======
        try:
            # Initialize mock components (replace with real ones when available)
            self.db = MockDatabaseManager()
            self.security = MockSecurityManager()
            
            # Initialize mock modules
            self.finance = MockModule("Finance")
            self.business = MockModule("Business")
            self.monitoring = MockModule("Monitoring")
            self.ai = MockModule("AI")
            
            # Create application
            self.application = Application.builder().token(self.token).build()
            
            logger.info("Bot initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
>>>>>>> d1736fc03db2fa4b979ede13b27aa1a0b866ea25

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
                    "uptime": str(uptime).split('.')[0],
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                },
                "resources": {
                    "cpu": f"{cpu_percent}%",
                    "memory": f"{memory.percent}%",
                    "disk": f"{disk.percent}%"
                },
                "performance": {
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
                "database": await self.db.check_connection()
            }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}

<<<<<<< HEAD
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
=======
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not update.message or not update.effective_user:
            return
            
        start_time = datetime.now()
        self.metrics.log_user_activity(update.effective_user.id)
        
        status = await self.get_system_status()
        
        status_text = f"""
**System Status**

**System Info**
• Platform: `{status['system']['platform']}`
• Python: `{status['system']['python']}`
• Uptime: `{status['system']['uptime']}`
• Time: `{status['system']['timestamp']}`

**Resources**
• CPU Usage: `{status['resources']['cpu']}`
• Memory Usage: `{status['resources']['memory']}`
• Disk Usage: `{status['resources']['disk']}`

**Performance**
• Avg Response: `{status['performance']['avg_response']}`
• Success Rate: `{status['performance']['success_rate']}`
• Commands: `{status['performance']['commands_handled']}`
• Active Users: `{status['performance']['active_users_24h']}`

**Modules**
• Finance: {'✅' if status['modules']['finance'] else '❌'}
• Business: {'✅' if status['modules']['business'] else '❌'}
• Monitoring: {'✅' if status['modules']['monitoring'] else '❌'}
• AI Assistant: {'✅' if status['modules']['ai'] else '❌'}

**Database**
• Status: {'✅ Connected' if status['database'] else '❌ Disconnected'}
"""
        if status.get('last_error'):
            status_text += f"\n**Last Error**\n`{status['last_error']}`"
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh_status"),
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
>>>>>>> d1736fc03db2fa4b979ede13b27aa1a0b866ea25
        """Handle /start command"""
        start_time = datetime.now()
        user = update.effective_user
        self.metrics.log_user_activity(user.id)
        
<<<<<<< HEAD
        welcome_text = f"""
🤖 **Welcome {user.first_name}!**

I'm your personal assistant bot with comprehensive business management capabilities.

🔥 **Core Features**:
💰 **Finance Management** - Track expenses & income
⚙️ **Business Operations** - Manage workflows & systems  
📊 **System Monitoring** - Real-time health & alerts
🤖 **AI Assistant** - Natural language processing
📈 **Business Intelligence** - Analytics & reporting

Use the buttons below to get started or type /help for more commands.
=======
        if not await self.security.authenticate_user(user_id):
            await update.message.reply_text(
                "🚫 Sorry, you are not authorized to use this bot."
            )
            return

        welcome_msg = f"""
**Welcome {first_name}!**

I'm your personal assistant bot with advanced AI capabilities.

**Core Features**:
• Finance Management
• Business Operations  
• System Monitoring
• AI Assistant
• Business Intelligence

Use /help for commands or /status for system health
>>>>>>> d1736fc03db2fa4b979ede13b27aa1a0b866ea25
"""
        keyboard = [
            [
                InlineKeyboardButton("📚 Commands", callback_data="show_help"),
                InlineKeyboardButton("📊 Status", callback_data="show_status")
            ],
            [
                InlineKeyboardButton("💰 Finance", callback_data="menu_finance"),
                InlineKeyboardButton("⚙️ Business", callback_data="menu_business")
<<<<<<< HEAD
            ],
            [
                InlineKeyboardButton("📊 Monitoring", callback_data="menu_monitoring"),
                InlineKeyboardButton("🤖 AI Assistant", callback_data="menu_ai")
=======
>>>>>>> d1736fc03db2fa4b979ede13b27aa1a0b866ea25
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
<<<<<<< HEAD
        self.metrics.log_command((datetime.now() - start_time).total_seconds())

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
=======
        end_time = datetime.now()
        self.metrics.log_command((end_time - start_time).total_seconds())
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
>>>>>>> d1736fc03db2fa4b979ede13b27aa1a0b866ea25
        """Handle /help command"""
        help_text = """
**Command Reference**

**Core Commands**
/start - Initialize bot
/help - Show this help
/status - System status
/menu - Main menu

<<<<<<< HEAD
💰 **Finance Commands** (Coming Soon)
/expense - Add expense
/income - Add income
/balance - Show balance

⚙️ **Business Commands** (Coming Soon)
/clients - Manage n8n clients
/docker - Docker status
/vps - VPS monitoring

📊 **Monitoring Commands** (Coming Soon)
/alerts - View alerts
/metrics - System metrics
/health - Health check

🤖 **AI Commands** (Coming Soon)
/ask - Ask AI assistant
/clear - Clear context

Use the interactive menu for easier navigation!
"""
        keyboard = [
            [
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
                InlineKeyboardButton("📊 Status", callback_data="show_status")
=======
**Features**
• Finance Management
• Business Operations
• System Monitoring
• AI Assistant

More features coming soon!
"""
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh_help"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
>>>>>>> d1736fc03db2fa4b979ede13b27aa1a0b866ea25
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
        
<<<<<<< HEAD
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
• Active Users: `{status['performance']['active_users_24h']}`

📦 **Modules**
• Finance: {'✅' if status['modules']['finance'] else '❌'}
• Business: {'✅' if status['modules']['business'] else '❌'}
• Monitoring: {'✅' if status['modules']['monitoring'] else '❌'}
• AI: {'✅' if status['modules']['ai'] else '❌'}

🗄️ **Database**: {'✅ Connected' if status['database'] else '❌ Disconnected'}
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
=======
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
            
>>>>>>> d1736fc03db2fa4b979ede13b27aa1a0b866ea25
        keyboard = [
            [
                InlineKeyboardButton("💰 Finance", callback_data="menu_finance"),
                InlineKeyboardButton("⚙️ Business", callback_data="menu_business")
            ],
            [
<<<<<<< HEAD
                InlineKeyboardButton("📊 Monitoring", callback_data="menu_monitoring"),
                InlineKeyboardButton("🤖 AI Assistant", callback_data="menu_ai")
            ],
            [
                InlineKeyboardButton("📊 Status", callback_data="show_status"),
=======
                InlineKeyboardButton("📊 Status", callback_data="refresh_status"),
>>>>>>> d1736fc03db2fa4b979ede13b27aa1a0b866ea25
                InlineKeyboardButton("❓ Help", callback_data="show_help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
<<<<<<< HEAD
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
            
            # Feature actions (coming soon responses)
            elif callback_data in ["add_expense", "add_income", "show_balance", "finance_report"]:
                await query.edit_message_text(
                    "💰 **Finance Feature**\n\nThis feature is coming soon! Stay tuned for updates.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Back", callback_data="menu_finance")
                    ]])
                )
            
            elif callback_data in ["n8n_clients", "docker_status", "vps_status", "system_metrics"]:
                await query.edit_message_text(
                    "⚙️ **Business Feature**\n\nThis feature is coming soon! Stay tuned for updates.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Back", callback_data="menu_business")
                    ]])
                )
            
            elif callback_data in ["view_alerts", "health_check", "view_logs"]:
                await query.edit_message_text(
                    "📊 **Monitoring Feature**\n\nThis feature is coming soon! Stay tuned for updates.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Back", callback_data="menu_monitoring")
                    ]])
                )
            
            elif callback_data in ["ask_ai", "clear_context", "voice_mode", "ai_settings"]:
                await query.edit_message_text(
                    "🤖 **AI Feature**\n\nThis feature is coming soon! Stay tuned for updates.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Back", callback_data="menu_ai")
                    ]])
                )
            
            else:
                await query.edit_message_text(
                    f"⚠️ **Unknown Action**\n\nThe action '{callback_data}' is not implemented yet.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
                    ]])
                )
=======
        await update.callback_query.edit_message_text(
            "🏠 **Main Menu**\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def setup_commands(self):
        """Setup bot commands for menu button"""
        commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show help message"),
            BotCommand("status", "Show system status"),
            BotCommand("menu", "Show main menu")
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
>>>>>>> d1736fc03db2fa4b979ede13b27aa1a0b866ea25
            
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ An error occurred. Please try again."
                )
                
        except Exception as e:
<<<<<<< HEAD
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

📦 **Modules**
• Finance: {'✅' if status['modules']['finance'] else '❌'}
• Business: {'✅' if status['modules']['business'] else '❌'}
• Monitoring: {'✅' if status['modules']['monitoring'] else '❌'}
• AI: {'✅' if status['modules']['ai'] else '❌'}

📊 **Resources**
• CPU: `{status['resources']['cpu']}`
• Memory: `{status['resources']['memory']}`
• Database: {'✅' if status['database'] else '❌'}

All systems operational!
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
        modules = {
            "finance": self.finance,
            "business": self.business,
            "monitoring": self.monitoring,
            "ai": self.ai
        }
        
        module = modules.get(module_name)
        if not module:
            await update.callback_query.edit_message_text(
                "❌ Module not found",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
                ]])
            )
            return
        
        menu = module.get_menu()
        
        # Add back button
        keyboard = menu.get("keyboard", [])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
        
        await update.callback_query.edit_message_text(
            menu.get("text", f"{module_name.title()} Module"),
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

=======
            logger.error(f"Error in error handler: {e}")

>>>>>>> d1736fc03db2fa4b979ede13b27aa1a0b866ea25
    async def health_check(self, request):
        """Health check endpoint"""
        try:
            status_data = {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                "version": BOT_VERSION,
                "uptime": str(self.metrics.get_uptime()),
                "services": {
                    "database": await self.db.check_connection(),
                    "bot": True
                }
            }
            
<<<<<<< HEAD
=======
            is_healthy = all([
                status_data["services"]["database"],
                status_data["services"]["monitoring"]
            ])
            
>>>>>>> d1736fc03db2fa4b979ede13b27aa1a0b866ea25
            return web.Response(
                text=json.dumps(status_data),
                content_type='application/json',
                status=200
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return web.Response(
                text=json.dumps({
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                }),
                content_type='application/json',
                status=503
            )

    async def setup_healthcheck(self):
        """Setup health check server"""
        try:
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
        except Exception as e:
            logger.error(f"Failed to setup health check: {e}")
            raise
<<<<<<< HEAD

    async def setup_commands(self):
        """Setup bot commands for menu button"""
        commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show help message"),
            BotCommand("status", "Show system status"),
            BotCommand("menu", "Show main menu")
        ]
        
        await self.application.bot.set_my_commands(commands)
        logger.info("Bot commands configured")

    async def setup(self):
        """Setup bot handlers and modules"""
        try:
            # Core handlers with auth
            self.application.add_handler(CommandHandler("start", self.require_auth(self.start_command)))
            self.application.add_handler(CommandHandler("help", self.require_auth(self.help_command)))
            self.application.add_handler(CommandHandler("status", self.require_auth(self.status_command)))
            self.application.add_handler(CommandHandler("menu", self.require_auth(self.main_menu_command)))
            self.application.add_handler(CallbackQueryHandler(self.require_auth(self.button_handler)))
=======
    
    async def setup(self):
        """Setup bot handlers and modules"""
        try:
            # Core handlers
            self.application.add_handler(CommandHandler("start", self.start))
            self.application.add_handler(CommandHandler("help", self.help))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(CallbackQueryHandler(self.button_handler))
>>>>>>> d1736fc03db2fa4b979ede13b27aa1a0b866ea25
            
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
            
            logger.info("Bot setup completed successfully")
        except Exception as e:
            logger.error(f"Error during bot setup: {e}")
            raise
<<<<<<< HEAD

=======
    
>>>>>>> d1736fc03db2fa4b979ede13b27aa1a0b866ea25
    async def run(self):
        """Run the bot"""
        try:
            logger.info("Starting bot...")
            
            # Setup health check first
            await self.setup_healthcheck()
            
            # Setup bot
            await self.setup()
            
            # Initialize application
            await self.application.initialize()
            
            # Start application
            await self.application.start()
            
<<<<<<< HEAD
            # Run polling
            await self.application.run_polling(
=======
            # Start updater (this runs indefinitely)
            await self.application.updater.start_polling(
>>>>>>> d1736fc03db2fa4b979ede13b27aa1a0b866ea25
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
            logger.info("Bot is running")
            
<<<<<<< HEAD
=======
            # Keep the bot running
            await asyncio.Event().wait()
            
>>>>>>> d1736fc03db2fa4b979ede13b27aa1a0b866ea25
        except Exception as e:
            logger.error(f"Critical error running bot: {e}")
            self.metrics.log_error(str(e))
            raise
        finally:
            # Ensure clean shutdown
            try:
<<<<<<< HEAD
=======
                await self.application.updater.stop()
>>>>>>> d1736fc03db2fa4b979ede13b27aa1a0b866ea25
                await self.application.stop()
                await self.application.shutdown()
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")

async def main():
    """Main function to run the bot"""
    try:
        # Set higher recursion limit for async operations
        sys.setrecursionlimit(10000)
        
        # Create and run bot
        bot = Bot()
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
