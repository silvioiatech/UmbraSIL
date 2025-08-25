# Personal Telegram Bot Assistant - Phase 4: Monitoring & Alerts
# Advanced System Monitoring, Configurable Alerts, Health Reports

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Scheduling and background tasks
import schedule
import threading
from concurrent.futures import ThreadPoolExecutor

# Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

logger = logging.getLogger(__name__)

# ==============================================================================
# MONITORING CONFIGURATION & MODELS
# ==============================================================================

class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"

@dataclass
class AlertRule:
    """Definition of an alert rule"""
    id: str
    name: str
    metric_type: str
    condition: str  # "gt", "lt", "eq"
    threshold: float
    severity: AlertSeverity
    enabled: bool = True
    cooldown_minutes: int = 15
    description: str = ""

@dataclass
class Alert:
    """Active alert instance"""
    id: str
    rule_id: str
    message: str
    severity: AlertSeverity
    status: AlertStatus
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metric_value: float = 0.0
    metadata: Dict[str, Any] = None

class MonitoringConfig:
    """Monitoring and alerts configuration"""
    
    # Collection intervals (seconds)
    METRICS_COLLECTION_INTERVAL = 300  # 5 minutes
    HEALTH_CHECK_INTERVAL = 600        # 10 minutes
    ALERT_CHECK_INTERVAL = 60          # 1 minute
    
    # Data retention
    METRICS_RETENTION_DAYS = 30
    ALERTS_RETENTION_DAYS = 90
    
    # Default alert rules
    DEFAULT_ALERT_RULES = [
        AlertRule("cpu_high", "High CPU Usage", "cpu", "gt", 80.0, AlertSeverity.HIGH, True, 15, "CPU usage above 80%"),
        AlertRule("cpu_critical", "Critical CPU Usage", "cpu", "gt", 95.0, AlertSeverity.CRITICAL, True, 5, "CPU usage above 95%"),
        AlertRule("memory_high", "High Memory Usage", "memory", "gt", 85.0, AlertSeverity.HIGH, True, 15, "Memory usage above 85%"),
        AlertRule("memory_critical", "Critical Memory Usage", "memory", "gt", 95.0, AlertSeverity.CRITICAL, True, 5, "Memory usage above 95%"),
        AlertRule("disk_high", "High Disk Usage", "disk", "gt", 85.0, AlertSeverity.HIGH, True, 30, "Disk usage above 85%"),
        AlertRule("disk_critical", "Critical Disk Usage", "disk", "gt", 95.0, AlertSeverity.CRITICAL, True, 10, "Disk usage above 95%"),
        AlertRule("load_high", "High System Load", "load", "gt", 4.0, AlertSeverity.MEDIUM, True, 20, "System load above 4.0"),
        AlertRule("container_down", "Container Down", "docker", "lt", 1.0, AlertSeverity.HIGH, True, 5, "Required container not running"),
    ]
    
    # Notification settings
    DAILY_REPORT_TIME = "08:00"  # Daily health report time
    WEEKLY_REPORT_DAY = 1        # Monday = 1
    
    # Health thresholds for reports
    HEALTH_THRESHOLDS = {
        "cpu": {"good": 60, "warning": 80, "critical": 95},
        "memory": {"good": 70, "warning": 85, "critical": 95},
        "disk": {"good": 70, "warning": 85, "critical": 95},
        "load": {"good": 2.0, "warning": 4.0, "critical": 8.0}
    }

# ==============================================================================
# DATABASE EXTENSIONS FOR PHASE 4
# ==============================================================================

