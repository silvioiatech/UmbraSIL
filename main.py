#!/usr/bin/env python3
"""
UmbraSIL Bot - Full Featured Version
All modules integrated and ready for Railway deployment
"""

import os
import sys
import logging
import psutil
import platform
import asyncio
import base64
import io
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Core Telegram imports
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Import NLP Manager
try:
    from nlp_manager import NLPManager
    NLP_AVAILABLE = True
except ImportError:
    NLPManager = None
    NLP_AVAILABLE = False
    logging.warning("NLP Manager not available - Natural language understanding limited")

# Optional imports with graceful fallbacks
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    paramiko = None
    PARAMIKO_AVAILABLE = False
    logging.warning("Paramiko not available - VPS management disabled")

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    AsyncOpenAI = None
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI not available - AI features limited")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic = None
    ANTHROPIC_AVAILABLE = False
    logging.warning("Anthropic not available - AI features limited")

try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    DOCKER_AVAILABLE = False
    logging.warning("Docker not available - Business module limited")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False
    logging.warning("Requests not available - External APIs limited")

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())
)
logger = logging.getLogger(__name__)

# Bot Configuration
BOT_VERSION = "1.2.0"
BOT_NAME = "UmbraSIL"

# Feature flags from environment
ENABLE_FINANCE = os.getenv("ENABLE_FINANCE", "true").lower() == "true"
ENABLE_BUSINESS = os.getenv("ENABLE_BUSINESS", "true").lower() == "true"
ENABLE_MONITORING = os.getenv("ENABLE_MONITORING", "true").lower() == "true"
ENABLE_AI = os.getenv("ENABLE_AI", "true").lower() == "true"
ENABLE_BI = os.getenv("ENABLE_BI", "true").lower() == "true"

class BotMetrics:
    """Track bot performance metrics"""
    
    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.command_count = 0
        self.error_count = 0
        self.active_users: Dict[int, datetime] = {}
        self.module_stats = {
            "finance": {"commands": 0, "errors": 0},
            "business": {"commands": 0, "errors": 0},
            "ai": {"commands": 0, "errors": 0},
            "monitoring": {"commands": 0, "errors": 0}
        }
    
    def log_command(self, response_time: float, module: str = "core"):
        self.command_count += 1
        if module in self.module_stats:
            self.module_stats[module]["commands"] += 1
    
    def log_error(self, error: str, module: str = "core"):
        self.error_count += 1
        if module in self.module_stats:
            self.module_stats[module]["errors"] += 1
        logger.error(f"Bot error in {module}: {error}")
    
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
        allowed_ids = os.getenv("ALLOWED_USER_IDS", "8286836821")
        self.allowed_users = [int(x.strip()) for x in allowed_ids.split(",") if x.strip()]
    
    async def authenticate_user(self, user_id: int) -> bool:
        return user_id in self.allowed_users

class AIManager:
    """AI Assistant Manager"""
    
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self.context_storage = {}
        
        if ENABLE_AI and OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        if ENABLE_AI and ANTHROPIC_AVAILABLE and os.getenv("CLAUDE_API_KEY"):
            self.anthropic_client = anthropic.AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY"))
    
    def is_operational(self) -> bool:
        return ENABLE_AI and (self.openai_client is not None or self.anthropic_client is not None)
    
    async def get_ai_response(self, user_id: int, message: str) -> str:
        """Get AI response from available providers"""
        if not self.is_operational():
            return "🤖 AI services are not configured. Please add your API keys to enable AI features."
        
        try:
            if self.openai_client:
                response = await self.openai_client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
                    messages=[
                        {"role": "system", "content": "You are UmbraSIL, a helpful assistant integrated into a Telegram bot. Be concise and helpful."},
                        {"role": "user", "content": message}
                    ],
                    max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "2000")),
                    temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
                )
                return response.choices[0].message.content
            
            elif self.anthropic_client:
                response = await self.anthropic_client.messages.create(
                    model=os.getenv("CLAUDE_MODEL", "claude-3-sonnet-20240229"),
                    max_tokens=2000,
                    messages=[{"role": "user", "content": message}]
                )
                return response.content[0].text
            
        except Exception as e:
            logger.error(f"AI response error: {e}")
            return f"🤖 AI service temporarily unavailable: {str(e)[:100]}"
        
        return "🤖 No AI providers configured."

