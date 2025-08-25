import os

class MonitoringConfig:
    """Monitoring module configuration"""
    
    # Intervals (in seconds)
    METRICS_INTERVAL = int(os.getenv("METRICS_INTERVAL", "300"))  # 5 minutes
    ALERT_CHECK_INTERVAL = int(os.getenv("ALERT_CHECK_INTERVAL", "60"))  # 1 minute
    
    # Thresholds
    CPU_THRESHOLD = float(os.getenv("CPU_THRESHOLD", "80"))  # 80%
    MEMORY_THRESHOLD = float(os.getenv("MEMORY_THRESHOLD", "80"))  # 80%
    DISK_THRESHOLD = float(os.getenv("DISK_THRESHOLD", "85"))  # 85%
    
    # Alert Settings
    ALERT_COOLDOWN = 1800  # 30 minutes between similar alerts