class MonitoringDatabase:
    """Database operations for monitoring and alerts"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    async def initialize_monitoring_tables(self):
        """Create monitoring-specific tables"""
        async with self.db.pool.acquire() as conn:
            # Alert rules table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS alert_rules (
                    id VARCHAR(100) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    metric_type VARCHAR(50) NOT NULL,
                    condition VARCHAR(10) NOT NULL,
                    threshold FLOAT NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    cooldown_minutes INTEGER DEFAULT 15,
                    description TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            # Active alerts table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id VARCHAR(100) PRIMARY KEY,
                    rule_id VARCHAR(100) NOT NULL,
                    message TEXT NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    acknowledged_at TIMESTAMP WITH TIME ZONE,
                    resolved_at TIMESTAMP WITH TIME ZONE,
                    metric_value FLOAT DEFAULT 0.0,
                    metadata JSONB,
                    FOREIGN KEY (rule_id) REFERENCES alert_rules(id)
                )
            ''')
            
            # Health reports table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS health_reports (
                    id SERIAL PRIMARY KEY,
                    report_type VARCHAR(50) NOT NULL,
                    health_score FLOAT NOT NULL,
                    metrics_summary JSONB,
                    alerts_summary JSONB,
                    recommendations TEXT[],
                    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            logger.info("Monitoring tables created/verified")
    
    async def save_alert_rule(self, rule: AlertRule):
        """Save or update an alert rule"""
        async with self.db.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO alert_rules (id, name, metric_type, condition, threshold, severity, 
                                       enabled, cooldown_minutes, description, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    name = $2, metric_type = $3, condition = $4, threshold = $5,
                    severity = $6, enabled = $7, cooldown_minutes = $8, description = $9,
                    updated_at = NOW()
            ''', rule.id, rule.name, rule.metric_type, rule.condition, rule.threshold,
                rule.severity.value, rule.enabled, rule.cooldown_minutes, rule.description)
    
    async def get_alert_rules(self) -> List[AlertRule]:
        """Get all alert rules"""
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch('SELECT * FROM alert_rules ORDER BY name')
            return [
                AlertRule(
                    id=row['id'],
                    name=row['name'],
                    metric_type=row['metric_type'],
                    condition=row['condition'],
                    threshold=row['threshold'],
                    severity=AlertSeverity(row['severity']),
                    enabled=row['enabled'],
                    cooldown_minutes=row['cooldown_minutes'],
                    description=row['description'] or ""
                )
                for row in rows
            ]
    
    async def create_alert(self, alert: Alert):
        """Create a new alert"""
        async with self.db.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO alerts (id, rule_id, message, severity, status, triggered_at, 
                                  metric_value, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ''', alert.id, alert.rule_id, alert.message, alert.severity.value,
                alert.status.value, alert.triggered_at, alert.metric_value, 
                json.dumps(alert.metadata) if alert.metadata else None)
    
    async def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM alerts 
                WHERE status = 'active' 
                ORDER BY triggered_at DESC
            ''')
            return [self._row_to_alert(row) for row in rows]
    
    async def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert"""
        async with self.db.pool.acquire() as conn:
            await conn.execute('''
                UPDATE alerts 
                SET status = 'acknowledged', acknowledged_at = NOW() 
                WHERE id = $1
            ''', alert_id)
    
    async def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        async with self.db.pool.acquire() as conn:
            await conn.execute('''
                UPDATE alerts 
                SET status = 'resolved', resolved_at = NOW() 
                WHERE id = $1
            ''', alert_id)
    
    async def get_metrics_history(self, metric_type: str, hours: int = 24) -> List[Dict]:
        """Get metrics history for a specific time period"""
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM system_metrics 
                WHERE metric_type = $1 
                AND timestamp > NOW() - INTERVAL '%s hours'
                ORDER BY timestamp DESC
            ''', metric_type, hours)
            
            return [
                {
                    "timestamp": row['timestamp'],
                    "value": row['metric_value'],
                    "metadata": json.loads(row['metadata']) if row['metadata'] else {}
                }
                for row in rows
            ]
    
    async def save_health_report(self, report_type: str, health_score: float, 
                               metrics_summary: Dict, alerts_summary: Dict, 
                               recommendations: List[str]):
        """Save a health report"""
        async with self.db.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO health_reports (report_type, health_score, metrics_summary, 
                                          alerts_summary, recommendations)
                VALUES ($1, $2, $3, $4, $5)
            ''', report_type, health_score, json.dumps(metrics_summary), 
                json.dumps(alerts_summary), recommendations)
    
    async def cleanup_old_data(self):
        """Clean up old monitoring data"""
        async with self.db.pool.acquire() as conn:
            # Clean old metrics
            await conn.execute('''
                DELETE FROM system_metrics 
                WHERE timestamp < NOW() - INTERVAL '%s days'
            ''', MonitoringConfig.METRICS_RETENTION_DAYS)
            
            # Clean old resolved alerts
            await conn.execute('''
                DELETE FROM alerts 
                WHERE status = 'resolved' 
                AND resolved_at < NOW() - INTERVAL '%s days'
            ''', MonitoringConfig.ALERTS_RETENTION_DAYS)
    
    def _row_to_alert(self, row) -> Alert:
        """Convert database row to Alert object"""
        return Alert(
            id=row['id'],
            rule_id=row['rule_id'],
            message=row['message'],
            severity=AlertSeverity(row['severity']),
            status=AlertStatus(row['status']),
            triggered_at=row['triggered_at'],
            acknowledged_at=row['acknowledged_at'],
            resolved_at=row['resolved_at'],
            metric_value=row['metric_value'],
            metadata=json.loads(row['metadata']) if row['metadata'] else None
        )

