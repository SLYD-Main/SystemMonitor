"""CPU monitoring module."""
import psutil
from typing import Dict, List, Optional
from datetime import datetime


class CPUMonitor:
    """Monitor CPU usage and statistics."""

    def __init__(self):
        self.cpu_count_physical = psutil.cpu_count(logical=False)
        self.cpu_count_logical = psutil.cpu_count(logical=True)

    def get_usage(self, interval: float = 1.0, per_cpu: bool = False) -> Dict:
        """
        Get CPU usage statistics.

        Args:
            interval: Time interval for measurement in seconds
            per_cpu: If True, return per-CPU usage

        Returns:
            Dictionary containing CPU usage statistics
        """
        cpu_percent = psutil.cpu_percent(interval=interval, percpu=per_cpu)
        cpu_freq = psutil.cpu_freq()

        stats = {
            "timestamp": datetime.now().isoformat(),
            "usage_percent": cpu_percent if not per_cpu else sum(cpu_percent) / len(cpu_percent),
            "per_cpu_percent": cpu_percent if per_cpu else None,
            "cpu_count": {
                "physical": self.cpu_count_physical,
                "logical": self.cpu_count_logical
            },
            "frequency": {
                "current": cpu_freq.current if cpu_freq else None,
                "min": cpu_freq.min if cpu_freq else None,
                "max": cpu_freq.max if cpu_freq else None
            } if cpu_freq else None,
            "load_average": self._get_load_average()
        }

        return stats

    def _get_load_average(self) -> Optional[Dict]:
        """Get system load average (Unix-like systems only)."""
        try:
            load_avg = psutil.getloadavg()
            return {
                "1min": load_avg[0],
                "5min": load_avg[1],
                "15min": load_avg[2]
            }
        except (AttributeError, OSError):
            return None

    def get_stats(self) -> Dict:
        """Get detailed CPU statistics."""
        cpu_times = psutil.cpu_times()
        cpu_stats = psutil.cpu_stats()

        return {
            "timestamp": datetime.now().isoformat(),
            "times": {
                "user": cpu_times.user,
                "system": cpu_times.system,
                "idle": cpu_times.idle,
                "iowait": getattr(cpu_times, 'iowait', None),
                "irq": getattr(cpu_times, 'irq', None),
                "softirq": getattr(cpu_times, 'softirq', None),
            },
            "stats": {
                "ctx_switches": cpu_stats.ctx_switches,
                "interrupts": cpu_stats.interrupts,
                "soft_interrupts": cpu_stats.soft_interrupts,
                "syscalls": getattr(cpu_stats, 'syscalls', None)
            }
        }