class FinanceManager:
    """Finance Management Module"""
    
    def __init__(self):
        self.transactions = []
        self.balance = 0.0
        self.currency = os.getenv("DEFAULT_CURRENCY", "EUR")
    
    def is_operational(self) -> bool:
        return ENABLE_FINANCE
    
    async def add_expense(self, amount: float, category: str, description: str = "") -> bool:
        """Add an expense transaction"""
        try:
            transaction = {
                "type": "expense",
                "amount": amount,
                "category": category,
                "description": description,
                "timestamp": datetime.now(timezone.utc),
                "currency": self.currency
            }
            self.transactions.append(transaction)
            self.balance -= amount
            return True
        except Exception as e:
            logger.error(f"Add expense error: {e}")
            return False
    
    async def add_income(self, amount: float, source: str, description: str = "") -> bool:
        """Add an income transaction"""
        try:
            transaction = {
                "type": "income",
                "amount": amount,
                "source": source,
                "description": description,
                "timestamp": datetime.now(timezone.utc),
                "currency": self.currency
            }
            self.transactions.append(transaction)
            self.balance += amount
            return True
        except Exception as e:
            logger.error(f"Add income error: {e}")
            return False
    
    async def get_balance(self) -> Dict[str, Any]:
        """Get current balance and summary"""
        today = datetime.now(timezone.utc).date()
        today_transactions = [t for t in self.transactions if t["timestamp"].date() == today]
        
        today_income = sum(t["amount"] for t in today_transactions if t["type"] == "income")
        today_expenses = sum(t["amount"] for t in today_transactions if t["type"] == "expense")
        
        return {
            "balance": self.balance,
            "currency": self.currency,
            "today_income": today_income,
            "today_expenses": today_expenses,
            "total_transactions": len(self.transactions)
        }

class BusinessManager:
    """Business Operations Manager"""
    
    def __init__(self):
        self.docker_client = None
        if ENABLE_BUSINESS and DOCKER_AVAILABLE:
            try:
                self.docker_client = docker.from_env()
            except Exception as e:
                logger.error(f"Docker client initialization error: {e}")
        
        self.vps_config = {
            "host": os.getenv("VPS_HOST"),
            "port": int(os.getenv("VPS_PORT", "22")),
            "username": os.getenv("VPS_USERNAME"),
            "password": os.getenv("VPS_PASSWORD")
        }
    
    def is_operational(self) -> bool:
        return ENABLE_BUSINESS
    
    async def get_docker_status(self) -> Dict[str, Any]:
        """Get Docker container status"""
        if not self.docker_client:
            return {"error": "Docker not available"}
        
        try:
            containers = self.docker_client.containers.list(all=True)
            return {
                "total_containers": len(containers),
                "running": len([c for c in containers if c.status == "running"]),
                "stopped": len([c for c in containers if c.status == "exited"]),
                "containers": [{"name": c.name, "status": c.status} for c in containers[:5]]
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def get_vps_status(self) -> Dict[str, Any]:
        """Get VPS status via SSH"""
        if not PARAMIKO_AVAILABLE or not self.vps_config["host"]:
            return {"error": "VPS connection not configured"}
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=self.vps_config["host"],
                port=self.vps_config["port"],
                username=self.vps_config["username"],
                password=self.vps_config["password"],
                timeout=10
            )
            
            stdin, stdout, stderr = ssh.exec_command("uptime && df -h / && free -m")
            result = stdout.read().decode()
            ssh.close()
            
            return {"status": "connected", "info": result[:500]}
        except Exception as e:
            return {"error": str(e)}

