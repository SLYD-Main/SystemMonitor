"""Alert and threshold management system."""
from typing import Dict, List, Callable, Optional
from datetime import datetime
from enum import Enum
import logging


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert:
    """Represents a monitoring alert."""

    def __init__(self, level: AlertLevel, metric: str, message: str, value: float, threshold: float):
        """
        Create a new alert.

        Args:
            level: Alert severity level
            metric: Metric that triggered the alert
            message: Human-readable alert message
            value: Current value that triggered the alert
            threshold: Threshold that was exceeded
        """
        self.level = level
        self.metric = metric
        self.message = message
        self.value = value
        self.threshold = threshold
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        """Convert alert to dictionary."""
        return {
            "level": self.level.value,
            "metric": self.metric,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat()
        }

    def __repr__(self) -> str:
        return f"[{self.level.value.upper()}] {self.metric}: {self.message} (value={self.value:.2f}, threshold={self.threshold})"


class AlertManager:
    """Manage monitoring alerts and thresholds."""

    def __init__(self, thresholds: Optional[Dict] = None):
        """
        Initialize the alert manager.

        Args:
            thresholds: Dictionary of thresholds for different metrics
        """
        self.thresholds = thresholds or self._default_thresholds()
        self.active_alerts: List[Alert] = []
        self.alert_history: List[Alert] = []
        self.callbacks: List[Callable] = []
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def _default_thresholds() -> Dict:
        """Get default threshold configuration."""
        return {
            "cpu": {
                "warning": 70,
                "critical": 90
            },
            "memory": {
                "warning": 75,
                "critical": 90
            },
            "disk": {
                "warning": 80,
                "critical": 95
            },
            "gpu": {
                "warning": 80,
                "critical": 95
            },
            "network": {
                "warning": 100,  # MB/s
                "critical": 500
            }
        }

    def register_callback(self, callback: Callable[[Alert], None]):
        """
        Register a callback function to be called when alerts are triggered.

        Args:
            callback: Function that takes an Alert object
        """
        self.callbacks.append(callback)

    def check_cpu(self, cpu_data: Dict) -> List[Alert]:
        """
        Check CPU metrics against thresholds.

        Args:
            cpu_data: CPU monitoring data

        Returns:
            List of triggered alerts
        """
        alerts = []
        usage = cpu_data.get("usage_percent", 0)

        if usage >= self.thresholds["cpu"]["critical"]:
            alert = Alert(
                AlertLevel.CRITICAL,
                "cpu_usage",
                f"CPU usage critically high at {usage:.1f}%",
                usage,
                self.thresholds["cpu"]["critical"]
            )
            alerts.append(alert)
        elif usage >= self.thresholds["cpu"]["warning"]:
            alert = Alert(
                AlertLevel.WARNING,
                "cpu_usage",
                f"CPU usage high at {usage:.1f}%",
                usage,
                self.thresholds["cpu"]["warning"]
            )
            alerts.append(alert)

        return alerts

    def check_memory(self, memory_data: Dict) -> List[Alert]:
        """
        Check memory metrics against thresholds.

        Args:
            memory_data: Memory monitoring data

        Returns:
            List of triggered alerts
        """
        alerts = []
        virtual_percent = memory_data.get("virtual", {}).get("percent", 0)
        swap_percent = memory_data.get("swap", {}).get("percent", 0)

        # Check virtual memory
        if virtual_percent >= self.thresholds["memory"]["critical"]:
            alert = Alert(
                AlertLevel.CRITICAL,
                "memory_usage",
                f"Memory usage critically high at {virtual_percent:.1f}%",
                virtual_percent,
                self.thresholds["memory"]["critical"]
            )
            alerts.append(alert)
        elif virtual_percent >= self.thresholds["memory"]["warning"]:
            alert = Alert(
                AlertLevel.WARNING,
                "memory_usage",
                f"Memory usage high at {virtual_percent:.1f}%",
                virtual_percent,
                self.thresholds["memory"]["warning"]
            )
            alerts.append(alert)

        # Check swap usage
        if swap_percent >= self.thresholds["memory"]["critical"]:
            alert = Alert(
                AlertLevel.CRITICAL,
                "swap_usage",
                f"Swap usage critically high at {swap_percent:.1f}%",
                swap_percent,
                self.thresholds["memory"]["critical"]
            )
            alerts.append(alert)
        elif swap_percent >= self.thresholds["memory"]["warning"]:
            alert = Alert(
                AlertLevel.WARNING,
                "swap_usage",
                f"Swap usage high at {swap_percent:.1f}%",
                swap_percent,
                self.thresholds["memory"]["warning"]
            )
            alerts.append(alert)

        return alerts

    def check_disk(self, disk_data: Dict) -> List[Alert]:
        """
        Check disk metrics against thresholds.

        Args:
            disk_data: Disk monitoring data

        Returns:
            List of triggered alerts
        """
        alerts = []

        for partition in disk_data.get("partitions", []):
            usage = partition.get("usage", {})
            if "error" in usage:
                continue

            percent = usage.get("percent", 0)
            mountpoint = partition.get("mountpoint", "unknown")

            if percent >= self.thresholds["disk"]["critical"]:
                alert = Alert(
                    AlertLevel.CRITICAL,
                    f"disk_usage_{mountpoint}",
                    f"Disk usage critically high on {mountpoint} at {percent:.1f}%",
                    percent,
                    self.thresholds["disk"]["critical"]
                )
                alerts.append(alert)
            elif percent >= self.thresholds["disk"]["warning"]:
                alert = Alert(
                    AlertLevel.WARNING,
                    f"disk_usage_{mountpoint}",
                    f"Disk usage high on {mountpoint} at {percent:.1f}%",
                    percent,
                    self.thresholds["disk"]["warning"]
                )
                alerts.append(alert)

        return alerts

    def check_gpu(self, gpu_data: Dict) -> List[Alert]:
        """
        Check GPU metrics against thresholds.

        Args:
            gpu_data: GPU monitoring data

        Returns:
            List of triggered alerts
        """
        alerts = []

        if not gpu_data.get("available"):
            return alerts

        for gpu in gpu_data.get("gpus", []):
            if "error" in gpu:
                continue

            gpu_index = gpu.get("index", 0)
            utilization = gpu.get("utilization", {}).get("gpu", 0)
            memory_percent = gpu.get("memory", {}).get("percent", 0)

            # Check GPU utilization
            if utilization >= self.thresholds["gpu"]["critical"]:
                alert = Alert(
                    AlertLevel.CRITICAL,
                    f"gpu_utilization_{gpu_index}",
                    f"GPU {gpu_index} utilization critically high at {utilization:.1f}%",
                    utilization,
                    self.thresholds["gpu"]["critical"]
                )
                alerts.append(alert)
            elif utilization >= self.thresholds["gpu"]["warning"]:
                alert = Alert(
                    AlertLevel.WARNING,
                    f"gpu_utilization_{gpu_index}",
                    f"GPU {gpu_index} utilization high at {utilization:.1f}%",
                    utilization,
                    self.thresholds["gpu"]["warning"]
                )
                alerts.append(alert)

            # Check GPU memory
            if memory_percent >= self.thresholds["gpu"]["critical"]:
                alert = Alert(
                    AlertLevel.CRITICAL,
                    f"gpu_memory_{gpu_index}",
                    f"GPU {gpu_index} memory critically high at {memory_percent:.1f}%",
                    memory_percent,
                    self.thresholds["gpu"]["critical"]
                )
                alerts.append(alert)
            elif memory_percent >= self.thresholds["gpu"]["warning"]:
                alert = Alert(
                    AlertLevel.WARNING,
                    f"gpu_memory_{gpu_index}",
                    f"GPU {gpu_index} memory high at {memory_percent:.1f}%",
                    memory_percent,
                    self.thresholds["gpu"]["warning"]
                )
                alerts.append(alert)

        return alerts

    def check_all(self, monitoring_data: Dict) -> List[Alert]:
        """
        Check all metrics against thresholds.

        Args:
            monitoring_data: Complete monitoring data

        Returns:
            List of all triggered alerts
        """
        all_alerts = []

        if "cpu" in monitoring_data:
            all_alerts.extend(self.check_cpu(monitoring_data["cpu"]))

        if "memory" in monitoring_data:
            all_alerts.extend(self.check_memory(monitoring_data["memory"]))

        if "disk" in monitoring_data:
            all_alerts.extend(self.check_disk(monitoring_data["disk"]))

        if "gpu" in monitoring_data:
            all_alerts.extend(self.check_gpu(monitoring_data["gpu"]))

        # Update active alerts and history
        self.active_alerts = all_alerts
        self.alert_history.extend(all_alerts)

        # Trigger callbacks
        for alert in all_alerts:
            self.logger.warning(str(alert))
            for callback in self.callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.error(f"Error in alert callback: {e}")

        return all_alerts

    def get_active_alerts(self) -> List[Alert]:
        """Get currently active alerts."""
        return self.active_alerts

    def get_alert_history(self, limit: Optional[int] = None) -> List[Alert]:
        """
        Get alert history.

        Args:
            limit: Maximum number of alerts to return (most recent first)

        Returns:
            List of historical alerts
        """
        if limit:
            return self.alert_history[-limit:]
        return self.alert_history

    def clear_alerts(self):
        """Clear active alerts."""
        self.active_alerts = []

    def clear_history(self):
        """Clear alert history."""
        self.alert_history = []