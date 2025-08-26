import os
import sys
import logging
import psutil
import platform
import asyncio
import paramiko
import base64
import io
import json
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
    MessageHandler,
    filters,
    ContextTypes
)

# AI API imports
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

try:
    import anthropic
except ImportError:
    anthropic = None

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

class AIAgent:
    """Intelligent AI Agent using OpenAI/Claude APIs"""
    
    def __init__(self, vps_monitor):
        self.vps_monitor = vps_monitor
        
        # Initialize AI clients
        openai_key = os.getenv("OPENAI_API_KEY")
        claude_key = os.getenv("CLAUDE_API_KEY")
        
        self.openai_client = AsyncOpenAI(api_key=openai_key) if openai_key and AsyncOpenAI else None
        self.claude_client = anthropic.AsyncAnthropic(api_key=claude_key) if claude_key and anthropic else None
        
        # Conversation context per user
        self.user_contexts = {}
        
        # System prompt for the AI agent
        self.system_prompt = f"""
You are UmbraSIL, an intelligent VPS management assistant. You can:

1. **Have normal conversations** - Chat naturally about any topic
2. **Manage VPS systems** - Execute commands, monitor health, manage services
3. **Control Docker** - Manage containers and services
4. **Handle files** - Browse, read, and manage filesystem
5. **System monitoring** - Check health, processes, resources

**IMPORTANT CAPABILITIES**:
- You have access to a VPS at {self.vps_monitor.host or 'configured host'} via SSH
- You can execute ANY shell command when requested
- You can check system status, manage services, handle Docker containers
- You understand both casual conversation AND technical requests

**Response Guidelines**:
- For casual conversation: Respond naturally and helpfully
- For VPS requests: Indicate you'll execute the command and explain what you're doing
- Be conversational but professional
- If asked to do something technical, explain what you'll do first

**Available Functions**:
- execute_command(command) - Run shell commands on VPS
- get_system_status() - Get CPU/memory/disk usage
- get_docker_status() - List Docker containers
- list_directory(path) - Browse filesystem

Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    async def process_message(self, user_id: int, message: str) -> Dict[str, Any]:
        """Process user message with AI and determine actions"""
        try:
            # Get or create user context
            if user_id not in self.user_contexts:
                self.user_contexts[user_id] = []
            
            # Add user message to context
            self.user_contexts[user_id].append({
                "role": "user",
                "content": message
            })
            
            # Keep context manageable (last 10 messages)
            if len(self.user_contexts[user_id]) > 20:
                self.user_contexts[user_id] = self.user_contexts[user_id][-20:]
            
            # Get AI response
            ai_response = await self._get_ai_response(user_id)
            
            # Parse response for actions
            actions = self._parse_ai_response(ai_response)
            
            # Add AI response to context
            self.user_contexts[user_id].append({
                "role": "assistant",
                "content": ai_response
            })
            
            return {
                "response": ai_response,
                "actions": actions,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"AI Agent error: {e}")
            return {
                "response": f"I apologize, I'm having trouble processing your request right now. Error: {str(e)}",
                "actions": [],
                "success": False
            }
    
    async def _get_ai_response(self, user_id: int) -> str:
        """Get response from AI API"""
        messages = [
            {"role": "system", "content": self.system_prompt}
        ] + self.user_contexts[user_id]
        
        # Try OpenAI first
        if self.openai_client:
            try:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"OpenAI error: {e}")
        
        # Fallback to Claude
        if self.claude_client:
            try:
                # Convert messages for Claude format
                claude_messages = []
                for msg in self.user_contexts[user_id]:
                    if msg["role"] != "system":
                        claude_messages.append(msg)
                
                response = await self.claude_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=1000,
                    system=self.system_prompt,
                    messages=claude_messages
                )
                return response.content[0].text
            except Exception as e:
                logger.error(f"Claude error: {e}")
        
        # Fallback to rule-based responses
        return self._get_fallback_response(self.user_contexts[user_id][-1]["content"])
    
    def _parse_ai_response(self, response: str) -> List[Dict]:
        """Parse AI response for actionable commands"""
        actions = []
        
        # Look for command execution indicators
        command_indicators = [
            "I'll execute", "Let me run", "I'll check", "Running", "Executing",
            "Let me get", "I'll show you", "Checking", "Getting"
        ]
        
        response_lower = response.lower()
        
        # Check for system status request
        if any(phrase in response_lower for phrase in ["system status", "server health", "check system"]):
            actions.append({"type": "system_status"})
        
        # Check for docker requests
        if any(phrase in response_lower for phrase in ["docker", "container"]):
            actions.append({"type": "docker_status"})
        
        # Check for file operations
        if any(phrase in response_lower for phrase in ["list files", "directory", "browse"]):
            actions.append({"type": "file_list", "path": "~"})
        
        # Check for specific commands
        command_patterns = {
            "disk space": "df -h",
            "memory usage": "free -h",
            "processes": "ps aux --sort=-%cpu | head -15",
            "uptime": "uptime",
            "network": "ss -tuln | head -20"
        }
        
        for pattern, command in command_patterns.items():
            if pattern in response_lower:
                actions.append({"type": "execute_command", "command": command})
        
        return actions
    
    def _get_fallback_response(self, message: str) -> str:
        """Fallback response when AI APIs are not available"""
        message_lower = message.lower()
        
        # Greeting responses
        if any(word in message_lower for word in ["hello", "hi", "hey"]):
            return "Hello! I'm UmbraSIL, your intelligent VPS assistant. I can help you manage your server and also chat about anything you'd like. What can I do for you today?"
        
        # VPS related responses
        if any(word in message_lower for word in ["server", "vps", "system", "status"]):
            return "I'd be happy to help with your VPS! I can check system status, execute commands, manage Docker containers, and more. What would you like me to do?"
        
        # Docker responses
        if "docker" in message_lower or "container" in message_lower:
            return "I can help you manage Docker containers! Let me check your container status for you."
        
        # Command responses
        if any(word in message_lower for word in ["command", "execute", "run"]):
            return "I can execute commands on your VPS! Just tell me what you'd like me to run, or ask me to check something specific like disk space or memory usage."
        
        # General conversation
        return f"I understand you said: '{message}'. I'm your intelligent VPS assistant, but I can also chat about general topics! For VPS management, I can check system status, execute commands, manage Docker, and browse files. What would you like to do?"
    
    def clear_context(self, user_id: int):
        """Clear conversation context for user"""
        if user_id in self.user_contexts:
            del self.user_contexts[user_id]

class SimpleAuth:
    
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
        
        # Initialize AI Agent
        self.ai_agent = AIAgent(self.vps_monitor)
        
        # Create application
        self.application = Application.builder().token(self.token).build()
        
        # Setup handlers immediately
        self.setup_handlers()
        
        logger.info("UmbraSIL Bot with AI Agent initialized successfully")
    
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
🤖 **Welcome {user.first_name}! I'm Your AI Agent**

I'm UmbraSIL's intelligent assistant. Just **talk to me naturally** and I'll help you manage your VPS!

🚀 **Try saying:**
• "check system status"
• "show disk space"
• "restart nginx"
• "list docker containers"
• "what's the memory usage"

Or use any shell command like `ls -la` or `ps aux`

💬 **Just start chatting with me!**
"""
        keyboard = [
            [
                InlineKeyboardButton("🤖 What can you do?", callback_data="show_help"),
                InlineKeyboardButton("📊 System Status", callback_data="show_status")
            ],
            [
                InlineKeyboardButton("🖥️ VPS Control Panel", callback_data="vps_control"),
                InlineKeyboardButton("🐳 Docker Status", callback_data="docker_management")
            ],
            [
                InlineKeyboardButton("📈 Traditional Menu", callback_data="traditional_menu")
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
        """Handle text messages - Real AI Agent processes everything"""
        if not update.message or not update.message.text:
            return
            
        user_text = update.message.text.strip()
        user_id = update.effective_user.id
        
        # Check if we're expecting a command (VPS command execution)
        if context.user_data.get('expecting_command'):
            context.user_data['expecting_command'] = False
            await self.execute_vps_command(update, context, user_text)
            return
        
        # Process with Real AI Agent
        await self.process_with_ai_agent(update, context, user_text, user_id)
    
    async def process_with_ai_agent(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_message: str, user_id: int):
        """Process message with real AI Agent (OpenAI/Claude)"""
        try:
            # Show typing indicator
            thinking_msg = await update.message.reply_text(
                "🤖 *Thinking...*",
                parse_mode='Markdown'
            )
            
            # Process with AI Agent
            result = await self.ai_agent.process_message(user_id, user_message)
            
            if not result["success"]:
                await thinking_msg.edit_text(
                    f"🤖 **UmbraSIL AI**\n\n{result['response']}",
                    parse_mode='Markdown'
                )
                return
            
            ai_response = result["response"]
            actions = result["actions"]
            
            # Execute any actions the AI determined
            action_results = []
            for action in actions:
                try:
                    if action["type"] == "system_status":
                        vps_stats = await self.vps_monitor.get_system_stats()
                        action_results.append(f"System Status: {'Healthy' if vps_stats and vps_stats.get('connected') else 'Disconnected'}")
                    
                    elif action["type"] == "docker_status":
                        docker_result = await self.vps_monitor.get_docker_status()
                        if docker_result["success"]:
                            container_count = len([line for line in docker_result["output"].split('\n') if line.strip()]) - 1
                            action_results.append(f"Docker: {container_count} containers found")
                        else:
                            action_results.append("Docker: Service unavailable")
                    
                    elif action["type"] == "execute_command":
                        cmd_result = await self.vps_monitor.execute_command(action["command"])
                        if cmd_result["success"]:
                            output = cmd_result["output"][:500] + "..." if len(cmd_result["output"]) > 500 else cmd_result["output"]
                            action_results.append(f"Command '{action['command']}' executed successfully")
                        else:
                            action_results.append(f"Command '{action['command']}' failed: {cmd_result['error'][:200]}")
                    
                    elif action["type"] == "file_list":
                        file_result = await self.vps_monitor.get_directory_listing(action.get("path", "~"))
                        if file_result["success"]:
                            file_count = len([line for line in file_result["output"].split('\n') if line.strip()])
                            action_results.append(f"Directory listing: {file_count} items found")
                        else:
                            action_results.append("Directory listing failed")
                            
                except Exception as e:
                    logger.error(f"Action execution error: {e}")
                    action_results.append(f"Action failed: {str(e)[:100]}")
            
            # Format the final response
            final_response = f"🤖 **UmbraSIL AI**\n\n{ai_response}"
            
            # Add action results if any
            if action_results:
                final_response += "\n\n🔧 **Actions Completed:**\n" + "\n".join([f"• {result}" for result in action_results])
            
            # Add helpful buttons
            keyboard = [
                [
                    InlineKeyboardButton("📊 System Status", callback_data="ai_system_status"),
                    InlineKeyboardButton("🐳 Docker Status", callback_data="ai_docker_status")
                ],
                [
                    InlineKeyboardButton("🔄 Clear Context", callback_data="ai_clear_context"),
                    InlineKeyboardButton("🖥️ VPS Control", callback_data="vps_control")
                ]
            ]
            
            await thinking_msg.edit_text(
                final_response,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"AI Agent processing error: {e}")
            await update.message.reply_text(
                f"🤖 **UmbraSIL AI**\n\n❌ I apologize, but I encountered an error processing your request: {str(e)[:200]}",
                parse_mode='Markdown'
            )
    
    async def ai_agent_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_message: str):
        """AI Agent processes user input and delegates to appropriate modules"""
        try:
            # Show thinking message
            thinking_msg = await update.message.reply_text(
                "🤖 **AI Agent Processing...**\n\n🧠 Analyzing your request...",
                parse_mode='Markdown'
            )
            
            # Analyze user intent and delegate
            intent_result = await self.analyze_user_intent(user_message)
            
            # Execute the appropriate action based on intent
            if intent_result['action'] == 'vps_command':
                await thinking_msg.edit_text(
                    f"🤖 **AI Agent**\n\n📝 Executing VPS command: `{intent_result['command']}`\n\n⏳ Please wait...",
                    parse_mode='Markdown'
                )
                result = await self.vps_monitor.execute_command(intent_result['command'])
                await self.format_command_response(thinking_msg, intent_result['command'], result)
                
            elif intent_result['action'] == 'vps_status':
                await thinking_msg.edit_text(
                    "🤖 **AI Agent**\n\n📊 Getting VPS system status...",
                    parse_mode='Markdown'
                )
                await self.show_ai_vps_status(thinking_msg)
                
            elif intent_result['action'] == 'docker_status':
                await thinking_msg.edit_text(
                    "🤖 **AI Agent**\n\n🐳 Checking Docker containers...",
                    parse_mode='Markdown'
                )
                result = await self.vps_monitor.get_docker_status()
                await self.format_docker_response(thinking_msg, result)
                
            elif intent_result['action'] == 'file_operation':
                await thinking_msg.edit_text(
                    f"🤖 **AI Agent**\n\n📁 {intent_result['description']}...",
                    parse_mode='Markdown'
                )
                await self.handle_file_operation(thinking_msg, intent_result)
                
            elif intent_result['action'] == 'help':
                await self.show_ai_help(thinking_msg)
                
            elif intent_result['action'] == 'conversation':
                # General AI conversation
                ai_response = await self.get_ai_response(user_message)
                await thinking_msg.edit_text(
                    f"🤖 **AI Agent Response**\n\n{ai_response}",
                    parse_mode='Markdown'
                )
            else:
                # Fallback response
                await thinking_msg.edit_text(
                    f"🤖 **AI Agent**\n\nI understand you said: \"{user_message}\"\n\nI can help with:\n• VPS commands (\"check disk space\", \"restart nginx\")\n• System monitoring (\"show system status\")\n• Docker management (\"list containers\")\n• File operations (\"show files in /var/www\")\n\nWhat would you like me to do?",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"AI Agent error: {e}")
            await update.message.reply_text(
                f"🤖 **AI Agent Error**\n\n❌ Sorry, I encountered an error: {str(e)}",
                parse_mode='Markdown'
            )
    
    async def analyze_user_intent(self, user_message: str) -> dict:
        """Analyze user intent and return action to take"""
        message_lower = user_message.lower()
        
        # VPS Command patterns
        command_patterns = {
            'disk space': 'df -h',
            'disk usage': 'df -h',
            'free space': 'df -h',
            'memory usage': 'free -h',
            'ram usage': 'free -h',
            'cpu usage': 'top -bn1 | head -20',
            'processes': 'ps aux --sort=-%cpu | head -15',
            'uptime': 'uptime',
            'who is logged': 'who',
            'network': 'ss -tuln | head -20',
            'restart nginx': 'sudo systemctl restart nginx',
            'restart apache': 'sudo systemctl restart apache2',
            'nginx status': 'systemctl status nginx',
            'apache status': 'systemctl status apache2',
        }
        
        # Check for direct command patterns
        for pattern, command in command_patterns.items():
            if pattern in message_lower:
                return {
                    'action': 'vps_command',
                    'command': command,
                    'pattern': pattern
                }
        
        # Check for system status requests
        status_keywords = ['status', 'health', 'system', 'server', 'vps']
        if any(keyword in message_lower for keyword in status_keywords):
            return {'action': 'vps_status'}
        
        # Check for Docker requests
        docker_keywords = ['docker', 'container', 'containers']
        if any(keyword in message_lower for keyword in docker_keywords):
            return {'action': 'docker_status'}
        
        # Check for file operations
        file_keywords = ['file', 'files', 'directory', 'folder', 'ls', 'list']
        if any(keyword in message_lower for keyword in file_keywords):
            # Extract path if mentioned
            path = '~'  # default
            if '/var/' in message_lower:
                path = '/var/www'
            elif '/home/' in message_lower:
                path = '/home'
            elif '/etc/' in message_lower:
                path = '/etc'
            
            return {
                'action': 'file_operation',
                'operation': 'list',
                'path': path,
                'description': f'Listing files in {path}'
            }
        
        # Check for help requests
        help_keywords = ['help', 'what can you do', 'commands', 'how']
        if any(keyword in message_lower for keyword in help_keywords):
            return {'action': 'help'}
        
        # If starts with a shell command, execute it directly
        shell_commands = ['ls', 'cat', 'grep', 'find', 'sudo', 'systemctl', 'docker', 'ps', 'top', 'htop']
        first_word = message_lower.split()[0] if message_lower.split() else ''
        if first_word in shell_commands:
            return {
                'action': 'vps_command',
                'command': user_message,
                'pattern': 'direct_command'
            }
        
        # Default to conversation
        return {'action': 'conversation'}
    
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
    
    async def format_command_response(self, message, command: str, result: dict):
        """Format command execution response for AI Agent"""
        try:
            if result["success"]:
                output = result["output"] if result["output"] else "(No output)"
                if len(output) > 3000:
                    output = output[:3000] + "\n\n... (truncated)"
                
                response_text = f"""
🤖 **AI Agent - Command Executed**

✅ Successfully ran: `{command}`

📋 **Result**:
```
{output}
```

🔄 **Time**: {datetime.now().strftime('%H:%M:%S')}
"""
            else:
                error = result["error"] if result["error"] else "Unknown error"
                if len(error) > 3000:
                    error = error[:3000] + "\n\n... (truncated)"
                
                response_text = f"""
🤖 **AI Agent - Command Failed**

❌ Failed to run: `{command}`

🚫 **Error**:
```
{error}
```

🔄 **Time**: {datetime.now().strftime('%H:%M:%S')}
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("💬 Ask AI Another Question", callback_data="ai_chat"),
                    InlineKeyboardButton("🖥️ VPS Control", callback_data="vps_control")
                ]
            ]
            
            await message.edit_text(
                response_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error formatting command response: {e}")
    
    async def show_ai_vps_status(self, message):
        """Show VPS status via AI Agent"""
        try:
            vps_stats = await self.vps_monitor.get_system_stats()
            
            if not vps_stats or not vps_stats.get("connected"):
                error_msg = vps_stats.get("error", "Connection failed") if vps_stats else "VPS not configured"
                status_text = f"""
🤖 **AI Agent - VPS Status**

🚨 **Connection Issue**: {error_msg}

🔧 I can help you troubleshoot VPS connection issues. Just ask!
"""
            else:
                cpu = vps_stats["cpu_percent"]
                memory = vps_stats["memory_percent"]
                disk = vps_stats["disk_percent"]
                
                status_emoji = "✅"
                if cpu > 80 or memory > 80 or disk > 90:
                    status_emoji = "⚠️"
                if cpu > 95 or memory > 95 or disk > 95:
                    status_emoji = "🚨"
                
                status_text = f"""
🤖 **AI Agent - VPS Status**

{status_emoji} **Overall Health**: {'Healthy' if status_emoji == '✅' else 'Needs Attention' if status_emoji == '⚠️' else 'Critical'}

📊 **Resource Usage**:
• CPU: {cpu:.1f}%
• Memory: {memory:.1f}% ({vps_stats['memory_used_gb']:.1f}GB / {vps_stats['memory_total_gb']:.1f}GB)
• Disk: {disk:.1f}%

⏰ **Uptime**: {vps_stats['uptime']}
🌐 **Host**: {self.vps_monitor.host}

💬 Ask me anything about your VPS!
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh Status", callback_data="ai_vps_refresh"),
                    InlineKeyboardButton("📊 More Details", callback_data="health_check")
                ]
            ]
            
            await message.edit_text(
                status_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"AI VPS status error: {e}")
            await message.edit_text(
                f"🤖 **AI Agent Error**\n\n❌ Cannot get VPS status: {str(e)}"
            )
    
    async def format_docker_response(self, message, result: dict):
        """Format Docker status response for AI Agent"""
        try:
            if result["success"]:
                output = result["output"][:2500]  # Limit for readability
                response_text = f"""
🤖 **AI Agent - Docker Status**

🐳 **Container Overview**:
```
{output}
```

💬 Need to manage containers? Just ask me!
Examples: "restart container X", "stop all containers"
"""
            else:
                response_text = f"""
🤖 **AI Agent - Docker Status**

❌ **Issue**: {result['error']}

🔧 **Possible Solutions**:
• Docker might not be installed
• Docker service might be stopped
• Permission issues

💬 Ask me to check or fix Docker issues!
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh Docker", callback_data="ai_docker_refresh"),
                    InlineKeyboardButton("🐳 Docker Control", callback_data="docker_management")
                ]
            ]
            
            await message.edit_text(
                response_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Docker response formatting error: {e}")
    
    async def handle_file_operation(self, message, intent_result: dict):
        """Handle file operations via AI Agent"""
        try:
            path = intent_result['path']
            result = await self.vps_monitor.get_directory_listing(path)
            
            if result["success"]:
                output = result["output"][:2500]
                response_text = f"""
