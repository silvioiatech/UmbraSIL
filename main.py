import os
import sys
import logging
import psutil
import platform
import asyncio
import paramiko
import base64
import io
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

class VPSMonitor:
    """Monitor external VPS via SSH"""
    
    def __init__(self):
        self.host = os.getenv("VPS_HOST")
        self.port = int(os.getenv("VPS_PORT", "22"))
        self.username = os.getenv("VPS_USERNAME")
        self.private_key_b64 = os.getenv("VPS_PRIVATE_KEY")
        self.ssh_client = None
        
    async def connect(self):
        """Connect to VPS via SSH"""
        try:
            if not all([self.host, self.username, self.private_key_b64]):
                logger.warning("VPS credentials not configured")
                return False
                
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Decode private key
            private_key_data = base64.b64decode(self.private_key_b64)
            private_key = paramiko.RSAKey.from_private_key_file(
                io.StringIO(private_key_data.decode())
            )
            
            self.ssh_client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                pkey=private_key,
                timeout=10
            )
            
            return True
            
        except Exception as e:
            logger.error(f"VPS connection error: {e}")
            return False
    
    async def get_system_stats(self):
        """Get VPS system statistics"""
        try:
            if not self.ssh_client:
                if not await self.connect():
                    return None
            
            # Get CPU usage
            stdin, stdout, stderr = self.ssh_client.exec_command(
                "top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1}'"
            )
            cpu_usage = float(stdout.read().decode().strip())
            
            # Get memory usage
            stdin, stdout, stderr = self.ssh_client.exec_command(
                "free | grep Mem | awk '{printf \"%.1f %.1f %.1f\", $3/$2 * 100.0, $3/1024/1024, $2/1024/1024}'"
            )
            memory_info = stdout.read().decode().strip().split()
            memory_percent = float(memory_info[0])
            memory_used_gb = float(memory_info[1])
            memory_total_gb = float(memory_info[2])
            
            # Get disk usage
            stdin, stdout, stderr = self.ssh_client.exec_command(
                "df -h / | awk 'NR==2 {printf \"%s %s %s\", $3, $2, $5}'"
            )
            disk_info = stdout.read().decode().strip().split()
            disk_used = disk_info[0]
            disk_total = disk_info[1]
            disk_percent = float(disk_info[2].replace('%', ''))
            
            # Get uptime
            stdin, stdout, stderr = self.ssh_client.exec_command("uptime -p")
            uptime = stdout.read().decode().strip()
            
            # Get load average
            stdin, stdout, stderr = self.ssh_client.exec_command("uptime | awk -F'load average:' '{print $2}'")
            load_avg = stdout.read().decode().strip()
            
            return {
                "cpu_percent": cpu_usage,
                "memory_percent": memory_percent,
                "memory_used_gb": memory_used_gb,
                "memory_total_gb": memory_total_gb,
                "disk_used": disk_used,
                "disk_total": disk_total,
                "disk_percent": disk_percent,
                "uptime": uptime,
                "load_avg": load_avg,
                "connected": True
            }
            
        except Exception as e:
            logger.error(f"Error getting VPS stats: {e}")
            return {
                "connected": False,
                "error": str(e)
            }
    
    async def execute_command(self, command: str, timeout: int = 30):
        """Execute command on VPS and return output"""
        try:
            if not self.ssh_client:
                if not await self.connect():
                    return {"success": False, "error": "Connection failed"}
            
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)
            
            output = stdout.read().decode('utf-8', errors='ignore').strip()
            error = stderr.read().decode('utf-8', errors='ignore').strip()
            exit_code = stdout.channel.recv_exit_status()
            
            return {
                "success": exit_code == 0,
                "output": output,
                "error": error,
                "exit_code": exit_code
            }
            
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_directory_listing(self, path: str = "~"):
        """Get directory contents"""
        command = f"ls -la '{path}'"
        result = await self.execute_command(command)
        return result
    
    async def get_file_content(self, filepath: str, max_lines: int = 50):
        """Get file content (limited lines for Telegram)"""
        command = f"head -n {max_lines} '{filepath}'"
        result = await self.execute_command(command)
        return result
    
    async def write_file(self, filepath: str, content: str):
        """Write content to file"""
        # Escape content for shell
        escaped_content = content.replace("'", "'\"'\"'")
        command = f"echo '{escaped_content}' > '{filepath}'"
        result = await self.execute_command(command)
        return result
    
    async def get_running_processes(self):
        """Get running processes"""
        command = "ps aux --sort=-%cpu | head -20"
        result = await self.execute_command(command)
        return result
    
    async def get_docker_status(self):
        """Get Docker containers status"""
        command = "docker ps -a"
        result = await self.execute_command(command)
        return result
    
    async def get_service_status(self, service_name: str):
        """Get systemd service status"""
        command = f"systemctl status {service_name}"
        result = await self.execute_command(command)
        return result
    
    async def restart_service(self, service_name: str):
        """Restart systemd service"""
        command = f"sudo systemctl restart {service_name}"
        result = await self.execute_command(command)
        return result
    
    async def get_logs(self, service_name: str = None, lines: int = 50):
        """Get system or service logs"""
        if service_name:
            command = f"journalctl -u {service_name} -n {lines} --no-pager"
        else:
            command = f"journalctl -n {lines} --no-pager"
        result = await self.execute_command(command)
        return result
    
    async def get_network_info(self):
        """Get network information"""
        command = "ss -tuln | head -20; echo '---'; ip addr show | head -30"
        result = await self.execute_command(command)
        return result
    
    def disconnect(self):
        """Disconnect from VPS"""
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None