class MonitoringManager:
    """System Monitoring Manager"""
    
    def __init__(self):
        self.alerts = []
        self.thresholds = {
            "cpu": int(os.getenv("CPU_THRESHOLD", "80")),
            "memory": int(os.getenv("MEMORY_THRESHOLD", "80")),
            "disk": int(os.getenv("DISK_THRESHOLD", "85"))
        }
    
    def is_operational(self) -> bool:
        return ENABLE_MONITORING
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Comprehensive system health check"""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Check thresholds
            alerts = []
            if cpu_percent > self.thresholds["cpu"]:
                alerts.append(f"High CPU usage: {cpu_percent}%")
            if memory.percent > self.thresholds["memory"]:
                alerts.append(f"High memory usage: {memory.percent}%")
            if disk.percent > self.thresholds["disk"]:
                alerts.append(f"High disk usage: {disk.percent}%")
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "alerts": alerts,
                "status": "healthy" if not alerts else "warning"
            }
        except Exception as e:
            return {"error": str(e), "status": "error"}

class UmbraSILBot:
    """Main bot class - fully featured with all modules integrated"""
    
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
        
        # Initialize core components
        self.metrics = BotMetrics()
        self.auth = SimpleAuth()
        
        # Initialize NLP Manager for natural language understanding
        self.nlp_manager = None
        if NLP_AVAILABLE:
            self.nlp_manager = NLPManager()
            if self.nlp_manager.is_operational():
                logger.info("✅ NLP Manager initialized with OpenRouter")
            else:
                logger.info("⚠️ NLP Manager initialized but no API key set")
        
        # Initialize module managers
        self.ai_manager = AIManager()
        self.finance_manager = FinanceManager()
        self.business_manager = BusinessManager()
        self.monitoring_manager = MonitoringManager()
        
        # Create application
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()
        
        logger.info("🚀 UmbraSIL Bot initialized successfully with all modules")
        logger.info(f"📊 Active modules: Finance={ENABLE_FINANCE}, Business={ENABLE_BUSINESS}, AI={ENABLE_AI}, Monitoring={ENABLE_MONITORING}")
    
    def setup_handlers(self):
        """Setup bot handlers with authentication"""
        
        # Core handlers
        self.application.add_handler(
            CommandHandler("start", self.require_auth(self.start_command))
        )
        self.application.add_handler(
            CommandHandler("help", self.require_auth(self.help_command))
        )
        self.application.add_handler(
            CommandHandler("status", self.require_auth(self.status_command))
        )
        self.application.add_handler(
            CommandHandler("menu", self.require_auth(self.main_menu_command))
        )
        
        # Module-specific commands
        if ENABLE_AI:
            self.application.add_handler(
                CommandHandler("ai", self.require_auth(self.ai_command))
            )
        
        if ENABLE_FINANCE:
            self.application.add_handler(
                CommandHandler("finance", self.require_auth(self.finance_command))
            )
        
        if ENABLE_BUSINESS:
            self.application.add_handler(
                CommandHandler("business", self.require_auth(self.business_command))
            )
        
        # Button handler
        self.application.add_handler(
            CallbackQueryHandler(self.require_auth(self.button_handler))
        )
        
        # Text message handler
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.require_auth(self.handle_text_message)
            )
        )
        
        # Photo handler for receipts
        self.application.add_handler(
            MessageHandler(
                filters.PHOTO,
                self.require_auth(self.handle_photo_message)
            )
        )
        
        # Error handler
        self.application.add_error_handler(self.handle_error)
        
        logger.info("✅ All handlers setup completed")
    
    def require_auth(self, func):
        """Authentication decorator"""
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not update.effective_user:
                return
                
            user_id = update.effective_user.id
            if not await self.auth.authenticate_user(user_id):
                message = "🚫 Access denied. You are not authorized to use this bot."
                if update.message:
                    await update.message.reply_text(message)
                elif update.callback_query:
                    await update.callback_query.answer(message, show_alert=True)
                return
                
            return await func(update, context)
        return wrapper
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        self.metrics.log_user_activity(user.id)
        
        # Build feature list dynamically
        features = ["• System monitoring", "• Interactive menus", "• Help and status information"]
        
        if ENABLE_AI and self.ai_manager.is_operational():
            features.append("• 🤖 AI Assistant (OpenAI/Claude)")
        
        if ENABLE_FINANCE and self.finance_manager.is_operational():
            features.append("• 💰 Finance Management")
        
        if ENABLE_BUSINESS and self.business_manager.is_operational():
            features.append("• ⚙️ Business Operations")
        
        if ENABLE_MONITORING and self.monitoring_manager.is_operational():
            features.append("• 📊 Advanced Monitoring")
        
        welcome_text = f"""
🤖 **Welcome {user.first_name}! I'm UmbraSIL v{BOT_VERSION}**

Your intelligent bot assistant is ready with full features!

🚀 **Available Features:**
{chr(10).join(features)}

💬 **Get Started:**
Use the buttons below or type /help for detailed information.
"""
        
        keyboard = [
            [
                InlineKeyboardButton("📊 System Status", callback_data="system_status"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
            ]
        ]
        
        # Add module shortcuts if enabled
        module_buttons = []
        if ENABLE_AI and self.ai_manager.is_operational():
            module_buttons.append(InlineKeyboardButton("🤖 AI Chat", callback_data="ai_menu"))
        
        if ENABLE_FINANCE and self.finance_manager.is_operational():
            module_buttons.append(InlineKeyboardButton("💰 Finance", callback_data="finance_menu"))
        
        if module_buttons:
            keyboard.append(module_buttons[:2])  # Max 2 buttons per row
        
        keyboard.append([InlineKeyboardButton("❓ Help", callback_data="show_help")])
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        self.metrics.log_command(1.0)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        
        # Build help text dynamically based on enabled modules
        help_text = f"""
📚 **UmbraSIL v{BOT_VERSION} Help**

**🔧 Basic Commands:**
• /start - Start the bot and see welcome
• /help - Show this help
• /status - System status and metrics
• /menu - Main navigation menu

**🎯 Module Commands:**"""

        if ENABLE_AI and self.ai_manager.is_operational():
            help_text += "\n• /ai - Access AI Assistant"
        
        if ENABLE_FINANCE and self.finance_manager.is_operational():
            help_text += "\n• /finance - Finance management"
        
        if ENABLE_BUSINESS and self.business_manager.is_operational():
            help_text += "\n• /business - Business operations"

        help_text += f"""

**🚀 Key Features:**
• 📊 **System Monitoring** - Real-time resource tracking
• 🔧 **Interactive Menus** - Easy button navigation
• 🛡️ **Secure Access** - User authentication"""

        if ENABLE_AI and self.ai_manager.is_operational():
            help_text += "\n• 🤖 **AI Assistant** - OpenAI/Claude integration"
        
        if ENABLE_FINANCE and self.finance_manager.is_operational():
            help_text += "\n• 💰 **Finance Manager** - Track income & expenses"
        
        if ENABLE_BUSINESS and self.business_manager.is_operational():
            help_text += "\n• ⚙️ **Business Ops** - Docker & VPS management"

        help_text += """