🤖 **AI Agent - File Listing**

📂 **Directory**: `{path}`

```
{output}
```

💬 Need to read a file or navigate? Just tell me!
Examples: "read /etc/nginx.conf", "show files in /var/log"
"""
            else:
                response_text = f"""
🤖 **AI Agent - File Operation Failed**

❌ **Path**: `{path}`
**Error**: {result['error']}

💬 Try a different path or ask me for help!
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("📁 File Manager", callback_data="file_manager"),
                    InlineKeyboardButton("💬 Ask AI", callback_data="ai_chat")
                ]
            ]
            
            await message.edit_text(
                response_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"File operation error: {e}")
    
    async def show_ai_help(self, message):
        """Show AI Agent help"""
        help_text = f"""
🤖 **AI Agent - I'm Your VPS Assistant!**

🚀 **Just talk to me naturally! I understand:**

💻 **System Commands**:
• "check disk space" → Shows disk usage
• "what's the memory usage" → Shows RAM info
• "show running processes" → Lists processes
• "restart nginx" → Restarts nginx service

📊 **System Info**:
• "system status" → Full health overview
• "server health" → Resource monitoring
• "uptime" → How long server is running

🐳 **Docker Management**:
• "docker status" → List containers
• "containers" → Show running containers

📁 **File Operations**:
• "list files in /var/www" → Browse directory
• "show files" → List current directory

⚙️ **Direct Commands**:
• Just type any shell command: `ls -la`, `ps aux`, `df -h`

💬 **Or just ask me anything about your VPS!**

Host: `{self.vps_monitor.host or 'Not configured'}`
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🖥️ VPS Control Panel", callback_data="vps_control"),
                InlineKeyboardButton("📊 System Status", callback_data="show_status")
            ]
        ]
        
        await message.edit_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def get_ai_response(self, user_message: str) -> str:
        """Generate AI response for general conversation"""
        # Simple responses for now - can be enhanced with actual AI API later
        responses = {
            'hello': 'Hello! I\'m your VPS AI Agent. How can I help you manage your server today?',
            'hi': 'Hi there! Ready to help with your VPS management. What do you need?',
            'thanks': 'You\'re welcome! Let me know if you need anything else with your VPS.',
            'good': 'Glad to hear that! Is there anything else I can help you with?',
        }
        
        message_lower = user_message.lower()
        for key, response in responses.items():
            if key in message_lower:
                return response
        
        return f'I understand you said: "{user_message}"\n\nI\'m specialized in VPS management. Try asking me about system status, running commands, or checking Docker containers!'
    
    async def show_traditional_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show traditional button-based menu"""
        menu_text = """
📈 **Traditional Menu**

Classic button-based navigation:
"""
        
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
                InlineKeyboardButton("🔙 Back to AI Agent", callback_data="main_menu")
            ]
        ]
        
        await update.callback_query.edit_message_text(
            menu_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
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
            elif callback_data == "ai_vps_refresh":
                # AI Agent refresh VPS status
                thinking_msg = await update.callback_query.message.reply_text(
                    "🤖 **AI Agent**\n\n🔄 Refreshing VPS status...",
                    parse_mode='Markdown'
                )
                await self.show_ai_vps_status(thinking_msg)
            elif callback_data == "ai_docker_refresh":
                # AI Agent refresh Docker status
                thinking_msg = await update.callback_query.message.reply_text(
                    "🤖 **AI Agent**\n\n🐳 Refreshing Docker status...",
                    parse_mode='Markdown'
                )
                result = await self.vps_monitor.get_docker_status()
                await self.format_docker_response(thinking_msg, result)
            elif callback_data == "traditional_menu":
                await self.show_traditional_menu(update, context)
            elif callback_data == "ai_system_status":
                # AI Agent system status
                thinking_msg = await update.callback_query.message.reply_text(
                    "🤖 **UmbraSIL AI**\n\nLet me check your VPS system status...",
                    parse_mode='Markdown'
                )
                await self.show_ai_vps_status(thinking_msg)
            elif callback_data == "ai_docker_status":
                # AI Agent docker status
                thinking_msg = await update.callback_query.message.reply_text(
                    "🤖 **UmbraSIL AI**\n\nChecking your Docker containers...",
                    parse_mode='Markdown'
                )
                result = await self.vps_monitor.get_docker_status()
                await self.format_docker_response(thinking_msg, result)
            elif callback_data == "ai_clear_context":
                # Clear AI conversation context
                user_id = update.effective_user.id
                self.ai_agent.clear_context(user_id)
                await update.callback_query.answer("🧠 Conversation context cleared!", show_alert=True)
            
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