class UmbraSILBot:
    """Main bot class - simplified and working"""
    
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
        
        # Initialize components
        self.metrics = BotMetrics()
        self.auth = SimpleAuth()
        self.vps_monitor = VPSMonitor()
        
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
        
        # Message handler for command execution
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.require_auth(self.handle_text_message)
        ))
        
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
        """Show VPS health check"""
        try:
            # Get VPS statistics
            vps_stats = await self.vps_monitor.get_system_stats()
            
            if not vps_stats or not vps_stats.get("connected"):
                # Show connection error
                error_msg = vps_stats.get("error", "Connection failed") if vps_stats else "VPS credentials not configured"
                
                health_text = f"""
❤️ **VPS Health Check**

🚨 **Connection Status**: FAILED

⚠️ **Error**: {error_msg}

🔧 **Troubleshooting**:
• Check VPS credentials in Railway environment
• Verify VPS_HOST, VPS_USERNAME, VPS_PRIVATE_KEY
• Ensure VPS is accessible on port {self.vps_monitor.port}
• Check SSH key permissions

🔄 **Last Checked**: {datetime.now().strftime('%H:%M:%S')}
"""
            else:
                # Determine health status
                cpu_percent = vps_stats["cpu_percent"]
                memory_percent = vps_stats["memory_percent"]
                disk_percent = vps_stats["disk_percent"]
                
                health_status = "✅ HEALTHY"
                if cpu_percent > 80 or memory_percent > 80 or disk_percent > 90:
                    health_status = "⚠️ WARNING"
                if cpu_percent > 95 or memory_percent > 95 or disk_percent > 95:
                    health_status = "🚨 CRITICAL"
                
                health_text = f"""
❤️ **VPS Health Check**

🟢 **Overall Status**: {health_status}
🔗 **Host**: `{self.vps_monitor.host}`

💻 **System Resources**
• CPU Usage: `{cpu_percent:.1f}%`
• Memory: `{memory_percent:.1f}%` ({vps_stats['memory_used_gb']:.1f}GB / {vps_stats['memory_total_gb']:.1f}GB)
• Disk: `{disk_percent:.1f}%` ({vps_stats['disk_used']} / {vps_stats['disk_total']})

⚙️ **System Info**
• Uptime: `{vps_stats['uptime']}`
• Load Average: `{vps_stats['load_avg']}`

🤖 **Bot Stats**
• Commands: `{self.metrics.command_count}`
• Bot Uptime: `{self.metrics.get_uptime()}`

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
                f"❌ Error getting VPS health status: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="menu_monitoring")
                ]])
            )
    
    async def show_vps_control_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show VPS control main menu"""
        control_text = """
🖥️ **VPS Control Panel**

Full access to your VPS management:
"""
        
        keyboard = [
            [
                InlineKeyboardButton("⚙️ Execute Command", callback_data="execute_command"),
                InlineKeyboardButton("🔍 System Info", callback_data="system_info")
            ],
            [
                InlineKeyboardButton("🌐 Network Info", callback_data="network_info"),
                InlineKeyboardButton("🔄 Restart Services", callback_data="service_control")
            ],
            [
                InlineKeyboardButton("🔙 Back to Business", callback_data="menu_business")
            ]
        ]
        
        await update.callback_query.edit_message_text(
            control_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages for command execution"""
        if not update.message or not update.message.text:
            return
            
        # Check if we're expecting a command
        if context.user_data.get('expecting_command'):
            command = update.message.text.strip()
            
            # Clear the flag
            context.user_data['expecting_command'] = False
            
            # Execute the command
            await self.execute_vps_command(update, context, command)
        else:
            # Regular text message - could be used for AI chat later
            await update.message.reply_text(
                "💡 Use /menu to access bot features or send commands via VPS Control Panel."
            )
    
    async def execute_vps_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, command: str):
        """Execute command on VPS and show result"""
        try:
            # Show "executing" message
            status_msg = await update.message.reply_text(
                f"⚙️ **Executing Command**\n\n`{command}`\n\n⏳ Please wait...",
                parse_mode='Markdown'
            )
            
            # Execute command
            result = await self.vps_monitor.execute_command(command)
            
            if result["success"]:
                # Format successful output
                output = result["output"] if result["output"] else "(No output)"
                
                # Limit output length for Telegram
                if len(output) > 3500:
                    output = output[:3500] + "\n\n... (output truncated)"
                
                response_text = f"""
⚙️ **Command Executed Successfully**

📝 **Command**: `{command}`
✅ **Exit Code**: {result['exit_code']}

📋 **Output**:
```
{output}
```

🔄 **Executed**: {datetime.now().strftime('%H:%M:%S')}
"""
            else:
                # Format error output
                error = result["error"] if result["error"] else "Unknown error"
                
                if len(error) > 3500:
                    error = error[:3500] + "\n\n... (error truncated)"
                
                response_text = f"""
⚙️ **Command Failed**

📝 **Command**: `{command}`
❌ **Exit Code**: {result.get('exit_code', 'N/A')}

🚫 **Error**:
```
{error}
```

🔄 **Executed**: {datetime.now().strftime('%H:%M:%S')}
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("⚙️ Execute Another", callback_data="execute_command"),
                    InlineKeyboardButton("🖥️ VPS Control", callback_data="vps_control")
                ]
            ]
            
            # Update the status message with results
            await status_msg.edit_text(
                response_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            await update.message.reply_text(
                f"❌ **Error executing command**\n\n{str(e)}",
                parse_mode='Markdown'
            )
    
    async def show_docker_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show Docker containers status"""
        try:
            result = await self.vps_monitor.get_docker_status()
            
            if not result["success"]:
                status_text = f"""
🐳 **Docker Status**

❌ **Error**: {result['error']}

🔧 **Possible Issues**:
• Docker not installed
• Docker service not running
• Permission denied

🔄 **Last Checked**: {datetime.now().strftime('%H:%M:%S')}
"""
            else:
                # Format Docker output
                output = result["output"][:3000]  # Limit for Telegram
                status_text = f"""
🐳 **Docker Containers**

```
{output}
```

🔄 **Last Updated**: {datetime.now().strftime('%H:%M:%S')}
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="docker_management"),
                    InlineKeyboardButton("🔙 Back", callback_data="vps_control")
                ]
            ]
            
            await update.callback_query.edit_message_text(
                status_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Docker status error: {e}")
            await update.callback_query.edit_message_text(
                f"❌ Error getting Docker status: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="vps_control")
                ]])
            )
    
    async def show_vps_processes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show running processes"""
        try:
            result = await self.vps_monitor.get_running_processes()
            
            if not result["success"]:
                process_text = f"""