# ==============================================================================
# ALERT ENGINE
# ==============================================================================

class AlertEngine:
    """Alert processing and management engine"""
    
    def __init__(self, monitoring_db: MonitoringDatabase, bot_application):
        self.monitoring_db = monitoring_db
        self.bot = bot_application
        self.active_alerts = {}  # Cache for cooldown tracking
        self.alert_rules = []
        self.authorized_users = []  # Will be set from config
        
    async def initialize(self):
        """Initialize alert engine"""
        # Load alert rules
        await self.load_alert_rules()
        
        # Initialize default rules if none exist
        if not self.alert_rules:
            await self.initialize_default_rules()
    
    async def initialize_default_rules(self):
        """Create default alert rules"""
        for rule in MonitoringConfig.DEFAULT_ALERT_RULES:
            await self.monitoring_db.save_alert_rule(rule)
        
        await self.load_alert_rules()
        logger.info(f"Initialized {len(self.alert_rules)} default alert rules")
    
    async def load_alert_rules(self):
        """Load alert rules from database"""
        self.alert_rules = await self.monitoring_db.get_alert_rules()
    
    async def check_metrics(self, metrics: Dict[str, Any]):
        """Check metrics against alert rules"""
        try:
            for rule in self.alert_rules:
                if not rule.enabled:
                    continue
                
                # Extract metric value based on rule type
                metric_value = self._extract_metric_value(metrics, rule)
                if metric_value is None:
                    continue
                
                # Check if rule condition is met
                if self._evaluate_condition(metric_value, rule):
                    # Check cooldown
                    if not self._is_in_cooldown(rule.id):
                        await self._trigger_alert(rule, metric_value, metrics)
                else:
                    # Check if we should resolve existing alert
                    await self._check_alert_resolution(rule.id, metric_value)
                    
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    def _extract_metric_value(self, metrics: Dict[str, Any], rule: AlertRule) -> Optional[float]:
        """Extract the relevant metric value for a rule"""
        if rule.metric_type == "cpu":
            return metrics.get('cpu', {}).get('usage_percent')
        elif rule.metric_type == "memory":
            return metrics.get('memory', {}).get('usage_percent')
        elif rule.metric_type == "disk":
            return metrics.get('disk', {}).get('usage_percent')
        elif rule.metric_type == "load":
            return metrics.get('load', {}).get('load_1m')
        elif rule.metric_type == "docker":
            # For container checks, return number of running containers
            return metrics.get('docker', {}).get('running_containers', 0)
        
        return None
    
    def _evaluate_condition(self, value: float, rule: AlertRule) -> bool:
        """Evaluate if a metric value meets the alert condition"""
        if rule.condition == "gt":
            return value > rule.threshold
        elif rule.condition == "lt":
            return value < rule.threshold
        elif rule.condition == "eq":
            return abs(value - rule.threshold) < 0.01  # Float comparison
        
        return False
    
    def _is_in_cooldown(self, rule_id: str) -> bool:
        """Check if an alert rule is in cooldown period"""
        if rule_id in self.active_alerts:
            last_triggered = self.active_alerts[rule_id]
            rule = next((r for r in self.alert_rules if r.id == rule_id), None)
            if rule:
                cooldown_period = timedelta(minutes=rule.cooldown_minutes)
                return datetime.now() - last_triggered < cooldown_period
        return False
    
    async def _trigger_alert(self, rule: AlertRule, metric_value: float, metrics: Dict[str, Any]):
        """Trigger a new alert"""
        alert_id = f"{rule.id}_{int(datetime.now().timestamp())}"
        
        alert = Alert(
            id=alert_id,
            rule_id=rule.id,
            message=f"🚨 {rule.name}: {metric_value:.1f}{'%' if rule.metric_type in ['cpu', 'memory', 'disk'] else ''} (threshold: {rule.threshold}{'%' if rule.metric_type in ['cpu', 'memory', 'disk'] else ''})",
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            triggered_at=datetime.now(),
            metric_value=metric_value,
            metadata={"full_metrics": metrics}
        )
        
        # Save to database
        await self.monitoring_db.create_alert(alert)
        
        # Update cooldown tracking
        self.active_alerts[rule.id] = datetime.now()
        
        # Send notification
        await self._send_alert_notification(alert)
        
        logger.info(f"Alert triggered: {rule.name} - {metric_value}")
    
    async def _check_alert_resolution(self, rule_id: str, current_value: float):
        """Check if an alert should be automatically resolved"""
        # This could be enhanced to auto-resolve alerts when conditions normalize
        pass
    
    async def _send_alert_notification(self, alert: Alert):
        """Send alert notification to authorized users"""
        if not self.authorized_users:
            return
        
        # Format alert message
        severity_emoji = {
            AlertSeverity.LOW: "🔵",
            AlertSeverity.MEDIUM: "🟡", 
            AlertSeverity.HIGH: "🟠",
            AlertSeverity.CRITICAL: "🔴"
        }.get(alert.severity, "⚪")
        
        message = f"{severity_emoji} **ALERT - {alert.severity.value.upper()}**\n\n"
        message += f"{alert.message}\n\n"
        message += f"🕐 **Triggered:** {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        message += f"📊 **Rule ID:** {alert.rule_id}"
        
        # Add action buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ Acknowledge", callback_data=f"ack_alert_{alert.id}"),
                InlineKeyboardButton("🔍 Details", callback_data=f"alert_details_{alert.id}")
            ],
            [InlineKeyboardButton("📊 System Status", callback_data="system_monitor")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send to all authorized users
        for user_id in self.authorized_users:
            try:
                await self.bot.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Failed to send alert to user {user_id}: {e}")

# ==============================================================================
# HEALTH REPORTING SYSTEM
# ==============================================================================

class HealthReporter:
    """Generates comprehensive health reports"""
    
    def __init__(self, monitoring_db: MonitoringDatabase, vps_monitor):
        self.monitoring_db = monitoring_db
        self.vps_monitor = vps_monitor
    
    async def generate_daily_report(self) -> Dict[str, Any]:
        """Generate daily health report"""
        try:
            # Get latest metrics
            metrics_result = await self.vps_monitor.get_system_metrics()
            if not metrics_result['success']:
                return {"success": False, "error": "Failed to get current metrics"}
            
            current_metrics = metrics_result['metrics']
            
            # Get 24h metrics history
            cpu_history = await self.monitoring_db.get_metrics_history("cpu", 24)
            memory_history = await self.monitoring_db.get_metrics_history("memory", 24)
            
            # Get active alerts
            active_alerts = await self.monitoring_db.get_active_alerts()
            
            # Calculate health score
            health_score = self._calculate_health_score(current_metrics, active_alerts)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(current_metrics, active_alerts)
            
            # Create summary
            report = {
                "success": True,
                "report_type": "daily",
                "generated_at": datetime.now().isoformat(),
                "health_score": health_score,
                "current_metrics": current_metrics,
                "metrics_trends": {
                    "cpu_avg_24h": self._calculate_average([m["value"] for m in cpu_history]),
                    "memory_avg_24h": self._calculate_average([m["value"] for m in memory_history]),
                },
                "alerts_summary": {
                    "active_count": len(active_alerts),
                    "by_severity": self._group_alerts_by_severity(active_alerts)
                },
                "recommendations": recommendations
            }
            
            # Save to database
            await self.monitoring_db.save_health_report(
                "daily", health_score, current_metrics,
                report["alerts_summary"], recommendations
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate daily report: {e}")
            return {"success": False, "error": str(e)}
    
    def _calculate_health_score(self, metrics: Dict[str, Any], alerts: List[Alert]) -> float:
        """Calculate overall system health score (0-100)"""
        score = 100.0
        
        # Deduct points for high resource usage
        cpu_usage = metrics.get('cpu', {}).get('usage_percent', 0)
        memory_usage = metrics.get('memory', {}).get('usage_percent', 0)
        disk_usage = metrics.get('disk', {}).get('usage_percent', 0)
        load = metrics.get('load', {}).get('load_1m', 0)
        
        # CPU impact
        if cpu_usage > 90:
            score -= 20
        elif cpu_usage > 70:
            score -= 10
        elif cpu_usage > 50:
            score -= 5
        
        # Memory impact
        if memory_usage > 90:
            score -= 20
        elif memory_usage > 80:
            score -= 10
        elif memory_usage > 70:
            score -= 5
        
        # Disk impact
        if disk_usage > 95:
            score -= 15
        elif disk_usage > 85:
            score -= 8
        elif disk_usage > 75:
            score -= 3
        
        # Load impact
        if load > 8:
            score -= 15
        elif load > 4:
            score -= 8
        elif load > 2:
            score -= 3
        
        # Alert impact
        for alert in alerts:
            if alert.severity == AlertSeverity.CRITICAL:
                score -= 15
            elif alert.severity == AlertSeverity.HIGH:
                score -= 10
            elif alert.severity == AlertSeverity.MEDIUM:
                score -= 5
            elif alert.severity == AlertSeverity.LOW:
                score -= 2
        
        return max(0, min(100, score))
    
    def _generate_recommendations(self, metrics: Dict[str, Any], alerts: List[Alert]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        cpu_usage = metrics.get('cpu', {}).get('usage_percent', 0)
        memory_usage = metrics.get('memory', {}).get('usage_percent', 0)
        disk_usage = metrics.get('disk', {}).get('usage_percent', 0)
        load = metrics.get('load', {}).get('load_1m', 0)
        
        # CPU recommendations
        if cpu_usage > 85:
            recommendations.append("🔥 Critical CPU usage detected. Consider upgrading server or optimizing processes.")
        elif cpu_usage > 70:
            recommendations.append("⚠️ High CPU usage. Monitor running processes and consider optimization.")
        
        # Memory recommendations
        if memory_usage > 85:
            recommendations.append("💾 Critical memory usage. Consider adding RAM or reducing memory-intensive processes.")
        elif memory_usage > 70:
            recommendations.append("⚠️ High memory usage. Review memory consumption of applications.")
        
        # Disk recommendations
        if disk_usage > 90:
            recommendations.append("💽 Critical disk space. Immediate cleanup required to prevent system issues.")
        elif disk_usage > 80:
            recommendations.append("⚠️ High disk usage. Consider cleanup of logs and temporary files.")
        
        # Load recommendations
        if load > 4:
            recommendations.append("🏋️ High system load detected. Review running processes and system performance.")
        
        # Docker recommendations
        docker_stats = metrics.get('docker', {})
        stopped_containers = docker_stats.get('stopped_containers', 0)
        if stopped_containers > 0:
            recommendations.append(f"🐳 {stopped_containers} stopped containers detected. Review container health.")
        
        # Alert-based recommendations
        critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        if critical_alerts:
            recommendations.append(f"🚨 {len(critical_alerts)} critical alerts active. Immediate attention required.")
        
        # Default healthy message
        if not recommendations:
            recommendations.append("✅ System appears healthy. Continue regular monitoring.")
        
        return recommendations
    
    def _calculate_average(self, values: List[float]) -> float:
        """Calculate average of values"""
        return sum(values) / len(values) if values else 0.0
    
    def _group_alerts_by_severity(self, alerts: List[Alert]) -> Dict[str, int]:
        """Group alerts by severity"""
        severity_counts = {severity.value: 0 for severity in AlertSeverity}
        for alert in alerts:
            severity_counts[alert.severity.value] += 1
        return severity_counts
    
    def format_report_message(self, report: Dict[str, Any]) -> str:
        """Format health report for Telegram message"""
        if not report["success"]:
            return f"❌ Failed to generate health report: {report.get('error', 'Unknown error')}"
        
        health_score = report["health_score"]
        
        # Health score emoji
        if health_score >= 90:
            health_emoji = "🟢"
            health_status = "Excellent"
        elif health_score >= 75:
            health_emoji = "🟡"
            health_status = "Good"
        elif health_score >= 60:
            health_emoji = "🟠"
            health_status = "Fair"
        else:
            health_emoji = "🔴"
            health_status = "Poor"
        
        message = f"📊 **Daily Health Report**\n\n"
        message += f"{health_emoji} **Health Score:** {health_score:.1f}/100 ({health_status})\n\n"
        
        # Current metrics
        current = report["current_metrics"]
        cpu = current.get('cpu', {})
        memory = current.get('memory', {})
        disk = current.get('disk', {})
        docker_stats = current.get('docker', {})
        
        message += f"💻 **System Status:**\n"
        message += f"• CPU: {cpu.get('usage_percent', 0):.1f}%\n"
        message += f"• Memory: {memory.get('usage_percent', 0):.1f}% ({memory.get('used_mb', 0)}MB/{memory.get('total_mb', 0)}MB)\n"
        message += f"• Disk: {disk.get('usage_percent', 0):.1f}% ({disk.get('used', 'N/A')}/{disk.get('total', 'N/A')})\n"
        message += f"• Containers: {docker_stats.get('running_containers', 0)} running, {docker_stats.get('stopped_containers', 0)} stopped\n\n"
        
        # Alerts summary
        alerts_summary = report["alerts_summary"]
        active_count = alerts_summary["active_count"]
        
        if active_count > 0:
            message += f"🚨 **Active Alerts:** {active_count}\n"
            by_severity = alerts_summary["by_severity"]
            if by_severity.get('critical', 0) > 0:
                message += f"• 🔴 Critical: {by_severity['critical']}\n"
            if by_severity.get('high', 0) > 0:
                message += f"• 🟠 High: {by_severity['high']}\n"
            if by_severity.get('medium', 0) > 0:
                message += f"• 🟡 Medium: {by_severity['medium']}\n"
            if by_severity.get('low', 0) > 0:
                message += f"• 🔵 Low: {by_severity['low']}\n"
            message += "\n"
        else:
            message += f"✅ **No Active Alerts**\n\n"
        
        # Recommendations
        recommendations = report["recommendations"][:3]  # Show top 3
        if recommendations:
            message += f"💡 **Recommendations:**\n"
            for rec in recommendations:
                message += f"• {rec}\n"
        
        message += f"\n🕐 Generated: {datetime.fromisoformat(report['generated_at']).strftime('%Y-%m-%d %H:%M')}"
        
        return message

# ==============================================================================
# MONITORING MANAGER - MAIN CLASS
# ==============================================================================

class MonitoringManager:
    """Main monitoring and alerting system manager"""
    
    def __init__(self, db_manager, vps_monitor, bot_application):
        self.db = db_manager
        self.monitoring_db = MonitoringDatabase(db_manager)
        self.vps_monitor = vps_monitor
        self.alert_engine = AlertEngine(self.monitoring_db, bot_application)
        self.health_reporter = HealthReporter(self.monitoring_db, vps_monitor)
        self.bot = bot_application
        
        # Background task management
        self.monitoring_active = False
        self.task_executor = ThreadPoolExecutor(max_workers=2)
        
        # Store authorized user IDs
        self.authorized_users = []
    
    async def initialize(self):
        """Initialize the monitoring system"""
        await self.monitoring_db.initialize_monitoring_tables()
        await self.alert_engine.initialize()
        logger.info("Monitoring system initialized")
    
    def setup_handlers(self, application):
        """Setup monitoring-related handlers"""
        # Alert management
        application.add_handler(CommandHandler('alerts', self.show_alerts))
        application.add_handler(CommandHandler('alert_rules', self.show_alert_rules))
        application.add_handler(CommandHandler('health_report', self.generate_health_report))
        application.add_handler(CommandHandler('ack_alert', self.acknowledge_alert_command))
        
        # Monitoring controls
        application.add_handler(CommandHandler('start_monitoring', self.start_monitoring))
        application.add_handler(CommandHandler('stop_monitoring', self.stop_monitoring))
        application.add_handler(CommandHandler('monitoring_status', self.monitoring_status))
        
        # Callback handlers for alert interactions
        application.add_handler(CallbackQueryHandler(self.handle_alert_callbacks, pattern="^(ack_alert_|alert_details_|resolve_alert_)"))
    
    def set_authorized_users(self, user_ids: List[int]):
        """Set authorized users for alerts"""
        self.authorized_users = user_ids
        self.alert_engine.authorized_users = user_ids
    
    async def start_monitoring(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start background monitoring"""
        if self.monitoring_active:
            await update.message.reply_text("📊 Monitoring is already active.")
            return
        
        self.monitoring_active = True
        
        # Start background monitoring loop
        asyncio.create_task(self._monitoring_loop())
        
        await update.message.reply_text(
            "✅ **Monitoring Started**\n\n"
            f"🔄 Metrics collection: every {MonitoringConfig.METRICS_COLLECTION_INTERVAL//60} minutes\n"
            f"🚨 Alert checking: every {MonitoringConfig.ALERT_CHECK_INTERVAL//60} minute(s)\n"
            f"📊 Health reports: daily at {MonitoringConfig.DAILY_REPORT_TIME}\n\n"
            "Use /stop_monitoring to stop."
        )
        
        await self.db.log_command(update.effective_user.id, "start_monitoring", "Monitoring started", True)
    
    async def stop_monitoring(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop background monitoring"""
        if not self.monitoring_active:
            await update.message.reply_text("📊 Monitoring is not currently active.")
            return
        
        self.monitoring_active = False
        
        await update.message.reply_text(
            "⏹️ **Monitoring Stopped**\n\n"
            "Background monitoring has been disabled.\n"
            "Use /start_monitoring to restart."
        )
        
        await self.db.log_command(update.effective_user.id, "stop_monitoring", "Monitoring stopped", True)
    
    async def monitoring_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show monitoring system status"""
        status_emoji = "✅" if self.monitoring_active else "❌"
        status_text = "Active" if self.monitoring_active else "Inactive"
        
        # Get counts
        alert_rules = await self.monitoring_db.get_alert_rules()
        active_alerts = await self.monitoring_db.get_active_alerts()
        
        response = f"📊 **Monitoring System Status**\n\n"
        response += f"{status_emoji} **Status:** {status_text}\n"
        response += f"📋 **Alert Rules:** {len(alert_rules)} configured\n"
        response += f"🚨 **Active Alerts:** {len(active_alerts)}\n"
        response += f"👥 **Authorized Users:** {len(self.authorized_users)}\n\n"
        
        if self.monitoring_active:
            response += f"⚙️ **Collection Interval:** {MonitoringConfig.METRICS_COLLECTION_INTERVAL//60} min\n"
            response += f"🔍 **Alert Check:** {MonitoringConfig.ALERT_CHECK_INTERVAL//60} min\n"
        
        response += f"📅 **Data Retention:** {MonitoringConfig.METRICS_RETENTION_DAYS} days"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def show_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show active alerts"""
        active_alerts = await self.monitoring_db.get_active_alerts()
        
        if not active_alerts:
            await update.message.reply_text(
                "✅ **No Active Alerts**\n\n"
                "All systems are running normally."
            )
            return
        
        response = f"🚨 **Active Alerts ({len(active_alerts)})**\n\n"
        
        for alert in active_alerts[:10]:  # Show max 10 alerts
            severity_emoji = {
                AlertSeverity.LOW: "🔵",
                AlertSeverity.MEDIUM: "🟡",
                AlertSeverity.HIGH: "🟠", 
                AlertSeverity.CRITICAL: "🔴"
            }.get(alert.severity, "⚪")
            
            age = datetime.now() - alert.triggered_at
            age_str = f"{age.seconds//3600}h {(age.seconds//60)%60}m" if age.seconds > 3600 else f"{age.seconds//60}m"
            
            response += f"{severity_emoji} **{alert.severity.value.upper()}** - {age_str} ago\n"
            response += f"   {alert.message}\n"
            response += f"   ID: `{alert.id[:8]}...`\n\n"
        
        if len(active_alerts) > 10:
            response += f"... and {len(active_alerts) - 10} more alerts\n\n"
        
        # Add action buttons
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_alerts")],
            [InlineKeyboardButton("📊 System Status", callback_data="system_monitor")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(response, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def show_alert_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show configured alert rules"""
        rules = await self.monitoring_db.get_alert_rules()
        
        if not rules:
            await update.message.reply_text("📋 No alert rules configured.")
            return
        
        response = f"📋 **Alert Rules ({len(rules)})**\n\n"
        
        for rule in rules:
            status_emoji = "✅" if rule.enabled else "❌"
            severity_emoji = {
                AlertSeverity.LOW: "🔵",
                AlertSeverity.MEDIUM: "🟡",
                AlertSeverity.HIGH: "🟠",
                AlertSeverity.CRITICAL: "🔴"
            }.get(rule.severity, "⚪")
            
            response += f"{status_emoji} **{rule.name}**\n"
            response += f"   {severity_emoji} {rule.severity.value.upper()} - {rule.metric_type} {rule.condition} {rule.threshold}\n"
            response += f"   Cooldown: {rule.cooldown_minutes}min\n"
            if rule.description:
                response += f"   📝 {rule.description}\n"
            response += "\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def generate_health_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate and send health report"""
        loading_msg = await update.message.reply_text("📊 Generating health report...")
        
        report = await self.health_reporter.generate_daily_report()
        
        if not report["success"]:
            await loading_msg.edit_text(
                f"❌ Failed to generate health report:\n{report.get('error', 'Unknown error')}"
            )
            return
        
        report_message = self.health_reporter.format_report_message(report)
        
        # Add action buttons
        keyboard = [
            [InlineKeyboardButton("📊 System Monitor", callback_data="system_monitor")],
            [InlineKeyboardButton("🚨 View Alerts", callback_data="view_alerts")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await loading_msg.edit_text(
            report_message, 
            parse_mode='Markdown', 
            reply_markup=reply_markup
        )
        
        await self.db.log_command(update.effective_user.id, "health_report", f"Health score: {report['health_score']:.1f}", True)
    
    async def acknowledge_alert_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Acknowledge alert via command"""
        args = context.args
        if not args:
            await update.message.reply_text(
                "❌ Please specify an alert ID.\n"
                "Usage: /ack_alert <alert_id>"
            )
            return
        
        alert_id = args[0]
        await self.monitoring_db.acknowledge_alert(alert_id)
        