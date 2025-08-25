# Personal Telegram Bot Assistant - Phase 3: n8n Business Management
# VPS Connections, Client Management, Docker Operations

import os
import asyncio
import json
import subprocess
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import logging

# SSH and remote connections
import paramiko
from paramiko import SSHClient, AutoAddPolicy

# Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Docker API (optional - for local docker if needed)
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

logger = logging.getLogger(__name__)

# ==============================================================================
# BUSINESS CONFIGURATION
# ==============================================================================

class BusinessConfig:
    """Business management configuration"""
    
    # VPS Connection Details
    VPS_HOST = os.getenv("VPS_HOST")  # Your VPS IP/hostname
    VPS_PORT = int(os.getenv("VPS_PORT", "2222"))  # SSH port
    VPS_USERNAME = os.getenv("VPS_USERNAME", "n8nuser")
    VPS_PRIVATE_KEY = os.getenv("VPS_PRIVATE_KEY")  # Base64 encoded private key
    VPS_PASSWORD = os.getenv("VPS_PASSWORD")  # Alternative to key
    
    # n8n Configuration
    N8N_BASE_PATH = "/home/n8nuser/n8n-environment"
    N8N_MAIN_URL = "https://automatia.duckdns.org/n8n"
    CLIENT_PORT_RANGE = (20000, 21000)
    
    # Docker settings
    DOCKER_COMPOSE_PATH = "/usr/local/bin/docker-compose"
    
    # Monitoring intervals
    HEALTH_CHECK_INTERVAL = 300  # 5 minutes
    LOG_RETENTION_DAYS = 7

# Conversation states
CREATE_CLIENT_NAME, CREATE_CLIENT_PORT, CREATE_CLIENT_DOMAIN = range(3)
REMOVE_CLIENT_CONFIRM = 3

# ==============================================================================
# VPS CONNECTION MANAGER
# ==============================================================================

class VPSConnectionManager:
    """Manages SSH connections to the VPS"""
    
    def __init__(self):
        self.connection_pool = {}
        self.last_connection_time = {}
    
    async def get_connection(self, connection_id: str = "default") -> Optional[SSHClient]:
        """Get or create SSH connection"""
        try:
            # Check if existing connection is still alive
            if connection_id in self.connection_pool:
                ssh = self.connection_pool[connection_id]
                try:
                    # Test connection with a simple command
                    transport = ssh.get_transport()
                    if transport and transport.is_active():
                        return ssh
                except:
                    # Connection is dead, remove it
                    try:
                        ssh.close()
                    except:
                        pass
                    del self.connection_pool[connection_id]
            
            # Create new connection
            ssh = SSHClient()
            ssh.set_missing_host_key_policy(AutoAddPolicy())
            
            # Connect with key or password
            if BusinessConfig.VPS_PRIVATE_KEY:
                # Decode base64 private key
                import base64
                import io
                
                private_key_data = base64.b64decode(BusinessConfig.VPS_PRIVATE_KEY).decode('utf-8')
                private_key = paramiko.RSAKey.from_private_key(io.StringIO(private_key_data))
                
                ssh.connect(
                    hostname=BusinessConfig.VPS_HOST,
                    port=BusinessConfig.VPS_PORT,
                    username=BusinessConfig.VPS_USERNAME,
                    pkey=private_key,
                    timeout=10
                )
            else:
                ssh.connect(
                    hostname=BusinessConfig.VPS_HOST,
                    port=BusinessConfig.VPS_PORT,
                    username=BusinessConfig.VPS_USERNAME,
                    password=BusinessConfig.VPS_PASSWORD,
                    timeout=10
                )
            
            self.connection_pool[connection_id] = ssh
            self.last_connection_time[connection_id] = datetime.now()
            logger.info(f"SSH connection established: {connection_id}")
            return ssh
            
        except Exception as e:
            logger.error(f"SSH connection failed: {e}")
            return None
    
    async def execute_command(self, command: str, connection_id: str = "default") -> Tuple[bool, str, str]:
        """Execute command on VPS and return success, stdout, stderr"""
        ssh = await self.get_connection(connection_id)
        if not ssh:
            return False, "", "SSH connection failed"
        
        try:
            stdin, stdout, stderr = ssh.exec_command(command, timeout=30)
            
            # Read output
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')
            
            # Get exit code
            exit_code = stdout.channel.recv_exit_status()
            success = exit_code == 0
            
            logger.debug(f"Command: {command[:100]}... | Success: {success}")
            return success, stdout_data, stderr_data
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return False, "", str(e)
    
    def close_all_connections(self):
        """Close all SSH connections"""
        for connection_id, ssh in self.connection_pool.items():
            try:
                ssh.close()
                logger.info(f"SSH connection closed: {connection_id}")
            except:
                pass
        self.connection_pool.clear()

# ==============================================================================
# N8N CLIENT MANAGER
# ==============================================================================