📊 **VPS Processes**

❌ **Error**: {result['error']}

🔄 **Last Checked**: {datetime.now().strftime('%H:%M:%S')}
"""
            else:
                # Format process output
                output = result["output"][:3000]  # Limit for Telegram
                process_text = f"""
📊 **Top Processes (by CPU)**

```
{output}
```

🔄 **Last Updated**: {datetime.now().strftime('%H:%M:%S')}
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="vps_processes"),
                    InlineKeyboardButton("🔙 Back", callback_data="vps_control")
                ]
            ]
            
            await update.callback_query.edit_message_text(
                process_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Processes error: {e}")
            await update.callback_query.edit_message_text(
                f"❌ Error getting processes: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="vps_control")
                ]])
            )
    
    async def show_file_manager(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show file manager"""
        try:
            # Default to home directory
            current_path = context.user_data.get('current_path', '~')
            result = await self.vps_monitor.get_directory_listing(current_path)
            
            if not result["success"]:
                file_text = f"""
📁 **File Manager**

❌ **Error**: {result['error']}

📂 **Path**: `{current_path}`

🔄 **Last Checked**: {datetime.now().strftime('%H:%M:%S')}
"""
            else:
                # Format directory listing
                output = result["output"][:3000]  # Limit for Telegram
                file_text = f"""
📁 **File Manager**

📂 **Path**: `{current_path}`

```
{output}
```

🔄 **Last Updated**: {datetime.now().strftime('%H:%M:%S')}
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="file_manager"),
                    InlineKeyboardButton("📄 Read File", callback_data="read_file")
                ],
                [
                    InlineKeyboardButton("✏️ Write File", callback_data="write_file"),
                    InlineKeyboardButton("🔙 Back", callback_data="vps_control")
                ]
            ]
            
            await update.callback_query.edit_message_text(
                file_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"File manager error: {e}")
            await update.callback_query.edit_message_text(
                f"❌ Error accessing files: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="vps_control")
                ]])
            )
    
    async def show_system_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show system logs"""
        try:
            result = await self.vps_monitor.get_logs()
            
            if not result["success"]:
                log_text = f"""
