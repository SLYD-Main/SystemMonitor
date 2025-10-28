"""Disk monitoring module."""
import psutil
from typing import Dict, List
from datetime import datetime


class DiskMonitor:
    """Monitor disk usage and I/O statistics."""

    def get_disk_usage(self, path: str = "/") -> Dict:
        """
        Get disk usage for a specific path.

        Args:
            path: Path to check disk usage for

        Returns:
            Dictionary containing disk usage statistics
        """
        try:
            usage = psutil.disk_usage(path)
            return {
                "path": path,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent
            }
        except Exception as e:
            return {
                "path": path,
                "error": str(e)
            }

    def get_all_partitions(self) -> List[Dict]:
        """
        Get usage statistics for all disk partitions.

        Returns:
            List of dictionaries containing partition information
        """
        partitions = []
        for partition in psutil.disk_partitions(all=False):
            usage = self.get_disk_usage(partition.mountpoint)
            partition_info = {
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "opts": partition.opts,
                "usage": usage
            }
            partitions.append(partition_info)

        return partitions

    def get_io_stats(self) -> Dict:
        """
        Get disk I/O statistics.

        Returns:
            Dictionary containing I/O statistics
        """
        try:
            io_counters = psutil.disk_io_counters(perdisk=False)
            per_disk_counters = psutil.disk_io_counters(perdisk=True)

            stats = {
                "timestamp": datetime.now().isoformat(),
                "total": {
                    "read_count": io_counters.read_count,
                    "write_count": io_counters.write_count,
                    "read_bytes": io_counters.read_bytes,
                    "write_bytes": io_counters.write_bytes,
                    "read_time": io_counters.read_time,
                    "write_time": io_counters.write_time
                } if io_counters else None,
                "per_disk": {}
            }

            if per_disk_counters:
                for disk_name, counters in per_disk_counters.items():
                    stats["per_disk"][disk_name] = {
                        "read_count": counters.read_count,
                        "write_count": counters.write_count,
                        "read_bytes": counters.read_bytes,
                        "write_bytes": counters.write_bytes,
                        "read_time": counters.read_time,
                        "write_time": counters.write_time
                    }

            return stats
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }

    def get_complete_stats(self) -> Dict:
        """
        Get complete disk statistics including partitions and I/O.

        Returns:
            Dictionary with all disk information
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "partitions": self.get_all_partitions(),
            "io_stats": self.get_io_stats()
        }