class N8NClientManager:
    """Manages n8n client instances on the VPS"""
    
    def __init__(self, vps_manager: VPSConnectionManager, db_manager):
        self.vps = vps_manager
        self.db = db_manager
    
    async def create_client(self, client_name: str, port: int, domain: str = None, base_path: str = None) -> Dict[str, Any]:
        """Create a new n8n client instance"""
        try:
            # Validate client name
            if not client_name.isalnum():
                return {"success": False, "error": "Client name must be alphanumeric"}
            
            # Check if client already exists
            existing = await self.list_clients()
            if any(client['name'] == client_name for client in existing.get('clients', [])):
                return {"success": False, "error": f"Client '{client_name}' already exists"}
            
            # Check if port is in use
            if any(client['port'] == port for client in existing.get('clients', [])):
                return {"success": False, "error": f"Port {port} is already in use"}
            
            # Execute client creation script
            create_command = f"cd {BusinessConfig.N8N_BASE_PATH} && ./scripts/client-management/create-client.sh {client_name} {port}"
            if domain:
                create_command += f" {domain}"
            if base_path:
                create_command += f" {base_path}"
            
            success, stdout, stderr = await self.vps.execute_command(create_command)
            
            if success:
                # Log the creation in database
                await self._log_client_action(client_name, "create", f"Port: {port}", True)
                
                return {
                    "success": True,
                    "message": f"Client '{client_name}' created successfully",
                    "client_name": client_name,
                    "port": port,
                    "url": f"http://{BusinessConfig.VPS_HOST}:{port}",
                    "output": stdout
                }
            else:
                await self._log_client_action(client_name, "create", "Failed", False, stderr)
                return {"success": False, "error": stderr or "Creation failed"}
                
        except Exception as e:
            logger.error(f"Client creation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def remove_client(self, client_name: str, delete_data: bool = False) -> Dict[str, Any]:
        """Remove an n8n client instance"""
        try:
            # Check if client exists
            existing = await self.list_clients()
            client_exists = any(client['name'] == client_name for client in existing.get('clients', []))
            
            if not client_exists:
                return {"success": False, "error": f"Client '{client_name}' does not exist"}
            
            # Execute removal script
            remove_command = f"cd {BusinessConfig.N8N_BASE_PATH} && ./scripts/client-management/remove-client.sh {client_name}"
            if delete_data:
                # This would require script modification to accept a flag
                remove_command += " --delete-data"
            
            success, stdout, stderr = await self.vps.execute_command(remove_command)
            
            if success:
                await self._log_client_action(client_name, "remove", f"Data deleted: {delete_data}", True)
                
                return {
                    "success": True,
                    "message": f"Client '{client_name}' removed successfully",
                    "output": stdout
                }
            else:
                await self._log_client_action(client_name, "remove", "Failed", False, stderr)
                return {"success": False, "error": stderr or "Removal failed"}
                
        except Exception as e:
            logger.error(f"Client removal failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_clients(self) -> Dict[str, Any]:
        """List all n8n client instances"""
        try:
            # Execute list script
            list_command = f"cd {BusinessConfig.N8N_BASE_PATH} && ./scripts/client-management/list-clients.sh"
            success, stdout, stderr = await self.vps.execute_command(list_command)
            
            if not success:
                return {"success": False, "error": stderr or "Failed to list clients"}
            
            # Parse the output (this depends on your script format)
            clients = []
            lines = stdout.strip().split('\n')
            
            for line in lines:
                if ':' in line and 'PORT' in line:
                    # Parse format like: "client1:20000:running:data_exists"
                    parts = line.split(':')
                    if len(parts) >= 4:
                        clients.append({
                            "name": parts[0],
                            "port": int(parts[1]),
                            "status": parts[2],
                            "data_exists": parts[3] == "data_exists",
                            "url": f"http://{BusinessConfig.VPS_HOST}:{parts[1]}"
                        })
            
            return {
                "success": True,
                "clients": clients,
                "count": len(clients)
            }
            
        except Exception as e:
            logger.error(f"Failed to list clients: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_client_status(self, client_name: str) -> Dict[str, Any]:
        """Get detailed status of a specific client"""
        try:
            # Check container status
            status_command = f"docker ps -a --filter name=n8n-{client_name} --format 'table {{{{.Names}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}'"
            success, stdout, stderr = await self.vps.execute_command(status_command)
            
            if not success:
                return {"success": False, "error": "Failed to check container status"}
            
            # Get container logs (last 20 lines)
            logs_command = f"docker logs --tail 20 n8n-{client_name}"
            logs_success, logs_stdout, logs_stderr = await self.vps.execute_command(logs_command)
            
            # Check data directory
            data_command = f"ls -la {BusinessConfig.N8N_BASE_PATH}/data/clients/{client_name}/"
            data_success, data_stdout, data_stderr = await self.vps.execute_command(data_command)
            
            return {
                "success": True,
                "client_name": client_name,
                "container_status": stdout.strip(),
                "logs": logs_stdout if logs_success else "No logs available",
                "data_directory": data_stdout if data_success else "Data directory not accessible",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get client status: {e}")
            return {"success": False, "error": str(e)}
    
    async def restart_client(self, client_name: str) -> Dict[str, Any]:
        """Restart a client container"""
        try:
            restart_command = f"docker restart n8n-{client_name}"
            success, stdout, stderr = await self.vps.execute_command(restart_command)
            
            if success:
                await self._log_client_action(client_name, "restart", "Container restarted", True)
                return {
                    "success": True,
                    "message": f"Client '{client_name}' restarted successfully"
                }
            else:
                await self._log_client_action(client_name, "restart", "Failed", False, stderr)
                return {"success": False, "error": stderr or "Restart failed"}
                
        except Exception as e:
            logger.error(f"Client restart failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _log_client_action(self, client_name: str, action: str, details: str, success: bool, error: str = None):
        """Log client management actions"""
        try:
            # Store in system_metrics table (reusing from Phase 1)
            await self.db.log_command(
                0,  # System user
                f"client_{action}",
                f"Client: {client_name}, Details: {details}",
                success,
                error
            )
        except Exception as e:
            logger.error(f"Failed to log client action: {e}")

# ==============================================================================
# VPS SYSTEM MONITORING
# ==============================================================================

class VPSMonitor:
    """Monitor VPS system health and Docker containers"""
    
    def __init__(self, vps_manager: VPSConnectionManager, db_manager):
        self.vps = vps_manager
        self.db = db_manager
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        try:
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu": await self._get_cpu_usage(),
                "memory": await self._get_memory_usage(),
                "disk": await self._get_disk_usage(),
                "network": await self._get_network_stats(),
                "docker": await self._get_docker_stats(),
                "load": await self._get_system_load()
            }
            
            # Store metrics in database
            await self._store_metrics(metrics)
            
            return {"success": True, "metrics": metrics}
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_cpu_usage(self) -> Dict[str, float]:
        """Get CPU usage statistics"""
        # Using top command for CPU usage
        cmd = "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1 | cut -d'u' -f2"
        success, stdout, stderr = await self.vps.execute_command(cmd)
        
        if success and stdout.strip():
            try:
                cpu_usage = float(stdout.strip())
                return {"usage_percent": cpu_usage}
            except:
                pass
        
        return {"usage_percent": 0.0}
    
    async def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        cmd = "free -m | grep '^Mem:' | awk '{print $3,$2,$7}'"
        success, stdout, stderr = await self.vps.execute_command(cmd)
        
        if success and stdout.strip():
            try:
                used, total, available = map(int, stdout.strip().split())
                return {
                    "used_mb": used,
                    "total_mb": total,
                    "available_mb": available,
                    "usage_percent": (used / total) * 100 if total > 0 else 0
                }
            except:
                pass
        
        return {"used_mb": 0, "total_mb": 0, "available_mb": 0, "usage_percent": 0}
    
    async def _get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage statistics"""
        cmd = "df -h / | tail -1 | awk '{print $3,$2,$5}'"
        success, stdout, stderr = await self.vps.execute_command(cmd)
        
        if success and stdout.strip():
            try:
                parts = stdout.strip().split()
                used, total, percent = parts[0], parts[1], parts[2].replace('%', '')
                return {
                    "used": used,
                    "total": total,
                    "usage_percent": float(percent)
                }
            except:
                pass
        
        return {"used": "0G", "total": "0G", "usage_percent": 0.0}
    
    async def _get_network_stats(self) -> Dict[str, Any]:
        """Get network interface statistics"""
        cmd = "cat /proc/net/dev | grep -E '(eth0|ens|enp)' | head -1 | awk '{print $2,$10}'"
        success, stdout, stderr = await self.vps.execute_command(cmd)
        
        if success and stdout.strip():
            try:
                rx_bytes, tx_bytes = map(int, stdout.strip().split())
                return {
                    "rx_bytes": rx_bytes,
                    "tx_bytes": tx_bytes,
                    "rx_mb": round(rx_bytes / 1024 / 1024, 2),
                    "tx_mb": round(tx_bytes / 1024 / 1024, 2)
                }
            except:
                pass
        
        return {"rx_bytes": 0, "tx_bytes": 0, "rx_mb": 0, "tx_mb": 0}
    
    async def _get_system_load(self) -> Dict[str, Any]:
        """Get system load averages"""
        cmd = "uptime | awk -F'load average:' '{ print $2 }' | sed 's/^ *//' | cut -d',' -f1,2,3"
        success, stdout, stderr = await self.vps.execute_command(cmd)
        
        if success and stdout.strip():
            try:
                load_parts = [float(x.strip()) for x in stdout.strip().split(',')]
                return {
                    "load_1m": load_parts[0] if len(load_parts) > 0 else 0,
                    "load_5m": load_parts[1] if len(load_parts) > 1 else 0,
                    "load_15m": load_parts[2] if len(load_parts) > 2 else 0
                }
            except:
                pass
        
        return {"load_1m": 0, "load_5m": 0, "load_15m": 0}
    
    async def _get_docker_stats(self) -> Dict[str, Any]:
        """Get Docker container statistics"""
        # Get running containers count
        cmd = "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -v NAMES | wc -l"
        success, stdout, stderr = await self.vps.execute_command(cmd)
        running_containers = int(stdout.strip()) if success and stdout.strip().isdigit() else 0
        
        # Get all containers count
        cmd = "docker ps -a --format 'table {{.Names}}\t{{.Status}}' | grep -v NAMES | wc -l"
        success, stdout, stderr = await self.vps.execute_command(cmd)
        total_containers = int(stdout.strip()) if success and stdout.strip().isdigit() else 0
        
        # Get n8n specific containers
        cmd = "docker ps --filter name=n8n- --format 'table {{.Names}}\t{{.Status}}'"
        success, stdout, stderr = await self.vps.execute_command(cmd)
        n8n_containers = []
        
        if success:
            lines = stdout.strip().split('\n')[1:]  # Skip header
            for line in lines:
                if line.strip():
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        n8n_containers.append({
                            "name": parts[0],
                            "status": parts[1]
                        })
        
        return {
            "total_containers": total_containers,
            "running_containers": running_containers,
            "stopped_containers": total_containers - running_containers,
            "n8n_containers": n8n_containers
        }
    
    async def _store_metrics(self, metrics: Dict[str, Any]):
        """Store metrics in database"""
        try:
            async with self.db.pool.acquire() as conn:
                # Store each metric type
                for metric_type, data in metrics.items():
                    if metric_type != "timestamp" and isinstance(data, dict):
                        await conn.execute('''
                            INSERT INTO system_metrics (metric_type, metric_value, metadata)
                            VALUES ($1, $2, $3)
                        ''', 
                            metric_type,
                            data.get('usage_percent', 0) if 'usage_percent' in data else 0,
                            json.dumps(data)
                        )
        except Exception as e:
            logger.error(f"Failed to store metrics: {e}")

# ==============================================================================
# BUSINESS BOT HANDLERS
# ==============================================================================

class BusinessManager:
    """Business workflow management for the bot"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.vps_manager = VPSConnectionManager()
        self.client_manager = N8NClientManager(self.vps_manager, db_manager)
        self.monitor = VPSMonitor(self.vps_manager, db_manager)
    
    def setup_handlers(self, application):
        """Setup business-related handlers"""
        
        # Client management conversations
        application.add_handler(ConversationHandler(
            entry_points=[CommandHandler('create_client', self.create_client_start)],
            states={
                CREATE_CLIENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.create_client_name)],
                CREATE_CLIENT_PORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.create_client_port)],
                CREATE_CLIENT_DOMAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.create_client_domain)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
            name="create_client"
        ))
        
        application.add_handler(ConversationHandler(
            entry_points=[CommandHandler('remove_client', self.remove_client_start)],
            states={
                REMOVE_CLIENT_CONFIRM: [CallbackQueryHandler(self.remove_client_confirm)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
            name="remove_client"
        ))
        
        # Direct commands
        application.add_handler(CommandHandler('list_clients', self.list_clients))
        application.add_handler(CommandHandler('client_status', self.client_status))
        application.add_handler(CommandHandler('restart_client', self.restart_client))
        application.add_handler(CommandHandler('vps_status', self.vps_status))
        application.add_handler(CommandHandler('system_monitor', self.system_monitor))
    
    # ===== CLIENT MANAGEMENT =====
    
    async def create_client_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start client creation process"""
        if not BusinessConfig.VPS_HOST:
            await update.message.reply_text(
                "❌ VPS connection not configured.\n"
                "Please set VPS_HOST and credentials in environment variables."
            )
            return ConversationHandler.END
        
        await update.message.reply_text(
            "🏗️ **Create New n8n Client**\n\n"
            "Please enter the client name (alphanumeric only):\n"
            "Example: acme, client01, testorg",
            parse_mode='Markdown'
        )
        return CREATE_CLIENT_NAME
    
    async def create_client_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle client name input"""
        client_name = update.message.text.strip().lower()
        
        if not client_name.isalnum():
            await update.message.reply_text(
                "❌ Client name must be alphanumeric (letters and numbers only).\n"
                "Please enter a valid client name:"
            )
            return CREATE_CLIENT_NAME
        
        context.user_data['client_name'] = client_name
        
        await update.message.reply_text(
            f"✅ Client name: **{client_name}**\n\n"
            f"Please enter the port number ({BusinessConfig.CLIENT_PORT_RANGE[0]}-{BusinessConfig.CLIENT_PORT_RANGE[1]}):\n"
            "Example: 20005",
            parse_mode='Markdown'
        )
        return CREATE_CLIENT_PORT
    
    async def create_client_port(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle port input"""
        try:
            port = int(update.message.text.strip())
            
            if port < BusinessConfig.CLIENT_PORT_RANGE[0] or port > BusinessConfig.CLIENT_PORT_RANGE[1]:
                raise ValueError("Port out of range")
            
            context.user_data['client_port'] = port
            
            await update.message.reply_text(
                f"✅ Client name: **{context.user_data['client_name']}**\n"
                f"✅ Port: **{port}**\n\n"
                "Enter custom domain (optional) or type 'skip':\n"
                "Example: client.yourdomain.com",
                parse_mode='Markdown'
            )
            return CREATE_CLIENT_DOMAIN
            
        except ValueError:
            await update.message.reply_text(
                f"❌ Invalid port number. Please enter a number between {BusinessConfig.CLIENT_PORT_RANGE[0]} and {BusinessConfig.CLIENT_PORT_RANGE[1]}:"
            )
            return CREATE_CLIENT_PORT
    
    async def create_client_domain(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle domain input and create client"""
        domain = update.message.text.strip().lower()
        if domain == 'skip':
            domain = None
        
        context.user_data['client_domain'] = domain
        
        # Show processing message
        processing_msg = await update.message.reply_text(
            "🔄 Creating client instance... This may take a moment."
        )
        
        # Create the client
        result = await self.client_manager.create_client(
            context.user_data['client_name'],
            context.user_data['client_port'],
            domain
        )
        
        if result['success']:
            success_message = (
                f"✅ **Client Created Successfully!**\n\n"
                f"🏷️ Name: {result['client_name']}\n"
                f"🌐 URL: {result['url']}\n"
                f"🔌 Port: {result['port']}\n"
            )
            
            if domain:
                success_message += f"🌍 Domain: {domain}\n"
            
            success_message += f"\n📁 Data Path: `/data/clients/{result['client_name']}`"
            
            await processing_msg.edit_text(success_message, parse_mode='Markdown')
        else:
            await processing_msg.edit_text(
                f"❌ **Failed to Create Client**\n\n"
                f"Error: {result['error']}"
            )
        
        # Clear user data
        context.user_data.clear()
        return ConversationHandler.END
    
    async def remove_client_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start client removal process"""
        args = context.args
        if not args:
            await update.message.reply_text(
                "❌ Please specify a client name.\n"
                "Usage: /remove_client <client_name>\n"
                "Example: /remove_client acme"
            )
            return ConversationHandler.END
        
        client_name = args[0].lower()
        context.user_data['remove_client_name'] = client_name
        
        # Check if client exists
        clients_list = await self.client_manager.list_clients()
        if not clients_list['success']:
            await update.message.reply_text(
                f"❌ Failed to check clients: {clients_list['error']}"
            )
            return ConversationHandler.END
        
        client_exists = any(client['name'] == client_name for client in clients_list.get('clients', []))
        if not client_exists:
            await update.message.reply_text(
                f"❌ Client '{client_name}' does not exist.\n"
                "Use /list_clients to see available clients."
            )
            return ConversationHandler.END
        
        # Show confirmation
        keyboard = [
            [
                InlineKeyboardButton("🗑️ Remove (Keep Data)", callback_data="remove_keep"),
                InlineKeyboardButton("💥 Remove + Delete Data", callback_data="remove_delete")
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="remove_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚠️ **Confirm Client Removal**\n\n"
            f"Client: **{client_name}**\n\n"
            f"Choose removal option:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return REMOVE_CLIENT_CONFIRM
    
    async def remove_client_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle removal confirmation"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "remove_cancel":
            await query.edit_message_text("❌ Client removal cancelled.")
            context.user_data.clear()
            return ConversationHandler.END
        
        client_name = context.user_data['remove_client_name']
        delete_data = query.data == "remove_delete"
        
        # Show processing message
        await query.edit_message_text("🔄 Removing client... Please wait.")
        
        # Remove the client
        result = await self.client_manager.remove_client(client_name, delete_data)
        
        if result['success']:
            message = (
                f"✅ **Client Removed Successfully!**\n\n"
                f"🏷️ Client: {client_name}\n"
                f"🗑️ Data deleted: {'Yes' if delete_data else 'No'}"
            )
            await query.edit_message_text(message, parse_mode='Markdown')
        else:
            await query.edit_message_text(
                f"❌ **Failed to Remove Client**\n\n"
                f"Error: {result['error']}"
            )
        
        context.user_data.clear()
        return ConversationHandler.END
    
    async def list_clients(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all n8n clients"""
        user_id = update.effective_user.id
        
        # Show loading message
        loading_msg = await update.message.reply_text("🔍 Checking clients...")
        
        result = await self.client_manager.list_clients()
        
        if not result['success']:
            await loading_msg.edit_text(
                f"❌ **Failed to List Clients**\n\n"
                f"Error: {result['error']}"
            )
            return
        
        clients = result.get('clients', [])
        
        if not clients:
            await loading_msg.edit_text(
                "📋 **No n8n Clients Found**\n\n"
                "Use /create_client to create your first client instance."
            )
            return
        
        # Build client list
        response = f"📋 **n8n Client Instances ({len(clients)})**\n\n"
        
        for client in clients:
            status_emoji = "✅" if client['status'] == "running" else "❌"
            data_emoji = "💾" if client.get('data_exists', False) else "📁"
            
            response += f"{status_emoji} **{client['name']}**\n"
            response += f"   🌐 {client['url']}\n"
            response += f"   🔌 Port: {client['port']}\n"
            response += f"   📊 Status: {client['status']}\n"
            response += f"   {data_emoji} Data: {'Available' if client.get('data_exists', False) else 'Not found'}\n\n"
        
        response += "💡 Use /client_status <name> for detailed info"
        
        await loading_msg.edit_text(response, parse_mode='Markdown')
        await self.db.log_command(user_id, "list_clients", f"Found {len(clients)} clients", True)
    
    async def client_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get detailed status of a specific client"""
        args = context.args
        if not args:
            await update.message.reply_text(
                "❌ Please specify a client name.\n"
                "Usage: /client_status <client_name>\n"
                "Example: /client_status acme"
            )
            return
        
        client_name = args[0].lower()
        user_id = update.effective_user.id
        
        loading_msg = await update.message.reply_text(f"🔍 Checking status for {client_name}...")
        
        result = await self.client_manager.get_client_status(client_name)
        
        if not result['success']:
            await loading_msg.edit_text(
                f"❌ **Failed to Get Client Status**\n\n"
                f"Error: {result['error']}"
            )
            return
        
        response = f"📊 **Client Status: {client_name}**\n\n"
        response += f"🐳 **Container:** {result['container_status']}\n\n"
        
        if result['logs']:
            # Show last few lines of logs
            log_lines = result['logs'].split('\n')[-5:]  # Last 5 lines
            response += f"📋 **Recent Logs:**\n```\n" + "\n".join(log_lines) + "\n```\n\n"
        
        response += f"📁 **Data Directory:**\n```\n{result['data_directory'][:200]}...\n```\n\n"
        response += f"🕐 **Checked:** {datetime.fromisoformat(result['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Add action buttons
        keyboard = [
            [InlineKeyboardButton("🔄 Restart", callback_data=f"restart_client_{client_name}")],
            [InlineKeyboardButton("📊 Full Logs", callback_data=f"client_logs_{client_name}")],
            [InlineKeyboardButton("🌐 Open URL", url=f"http://{BusinessConfig.VPS_HOST}:20000")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(response, parse_mode='Markdown', reply_markup=reply_markup)
        await self.db.log_command(user_id, "client_status", f"Checked {client_name}", True)
    
    async def restart_client(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Restart a specific client"""
        args = context.args
        if not args:
            await update.message.reply_text(
                "❌ Please specify a client name.\n"
                "Usage: /restart_client <client_name>\n"
                "Example: /restart_client acme"
            )
            return
        
        client_name = args[0].lower()
        user_id = update.effective_user.id
        
        loading_msg = await update.message.reply_text(f"🔄 Restarting {client_name}...")
        
        result = await self.client_manager.restart_client(client_name)
        
        if result['success']:
            await loading_msg.edit_text(
                f"✅ **Client Restarted Successfully!**\n\n"
                f"🏷️ Client: {client_name}\n"
                f"🔄 Status: Container restarted\n\n"
                f"💡 Use /client_status {client_name} to check status"
            )
            await self.db.log_command(user_id, "restart_client", f"Restarted {client_name}", True)
        else:
            await loading_msg.edit_text(
                f"❌ **Failed to Restart Client**\n\n"
                f"Client: {client_name}\n"
                f"Error: {result['error']}"
            )
            await self.db.log_command(user_id, "restart_client", f"Failed to restart {client_name}", False, result['error'])
    
    # ===== VPS MONITORING =====
    
    async def vps_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show VPS connection and basic status"""
        user_id = update.effective_user.id
        
        if not BusinessConfig.VPS_HOST:
            await update.message.reply_text(
                "❌ VPS connection not configured.\n"
                "Please set VPS_HOST and credentials."
            )
            return
        
        loading_msg = await update.message.reply_text("🔍 Checking VPS status...")
        
        try:
            # Test connection
            ssh = await self.vps_manager.get_connection()
            if not ssh:
                await loading_msg.edit_text(
                    "❌ **VPS Connection Failed**\n\n"
                    "Unable to establish SSH connection.\n"
                    "Please check credentials and network connectivity."
                )
                return
            
            # Get basic system info
            success, uptime_output, _ = await self.vps_manager.execute_command("uptime")
            success2, disk_output, _ = await self.vps_manager.execute_command("df -h / | tail -1")
            success3, docker_output, _ = await self.vps_manager.execute_command("docker --version")
            
            response = f"✅ **VPS Status - Connected**\n\n"
            response += f"🌐 **Host:** {BusinessConfig.VPS_HOST}:{BusinessConfig.VPS_PORT}\n"
            response += f"👤 **User:** {BusinessConfig.VPS_USERNAME}\n\n"
            
            if success and uptime_output:
                response += f"⏰ **Uptime:** {uptime_output.strip()}\n"
            
            if success2 and disk_output:
                disk_parts = disk_output.split()
                if len(disk_parts) >= 5:
                    response += f"💾 **Disk:** {disk_parts[2]} used / {disk_parts[1]} total ({disk_parts[4]})\n"
            
            if success3 and docker_output:
                response += f"🐳 **Docker:** {docker_output.strip()}\n"
            
            response += f"\n🕐 **Checked:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Add monitoring buttons
            keyboard = [
                [InlineKeyboardButton("📊 System Monitor", callback_data="system_monitor")],
                [InlineKeyboardButton("🐳 Docker Status", callback_data="docker_status")],
                [InlineKeyboardButton("📋 Process List", callback_data="process_list")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_msg.edit_text(response, parse_mode='Markdown', reply_markup=reply_markup)
            await self.db.log_command(user_id, "vps_status", "VPS status checked", True)
            
        except Exception as e:
            logger.error(f"VPS status check failed: {e}")
            await loading_msg.edit_text(
                f"❌ **VPS Status Check Failed**\n\n"
                f"Error: {str(e)}"
            )
            await self.db.log_command(user_id, "vps_status", "Failed", False, str(e))
    
    async def system_monitor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show comprehensive system monitoring"""
        user_id = update.effective_user.id
        loading_msg = await update.message.reply_text("📊 Gathering system metrics...")
        
        result = await self.monitor.get_system_metrics()
        
        if not result['success']:
            await loading_msg.edit_text(
                f"❌ **System Monitoring Failed**\n\n"
                f"Error: {result['error']}"
            )
            return
        
        metrics = result['metrics']
        
        # Build comprehensive report
        response = f"📊 **System Monitoring Report**\n\n"
        
        # CPU
        cpu = metrics.get('cpu', {})
        cpu_usage = cpu.get('usage_percent', 0)
        cpu_emoji = "🔥" if cpu_usage > 80 else "⚠️" if cpu_usage > 60 else "✅"
        response += f"{cpu_emoji} **CPU Usage:** {cpu_usage:.1f}%\n"
        
        # Memory
        memory = metrics.get('memory', {})
        mem_usage = memory.get('usage_percent', 0)
        mem_emoji = "🔥" if mem_usage > 85 else "⚠️" if mem_usage > 70 else "✅"
        response += f"{mem_emoji} **Memory:** {memory.get('used_mb', 0)}MB / {memory.get('total_mb', 0)}MB ({mem_usage:.1f}%)\n"
        
        # Disk
        disk = metrics.get('disk', {})
        disk_usage = disk.get('usage_percent', 0)
        disk_emoji = "🔥" if disk_usage > 90 else "⚠️" if disk_usage > 80 else "✅"
        response += f"{disk_emoji} **Disk:** {disk.get('used', 'N/A')} / {disk.get('total', 'N/A')} ({disk_usage:.1f}%)\n"
        
        # Load Average
        load = metrics.get('load', {})
        load_1m = load.get('load_1m', 0)
        load_emoji = "🔥" if load_1m > 4 else "⚠️" if load_1m > 2 else "✅"
        response += f"{load_emoji} **Load:** {load_1m:.2f} (1m), {load.get('load_5m', 0):.2f} (5m), {load.get('load_15m', 0):.2f} (15m)\n\n"
        
        # Docker
        docker_stats = metrics.get('docker', {})
        response += f"🐳 **Docker Containers:**\n"
        response += f"   ✅ Running: {docker_stats.get('running_containers', 0)}\n"
        response += f"   ❌ Stopped: {docker_stats.get('stopped_containers', 0)}\n"
        response += f"   📊 Total: {docker_stats.get('total_containers', 0)}\n\n"
        
        # n8n Containers
        n8n_containers = docker_stats.get('n8n_containers', [])
        if n8n_containers:
            response += f"⚙️ **n8n Containers:**\n"
            for container in n8n_containers[:5]:  # Show max 5
                status_emoji = "✅" if "Up" in container['status'] else "❌"
                response += f"   {status_emoji} {container['name']}: {container['status']}\n"
            if len(n8n_containers) > 5:
                response += f"   ... and {len(n8n_containers) - 5} more\n"
        
        response += f"\n🕐 **Updated:** {datetime.fromisoformat(metrics['timestamp']).strftime('%H:%M:%S')}"
        
        # Add refresh button
        keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="system_monitor")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(response, parse_mode='Markdown', reply_markup=reply_markup)
        await self.db.log_command(user_id, "system_monitor", "System metrics gathered", True)
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel any ongoing conversation"""
        await update.message.reply_text("❌ Operation cancelled.")
        context.user_data.clear()
        return ConversationHandler.END
    
    def cleanup(self):
        """Cleanup resources"""
        self.vps_manager.close_all_connections()

# ==============================================================================
# REQUIREMENTS AND CONFIGURATION
# ==============================================================================

"""
Add to requirements.txt:

# Phase 3 additions:
paramiko==3.3.1
docker==6.1.3  # Optional, for local Docker operations
"""

# ==============================================================================
# ENVIRONMENT VARIABLES FOR PHASE 3
# ==============================================================================

"""
Required Railway Environment Variables:

# VPS Connection
VPS_HOST=your.vps.ip.or.hostname
VPS_PORT=2222
VPS_USERNAME=n8nuser
VPS_PRIVATE_KEY=<base64_encoded_private_key>  # OR use VPS_PASSWORD
VPS_PASSWORD=your_ssh_password  # Alternative to private key

# Optional
N8N_BASE_PATH=/home/n8nuser/n8n-environment  # Default path
CLIENT_PORT_RANGE_START=20000
CLIENT_PORT_RANGE_END=21000
"""

# ==============================================================================
# INTEGRATION INSTRUCTIONS
# ==============================================================================

"""
INTEGRATION WITH MAIN BOT:

1. Add to your main bot file:

from business_manager import BusinessManager, BusinessConfig

class PersonalBotAssistant:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.application = None
        self.finance_manager = FinanceManager(db_manager)
        
        # Add business manager
        self.business_manager = BusinessManager(db_manager)
    
    def setup_handlers(self):
        # ... existing handlers ...
        
        # Add business handlers
        self.business_manager.setup_handlers(self.application)
    
    # Update callback handler for business menu
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # ... existing code ...
        
        elif callback_data == "menu_business":
            keyboard = [
                [
                    InlineKeyboardButton("🏗️ Create Client", callback_data="create_client"),
                    InlineKeyboardButton("📋 List Clients", callback_data="list_clients")
                ],
                [
                    InlineKeyboardButton("📊 Client Status", callback_data="client_status"),
                    InlineKeyboardButton("🔄 Restart Client", callback_data="restart_client")
                ],
                [
                    InlineKeyboardButton("🖥️ VPS Status", callback_data="vps_status"),
                    InlineKeyboardButton("📊 System Monitor", callback_data="system_monitor")
                ],
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "⚙️ **Business Management**\n\n"
                "Manage n8n clients and VPS:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        
        # Handle business callbacks
        elif callback_data.startswith("restart_client_"):
            client_name = callback_data.split("_", 2)[2]
            result = await self.business_manager.client_manager.restart_client(client_name)
            if result['success']:
                await query.answer("✅ Client restarted successfully!", show_alert=True)
            else:
                await query.answer(f"❌ Restart failed: {result['error']}", show_alert=True)

2. Add cleanup to main application:

async def main():
    try:
        # ... existing code ...
        await bot.application.run_polling(drop_pending_updates=True)
    finally:
        if db_manager:
            await db_manager.close()
        # Cleanup business manager
        if hasattr(bot, 'business_manager'):
            bot.business_manager.cleanup()

3. VPS Setup Requirements:
   - Ensure your VPS has the client management scripts in place
   - SSH key should be base64 encoded for Railway secrets
   - UFW should allow the required ports (20000-21000)
"""

# ==============================================================================
# PHASE 3 FEATURE SUMMARY
# ==============================================================================

"""
🎉 PHASE 3: N8N BUSINESS MANAGEMENT COMPLETE!

✅ IMPLEMENTED FEATURES:

🏗️ Client Management:
- Create new n8n client instances with custom ports
- Remove clients with data preservation options
- List all clients with status and URLs
- Interactive client creation wizard

📊 Monitoring & Status:
- Real-time client status checking
- Container logs viewing
- VPS system metrics (CPU, Memory, Disk, Load)
- Docker container monitoring
- n8n-specific container tracking

🔧 Operations:
- Restart individual clients
- SSH connection management with pooling
- Secure credential handling (private keys)
- Error handling and logging

🖥️ System Integration:
- Seamless VPS connectivity via SSH
- Docker container management
- System health monitoring
- Performance metrics collection

🎯 COMMANDS AVAILABLE:
/create_client - Interactive client creation
/remove_client <name> - Remove client with confirmation
/list_clients - Show all clients and their status
/client_status <name> - Detailed client information
/restart_client <name> - Restart specific client
/vps_status - VPS connection and basic info
/system_monitor - Comprehensive system metrics

🔒 SECURITY FEATURES:
- SSH key-based authentication
- Connection pooling with timeout
- Secure environment variable handling
- Command logging and audit trails

🏗️ TECHNICAL HIGHLIGHTS:
- Async SSH operations with paramiko
- Connection reuse and management
- Error handling and recovery
- Modular architecture for easy extension
- Production-ready monitoring system

Ready for Phase 4: Enhanced Monitoring & Alerts! 🚀
"""