**💬 Text Interactions:**
• Type naturally for basic responses
• Use 'ai: your question' for AI chat
• Use 'expense: amount category desc' to log expenses
• Use 'income: amount source desc' to log income

**🎮 Getting Started:**
1. Use /start to see all available features
2. Navigate with buttons or commands
3. Try 'ai: hello' if AI is enabled
4. Use /menu anytime for main navigation

**Ready for Railway deployment! 🚀**
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
                InlineKeyboardButton("📊 Status", callback_data="system_status")
            ]
        ]
        
        await update.message.reply_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        await self.show_system_status(update, context)
    
    async def main_menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /menu command"""
        menu_text = f"🏠 **Main Menu** - UmbraSIL v{BOT_VERSION}\n\nChoose an option:"
        
        keyboard = [
            [
                InlineKeyboardButton("📊 System Status", callback_data="system_status"),
                InlineKeyboardButton("ℹ️ Bot Info", callback_data="bot_info")
            ]
        ]
        
        # Add module menus if enabled
        module_row1 = []
        module_row2 = []
        
        if ENABLE_AI and self.ai_manager.is_operational():
            module_row1.append(InlineKeyboardButton("🤖 AI Assistant", callback_data="ai_menu"))
        
        if ENABLE_FINANCE and self.finance_manager.is_operational():
            module_row1.append(InlineKeyboardButton("💰 Finance", callback_data="finance_menu"))
        
        if ENABLE_BUSINESS and self.business_manager.is_operational():
            module_row2.append(InlineKeyboardButton("⚙️ Business", callback_data="business_menu"))
        
        if ENABLE_MONITORING and self.monitoring_manager.is_operational():
            module_row2.append(InlineKeyboardButton("📈 Monitoring", callback_data="monitoring_menu"))
        
        if module_row1:
            keyboard.append(module_row1)
        if module_row2:
            keyboard.append(module_row2)
        
        keyboard.extend([
            [
                InlineKeyboardButton("❓ Help", callback_data="show_help"),
                InlineKeyboardButton("🔄 Refresh", callback_data="main_menu")
            ]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(menu_text, parse_mode='Markdown', reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(menu_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def ai_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ai command"""
        if not ENABLE_AI or not self.ai_manager.is_operational():
            await update.message.reply_text("🤖 AI module is not enabled or configured.")
            return
        
        await self.show_ai_menu(update, context)
    
    async def finance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /finance command"""
        if not ENABLE_FINANCE or not self.finance_manager.is_operational():
            await update.message.reply_text("💰 Finance module is not enabled.")
            return
        
        await self.show_finance_menu(update, context)
    
    async def business_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /business command"""
        if not ENABLE_BUSINESS or not self.business_manager.is_operational():
            await update.message.reply_text("⚙️ Business module is not enabled.")
            return
        
        await self.show_business_menu(update, context)
    
    async def show_ai_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show AI Assistant menu"""
        if not self.ai_manager.is_operational():
            text = "🤖 **AI Assistant**\n\nAI services are not configured. Please add your API keys."
            keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
        else:
            text = f"""
🤖 **AI Assistant**

Available AI providers:
• OpenAI: {'✅' if self.ai_manager.openai_client else '❌'}
• Claude: {'✅' if self.ai_manager.anthropic_client else '❌'}