📋 **System Logs**

❌ **Error**: {result['error']}

🔄 **Last Checked**: {datetime.now().strftime('%H:%M:%S')}
"""
            else:
                # Format log output
                output = result["output"][:3000]  # Limit for Telegram
                log_text = f"""
📋 **System Logs (Last 50)**

```
{output}
```

🔄 **Last Updated**: {datetime.now().strftime('%H:%M:%S')}
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="system_logs"),
                    InlineKeyboardButton("🔍 Service Logs", callback_data="service_logs")
                ],
                [
                    InlineKeyboardButton("🔙 Back", callback_data="vps_control")
                ]
            ]
            
            await update.callback_query.edit_message_text(
                log_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"System logs error: {e}")
            await update.callback_query.edit_message_text(
                f"❌ Error getting logs: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="vps_control")
                ]])
            )
    
    async def show_network_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show network information"""
        try:
            result = await self.vps_monitor.get_network_info()
            
            if not result["success"]:
                network_text = f"""
🌐 **Network Information**

❌ **Error**: {result['error']}

🔄 **Last Checked**: {datetime.now().strftime('%H:%M:%S')}
"""
            else:
                # Format network output
                output = result["output"][:3000]  # Limit for Telegram
                network_text = f"""
🌐 **Network Information**

```
{output}
```

🔄 **Last Updated**: {datetime.now().strftime('%H:%M:%S')}
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="network_info"),
                    InlineKeyboardButton("🔙 Back", callback_data="vps_control")
                ]
            ]
            
            await update.callback_query.edit_message_text(
                network_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Network info error: {e}")
            await update.callback_query.edit_message_text(
                f"❌ Error getting network info: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="vps_control")
                ]])
            )
    
    async def prompt_command_execution(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Prompt user to send a command"""
        prompt_text = """
⚙️ **Execute Command**

⚠️ **DANGER ZONE**: You can execute ANY command on your VPS.

📝 **Instructions**:
1. Type your command in the next message
2. Commands run as your VPS user
3. Use `sudo` for admin commands
4. Output limited to prevent spam

💫 **Examples**:
• `ls -la /var/www`
• `sudo systemctl status nginx`
• `df -h`
• `top -bn1 | head -10`

🚀 **Send your command now:**
"""
        
        keyboard = [
            [
                InlineKeyboardButton("❌ Cancel", callback_data="vps_control")
            ]
        ]
        
        # Set flag to expect command
        context.user_data['expecting_command'] = True
        
        await update.callback_query.edit_message_text(
            prompt_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
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
            elif callback_data in ["n8n_clients"]:
                await query.edit_message_text(
                    "⚙️ **n8n Client Management**\n\nThis feature is coming soon! Will manage your n8n workflow instances.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Back", callback_data="menu_business")
                    ]])
                )
            
            # VPS Management Features
            elif callback_data == "vps_control":
                await self.show_vps_control_menu(update, context)
            elif callback_data == "docker_management":
                await self.show_docker_status(update, context)
            elif callback_data == "vps_processes":
                await self.show_vps_processes(update, context)
            elif callback_data == "file_manager":
                await self.show_file_manager(update, context)
            elif callback_data == "system_logs":
                await self.show_system_logs(update, context)
            elif callback_data == "execute_command":
                await self.prompt_command_execution(update, context)
            elif callback_data == "network_info":
                await self.show_network_info(update, context)
            
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
                        InlineKeyboardButton("🖥️ VPS Control", callback_data="vps_control"),
                        InlineKeyboardButton("🏭 n8n Clients", callback_data="n8n_clients")
                    ],
                    [
                        InlineKeyboardButton("🐳 Docker", callback_data="docker_management"),
                        InlineKeyboardButton("📊 Processes", callback_data="vps_processes")
                    ],
                    [
                        InlineKeyboardButton("📁 File Manager", callback_data="file_manager"),
                        InlineKeyboardButton("📋 System Logs", callback_data="system_logs")
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
