"""Memory monitoring module."""
import psutil
from typing import Dict
from datetime import datetime


class MemoryMonitor:
    """Monitor RAM and Swap memory usage."""

    def get_memory(self) -> Dict:
        """
        Get memory usage statistics.

        Returns:
            Dictionary containing memory statistics
        """
        virtual_mem = psutil.virtual_memory()
        swap_mem = psutil.swap_memory()

        return {
            "timestamp": datetime.now().isoformat(),
            "virtual": {
                "total": virtual_mem.total,
                "available": virtual_mem.available,
                "used": virtual_mem.used,
                "free": virtual_mem.free,
                "percent": virtual_mem.percent,
                "active": getattr(virtual_mem, 'active', None),
                "inactive": getattr(virtual_mem, 'inactive', None),
                "buffers": getattr(virtual_mem, 'buffers', None),
                "cached": getattr(virtual_mem, 'cached', None),
                "shared": getattr(virtual_mem, 'shared', None)
            },
            "swap": {
                "total": swap_mem.total,
                "used": swap_mem.used,
                "free": swap_mem.free,
                "percent": swap_mem.percent,
                "sin": swap_mem.sin,
                "sout": swap_mem.sout
            }
        }

    def get_readable_memory(self) -> Dict:
        """
        Get memory statistics in human-readable format.

        Returns:
            Dictionary with formatted memory values
        """
        mem = self.get_memory()

        def format_bytes(bytes_value):
            """Convert bytes to human readable format."""
            if bytes_value is None:
                return None
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_value < 1024.0:
                    return f"{bytes_value:.2f} {unit}"
                bytes_value /= 1024.0
            return f"{bytes_value:.2f} PB"

        return {
            "timestamp": mem["timestamp"],
            "virtual": {
                "total": format_bytes(mem["virtual"]["total"]),
                "available": format_bytes(mem["virtual"]["available"]),
                "used": format_bytes(mem["virtual"]["used"]),
                "free": format_bytes(mem["virtual"]["free"]),
                "percent": f"{mem['virtual']['percent']:.1f}%"
            },
            "swap": {
                "total": format_bytes(mem["swap"]["total"]),
                "used": format_bytes(mem["swap"]["used"]),
                "free": format_bytes(mem["swap"]["free"]),
                "percent": f"{mem['swap']['percent']:.1f}%"
            }
        }