Choose an action:
"""
            keyboard = [
                [
                    InlineKeyboardButton("💬 Ask Question", callback_data="ai_ask"),
                    InlineKeyboardButton("🧹 Clear Context", callback_data="ai_clear")
                ],
                [
                    InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
                ]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def show_finance_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show Finance menu"""
        balance_info = await self.finance_manager.get_balance()
        
        text = f"""
💰 **Finance Management**

💳 **Current Balance**: {balance_info['balance']:.2f} {balance_info['currency']}

📊 **Today's Activity**:
• Income: +{balance_info['today_income']:.2f} {balance_info['currency']}
• Expenses: -{balance_info['today_expenses']:.2f} {balance_info['currency']}

📈 **Total Transactions**: {balance_info['total_transactions']}

Choose an action:
"""
        
        keyboard = [
            [
                InlineKeyboardButton("💸 Add Expense", callback_data="finance_expense"),
                InlineKeyboardButton("💰 Add Income", callback_data="finance_income")
            ],
            [
                InlineKeyboardButton("📊 View Balance", callback_data="finance_balance"),
                InlineKeyboardButton("📈 Generate Report", callback_data="finance_report")
            ],
            [
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def show_business_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show Business Operations menu"""
        docker_status = await self.business_manager.get_docker_status()
        vps_status = await self.business_manager.get_vps_status()
        
        text = f"""
⚙️ **Business Operations**

🐳 **Docker Status**:
{f"• {docker_status.get('running', 0)} running, {docker_status.get('stopped', 0)} stopped" if 'error' not in docker_status else f"• Error: {docker_status['error'][:50]}"}

🖥️ **VPS Status**:
{f"• Connected: {vps_status['status']}" if 'error' not in vps_status else f"• Error: {vps_status['error'][:50]}"}

Choose an action:
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🐳 Docker Status", callback_data="business_docker"),
                InlineKeyboardButton("🖥️ VPS Status", callback_data="business_vps")
            ],
            [
                InlineKeyboardButton("📊 System Metrics", callback_data="business_metrics"),
                InlineKeyboardButton("🔧 Services", callback_data="business_services")
            ],
            [
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def show_monitoring_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show Monitoring menu"""
        health = await self.monitoring_manager.check_system_health()
        
        status_emoji = "✅" if health.get("status") == "healthy" else "⚠️" if health.get("status") == "warning" else "❌"
        
        text = f"""
📊 **System Monitoring**

{status_emoji} **System Status**: {health.get('status', 'unknown').title()}

📈 **Current Metrics**:
• CPU: {health.get('cpu_percent', 0):.1f}%
• Memory: {health.get('memory_percent', 0):.1f}%
• Disk: {health.get('disk_percent', 0):.1f}%

🚨 **Active Alerts**: {len(health.get('alerts', []))}

Choose an action:
"""
        
        keyboard = [
            [
                InlineKeyboardButton("📈 System Metrics", callback_data="monitoring_metrics"),
                InlineKeyboardButton("🚨 View Alerts", callback_data="monitoring_alerts")
            ],
            [
                InlineKeyboardButton("❤️ Health Check", callback_data="monitoring_health"),
                InlineKeyboardButton("📋 System Logs", callback_data="monitoring_logs")
            ],
            [
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages with NLP understanding"""
        if not update.message or not update.message.text:
            return
        
        user_text = update.message.text.strip()
        user_text_lower = user_text.lower()
        
        # Try NLP processing first if available and finance is enabled
        if self.nlp_manager and self.nlp_manager.is_operational() and ENABLE_FINANCE:
            # Get user context
            user_context = {
                "currency": self.finance_manager.currency,
                "user_id": update.effective_user.id
            }
            
            # Process message with NLP
            nlp_result = await self.nlp_manager.process_message(user_text, user_context)
            
            # Handle based on intent
            if nlp_result.get('confidence', 0) > 0.7:
                intent = nlp_result.get('intent')
                entities = nlp_result.get('entities', {})
                
                if intent == 'expense' and entities.get('amount'):
                    # Add expense automatically
                    amount = entities['amount']
                    category = entities.get('category', 'other')
                    vendor = entities.get('vendor', '')
                    description = entities.get('description', f'{vendor} purchase' if vendor else 'Expense')
                    
                    success = await self.finance_manager.add_expense(amount, category, description)
                    if success:
                        response_text = f"💸 **Expense Added Automatically**\n\n"
                        response_text += f"• Amount: {amount:.2f} {self.finance_manager.currency}\n"
                        response_text += f"• Category: {category}\n"
                        if vendor:
                            response_text += f"• Vendor: {vendor}\n"
                        response_text += f"• Description: {description}\n\n"
                        response_text += f"💳 New balance: {self.finance_manager.balance:.2f} {self.finance_manager.currency}"
                        
                        await update.message.reply_text(response_text, parse_mode='Markdown')
                        self.metrics.log_command(1.0, "finance")
                        return
                    else:
                        await update.message.reply_text("❌ Failed to add expense. Please try again.")
                        return
                
                elif intent == 'income' and entities.get('amount'):
                    # Add income automatically
                    amount = entities['amount']
                    source = entities.get('source', 'income')
                    description = entities.get('description', f'Income from {source}')
                    
                    success = await self.finance_manager.add_income(amount, source, description)
                    if success:
                        response_text = f"💰 **Income Added Automatically**\n\n"
                        response_text += f"• Amount: {amount:.2f} {self.finance_manager.currency}\n"
                        response_text += f"• Source: {source}\n"
                        response_text += f"• Description: {description}\n\n"
                        response_text += f"💳 New balance: {self.finance_manager.balance:.2f} {self.finance_manager.currency}"
                        
                        await update.message.reply_text(response_text, parse_mode='Markdown')
                        self.metrics.log_command(1.0, "finance")
                        return
                    else:
                        await update.message.reply_text("❌ Failed to add income. Please try again.")
                        return
                
                elif intent == 'balance':
                    # Show balance
                    await self.show_finance_menu(update, context)
                    return
                
                elif intent == 'report':
                    # Generate report
                    balance_info = await self.finance_manager.get_balance()
                    report_text = f"📈 **Quick Financial Report**\n\n"
                    report_text += f"💳 Balance: {balance_info['balance']:.2f} {balance_info['currency']}\n"
                    report_text += f"📅 Today: +{balance_info['today_income']:.2f} / -{balance_info['today_expenses']:.2f}\n"
                    report_text += f"📦 Total transactions: {balance_info['total_transactions']}"
                    
                    await update.message.reply_text(report_text, parse_mode='Markdown')
                    return
        
        # Check for AI question (starts with "ai:" or contains AI keywords)
        if (ENABLE_AI and self.ai_manager.is_operational() and 
            (user_text_lower.startswith("ai:") or user_text_lower.startswith("ask:"))):
            
            # Remove prefix and get AI response
            question = user_text[3:].strip() if user_text_lower.startswith("ai:") else user_text[4:].strip()
            
            await update.message.reply_text("🤖 Thinking...")
            
            try:
                ai_response = await self.ai_manager.get_ai_response(update.effective_user.id, question)
                await update.message.reply_text(f"🤖 **AI Response:**\n\n{ai_response}", parse_mode='Markdown')
                self.metrics.log_command(1.0, "ai")
                return
            except Exception as e:
                await update.message.reply_text(f"🤖 Error getting AI response: {str(e)[:100]}")
                self.metrics.log_error(str(e), "ai")
                return
        
        # Check for finance commands
        if ENABLE_FINANCE and self.finance_manager.is_operational():
            if user_text_lower.startswith("expense:"):
                # Parse expense: amount category description
                try:
                    parts = user_text[8:].strip().split(' ', 2)
                    if len(parts) >= 2:
                        amount = float(parts[0])
                        category = parts[1]
                        description = parts[2] if len(parts) > 2 else ""
                        
                        success = await self.finance_manager.add_expense(amount, category, description)
                        if success:
                            await update.message.reply_text(
                                f"💸 **Expense Added**\n\n• Amount: {amount:.2f} {self.finance_manager.currency}\n• Category: {category}\n• Description: {description}\n\nUse /finance to see your balance.",
                                parse_mode='Markdown'
                            )
                            self.metrics.log_command(1.0, "finance")
                        else:
                            await update.message.reply_text("❌ Failed to add expense. Please try again.")
                    else:
                        await update.message.reply_text("💸 Format: `expense: amount category description`\nExample: `expense: 25.50 food Lunch at restaurant`", parse_mode='Markdown')
                    return
                except ValueError:
                    await update.message.reply_text("❌ Invalid amount. Use format: `expense: 25.50 food description`", parse_mode='Markdown')
                    return
            
            elif user_text_lower.startswith("income:"):
                # Parse income: amount source description
                try:
                    parts = user_text[7:].strip().split(' ', 2)
                    if len(parts) >= 2:
                        amount = float(parts[0])
                        source = parts[1]
                        description = parts[2] if len(parts) > 2 else ""
                        
                        success = await self.finance_manager.add_income(amount, source, description)
                        if success:
                            await update.message.reply_text(
                                f"💰 **Income Added**\n\n• Amount: {amount:.2f} {self.finance_manager.currency}\n• Source: {source}\n• Description: {description}\n\nUse /finance to see your balance.",
                                parse_mode='Markdown'
                            )
                            self.metrics.log_command(1.0, "finance")
                        else:
                            await update.message.reply_text("❌ Failed to add income. Please try again.")
                    else:
                        await update.message.reply_text("💰 Format: `income: amount source description`\nExample: `income: 2500 salary Monthly payment`", parse_mode='Markdown')
                    return
                except ValueError:
                    await update.message.reply_text("❌ Invalid amount. Use format: `income: 2500 salary description`", parse_mode='Markdown')
                    return
        
        # Simple response patterns for basic interactions
        if any(word in user_text_lower for word in ["hello", "hi", "hey"]):
            response = f"Hello! I'm UmbraSIL v{BOT_VERSION}. Type 'ai: your question' for AI chat, or use /help to see what I can do!"
        elif any(word in user_text_lower for word in ["status", "health"]):
            await self.show_system_status(update, context)
            return
        elif any(word in user_text_lower for word in ["help", "commands"]):
            await self.help_command(update, context)
            return
        elif any(word in user_text_lower for word in ["menu", "options"]):
            await self.main_menu_command(update, context)
            return
        elif any(word in user_text_lower for word in ["finance", "money", "budget"]):
            if ENABLE_FINANCE:
                await self.show_finance_menu(update, context)
                return
            else:
                response = "💰 Finance module is not enabled."
        elif any(word in user_text_lower for word in ["business", "docker", "vps"]):
            if ENABLE_BUSINESS:
                await self.show_business_menu(update, context)
                return
            else:
                response = "⚙️ Business module is not enabled."
        else:
            # If AI is available, suggest using it
            if ENABLE_AI and self.ai_manager.is_operational():
                response = f"I received: '{user_text[:100]}'\n\n💡 **Tip**: Start your message with 'ai:' for AI assistance!\n\nExample: `ai: How can I optimize my workflow?`\n\nOr use /help for commands and /menu for navigation."
            else:
                response = f"I received: '{user_text[:100]}'\n\nUse /help for commands or /menu for navigation."
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def show_system_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show system status"""
        try:
            # Get basic system info
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            status_text = f"""
📊 **System Status**

🤖 **Bot Info**:
• Version: {BOT_VERSION}
• Commands: {self.metrics.command_count}
• Success Rate: {self.metrics.get_success_rate():.1f}%
• Uptime: {self.metrics.get_uptime()}

⚙️ **System Resources**:
• CPU: {cpu_percent}%
• Memory: {memory.percent}%
• Disk: {disk.percent}%
• Platform: {platform.system()}

✅ **Status**: All systems operational!
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="system_status"),
                    InlineKeyboardButton("🏠 Menu", callback_data="main_menu")
                ]
            ]
            
            if update.message:
                await update.message.reply_text(status_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
            elif update.callback_query:
                await update.callback_query.edit_message_text(status_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        
        except Exception as e:
            logger.error(f"System status error: {e}")
            error_text = f"❌ Error getting status: {str(e)[:200]}"
            keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="main_menu")]]
            
            if update.message:
                await update.message.reply_text(error_text, reply_markup=InlineKeyboardMarkup(keyboard))
            elif update.callback_query:
                await update.callback_query.edit_message_text(error_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def show_bot_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot information"""
        info_text = f"""
ℹ️ **Bot Information**

🤖 **UmbraSIL Bot**
• Version: {BOT_VERSION}
• Created: 2025
• Purpose: Personal VPS Assistant

📈 **Current Session**:
• Started: {self.metrics.start_time.strftime('%H:%M:%S UTC')}
• Uptime: {self.metrics.get_uptime()}
• Commands Processed: {self.metrics.command_count}
• Active Users: {len(self.metrics.active_users)}

🔧 **Features**:
• Secure user authentication
• System resource monitoring
• Interactive menu navigation
• Error handling and logging

✨ **Status**: Running smoothly!
"""
        
        keyboard = [
            [
                InlineKeyboardButton("📊 System Status", callback_data="system_status"),
                InlineKeyboardButton("🏠 Menu", callback_data="main_menu")
            ]
        ]
        
        await update.callback_query.edit_message_text(
            info_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
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
                await self.help_command(update, context)
            elif callback_data == "system_status":
                await self.show_system_status(update, context)
            elif callback_data == "bot_info":
                await self.show_bot_info(update, context)
            
            # Module menus
            elif callback_data == "ai_menu":
                await self.show_ai_menu(update, context)
            elif callback_data == "finance_menu":
                await self.show_finance_menu(update, context)
            elif callback_data == "business_menu":
                await self.show_business_menu(update, context)
            elif callback_data == "monitoring_menu":
                await self.show_monitoring_menu(update, context)
            
            # AI module actions
            elif callback_data == "ai_ask":
                await query.edit_message_text(
                    "🤖 **AI Assistant**\n\nType your question in the chat or use format:\n`ai: your question here`\n\nExample: `ai: What's the best way to manage my finances?`",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="main_menu")]])
                )
            elif callback_data == "ai_clear":
                # Clear AI context
                if hasattr(self.ai_manager, 'context_storage'):
                    self.ai_manager.context_storage.clear()
                await query.edit_message_text(
                    "🧹 **AI Context Cleared**\n\nAll conversation history has been cleared.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🤖 AI Menu", callback_data="ai_menu")]])
                )
            
            # Finance module actions
            elif callback_data == "finance_expense":
                await query.edit_message_text(
                    "💸 **Add Expense**\n\nTo add an expense, use the format:\n`expense: amount category description`\n\nExample: `expense: 25.50 food Pizza for lunch`",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💰 Finance Menu", callback_data="finance_menu")]])
                )
            elif callback_data == "finance_income":
                await query.edit_message_text(
                    "💰 **Add Income**\n\nTo add income, use the format:\n`income: amount source description`\n\nExample: `income: 2500 salary Monthly salary`",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💰 Finance Menu", callback_data="finance_menu")]])
                )
            elif callback_data == "finance_balance":
                await self.show_finance_menu(update, context)
            elif callback_data == "finance_report":
                balance_info = await self.finance_manager.get_balance()
                report_text = f"""
📈 **Finance Report**

💳 **Current Balance**: {balance_info['balance']:.2f} {balance_info['currency']}

📊 **Summary**:
• Total Transactions: {balance_info['total_transactions']}
• Today's Income: +{balance_info['today_income']:.2f}
• Today's Expenses: -{balance_info['today_expenses']:.2f}
• Net Today: {balance_info['today_income'] - balance_info['today_expenses']:.2f}

📅 **Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
                await query.edit_message_text(
                    report_text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💰 Finance Menu", callback_data="finance_menu")]])
                )
            
            # Business module actions
            elif callback_data == "business_docker":
                docker_status = await self.business_manager.get_docker_status()
                if 'error' in docker_status:
                    status_text = f"🐳 **Docker Status**\n\n❌ Error: {docker_status['error']}"
                else:
                    status_text = f"""
🐳 **Docker Status**

📊 **Container Summary**:
• Total: {docker_status['total_containers']}
• Running: {docker_status['running']}
• Stopped: {docker_status['stopped']}

📋 **Recent Containers**:
{chr(10).join([f"• {c['name']}: {c['status']}" for c in docker_status.get('containers', [])[:5]])}
"""
                await query.edit_message_text(
                    status_text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Business Menu", callback_data="business_menu")]])
                )
            elif callback_data == "business_vps":
                vps_status = await self.business_manager.get_vps_status()
                if 'error' in vps_status:
                    status_text = f"🖥️ **VPS Status**\n\n❌ Error: {vps_status['error']}"
                else:
                    status_text = f"🖥️ **VPS Status**\n\n✅ Connected\n\n```\n{vps_status['info']}\n```"
                await query.edit_message_text(
                    status_text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Business Menu", callback_data="business_menu")]])
                )
            elif callback_data == "business_metrics":
                await self.show_system_status(update, context)
            elif callback_data == "business_services":
                await query.edit_message_text(
                    "🔧 **Business Services**\n\nService management features:\n• n8n workflow automation\n• Docker container management\n• VPS monitoring\n• System metrics\n\nUse the business menu to access specific services.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Business Menu", callback_data="business_menu")]])
                )
            
            # Monitoring module actions
            elif callback_data == "monitoring_metrics":
                health = await self.monitoring_manager.check_system_health()
                metrics_text = f"""
📈 **System Metrics**

⚙️ **Resource Usage**:
• CPU: {health.get('cpu_percent', 0):.1f}%
• Memory: {health.get('memory_percent', 0):.1f}%
• Disk: {health.get('disk_percent', 0):.1f}%

🎯 **Thresholds**:
• CPU Alert: >{self.monitoring_manager.thresholds['cpu']}%
• Memory Alert: >{self.monitoring_manager.thresholds['memory']}%
• Disk Alert: >{self.monitoring_manager.thresholds['disk']}%

📊 **Status**: {health.get('status', 'unknown').title()}
"""
                await query.edit_message_text(
                    metrics_text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📊 Monitoring Menu", callback_data="monitoring_menu")]])
                )
            elif callback_data == "monitoring_alerts":
                health = await self.monitoring_manager.check_system_health()
                alerts = health.get('alerts', [])
                alerts_text = f"""
🚨 **System Alerts**

📊 **Active Alerts**: {len(alerts)}

{chr(10).join([f"⚠️ {alert}" for alert in alerts]) if alerts else "✅ No active alerts"}

🔔 **Alert Thresholds**:
• CPU: {self.monitoring_manager.thresholds['cpu']}%
• Memory: {self.monitoring_manager.thresholds['memory']}%
• Disk: {self.monitoring_manager.thresholds['disk']}%
"""
                await query.edit_message_text(
                    alerts_text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📊 Monitoring Menu", callback_data="monitoring_menu")]])
                )
            elif callback_data == "monitoring_health":
                await self.show_monitoring_menu(update, context)
            elif callback_data == "monitoring_logs":
                await query.edit_message_text(
                    "📋 **System Logs**\n\nRecent bot activity:\n• Bot started successfully\n• All modules initialized\n• System monitoring active\n\nFor detailed logs, check your hosting platform's log viewer.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📊 Monitoring Menu", callback_data="monitoring_menu")]])
                )
            
            else:
                # Unknown action
                await query.edit_message_text(
                    f"🚧 **Action Not Available**\n\nThe feature '{callback_data}' is not implemented yet.\n\nUse the menu to navigate to available features.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="main_menu")]])
                )
                
        except Exception as e:
            logger.error(f"Button handler error: {e}")
            self.metrics.log_error(str(e))
            await query.edit_message_text(
                "❌ An error occurred. Please try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="main_menu")]])
            )
    
    async def handle_photo_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages (receipts)"""
        if not update.message or not update.message.photo:
            return
        
        # Notify user that receipt processing is in progress
        processing_msg = await update.message.reply_text(
            "📸 **Receipt detected!**\n\nProcessing your receipt...",
            parse_mode='Markdown'
        )
        
        # For now, provide instructions since OCR requires additional setup
        await processing_msg.edit_text(
            "📸 **Receipt Processing**\n\n"
            "Receipt OCR is not yet configured. To add this expense manually, please type:\n\n"
            "`spent [amount] at [store]`\n\n"
            "Example: `spent 47.30 at migros`\n\n"
            "💡 **Tip:** With NLP enabled, I can understand natural language like:\n"
            "• \"spent 25 at coop\"\n"
            "• \"paid 15.50 for lunch\"\n"
            "• \"bought groceries for 80\"",
            parse_mode='Markdown'
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

# Simplified main function without asyncio conflicts
def main():
    """Main function - uses run_polling to avoid event loop conflicts"""
    try:
        logger.info("🚀 Starting UmbraSIL Bot...")
        
        # Create bot instance
        bot = UmbraSILBot()
        
        # Run with polling (Railway handles health checks via PORT)
        logger.info("✅ Bot initialized, starting polling...")
        bot.application.run_polling(
            drop_pending_updates=True
        )
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
