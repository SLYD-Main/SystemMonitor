"""Network monitoring module."""
import psutil
import time
from typing import Dict, List, Optional
from datetime import datetime


class NetworkMonitor:
    """Monitor network usage and statistics."""

    def __init__(self):
        self.last_stats = None
        self.last_time = None

    def get_interfaces(self) -> List[str]:
        """
        Get list of network interface names.

        Returns:
            List of interface names
        """
        return list(psutil.net_io_counters(pernic=True).keys())

    def get_io_counters(self, per_nic: bool = False) -> Dict:
        """
        Get network I/O statistics.

        Args:
            per_nic: If True, return per-interface statistics

        Returns:
            Dictionary containing network I/O statistics
        """
        if per_nic:
            counters = psutil.net_io_counters(pernic=True)
            result = {
                "timestamp": datetime.now().isoformat(),
                "interfaces": {}
            }

            for interface, stats in counters.items():
                result["interfaces"][interface] = {
                    "bytes_sent": stats.bytes_sent,
                    "bytes_recv": stats.bytes_recv,
                    "packets_sent": stats.packets_sent,
                    "packets_recv": stats.packets_recv,
                    "errin": stats.errin,
                    "errout": stats.errout,
                    "dropin": stats.dropin,
                    "dropout": stats.dropout
                }

            return result
        else:
            stats = psutil.net_io_counters()
            return {
                "timestamp": datetime.now().isoformat(),
                "total": {
                    "bytes_sent": stats.bytes_sent,
                    "bytes_recv": stats.bytes_recv,
                    "packets_sent": stats.packets_sent,
                    "packets_recv": stats.packets_recv,
                    "errin": stats.errin,
                    "errout": stats.errout,
                    "dropin": stats.dropin,
                    "dropout": stats.dropout
                }
            }

    def get_speed(self, interval: float = 1.0, per_nic: bool = False) -> Dict:
        """
        Get network speed (bytes per second).

        Args:
            interval: Time interval for measurement in seconds
            per_nic: If True, return per-interface speeds

        Returns:
            Dictionary containing network speeds
        """
        counters_before = psutil.net_io_counters(pernic=per_nic)
        time.sleep(interval)
        counters_after = psutil.net_io_counters(pernic=per_nic)

        if per_nic:
            result = {
                "timestamp": datetime.now().isoformat(),
                "interval_seconds": interval,
                "interfaces": {}
            }

            for interface in counters_before.keys():
                if interface in counters_after:
                    sent_speed = (counters_after[interface].bytes_sent -
                                 counters_before[interface].bytes_sent) / interval
                    recv_speed = (counters_after[interface].bytes_recv -
                                 counters_before[interface].bytes_recv) / interval

                    result["interfaces"][interface] = {
                        "upload_speed_bps": sent_speed,
                        "download_speed_bps": recv_speed,
                        "upload_speed_mbps": sent_speed / (1024 * 1024),
                        "download_speed_mbps": recv_speed / (1024 * 1024)
                    }

            return result
        else:
            sent_speed = (counters_after.bytes_sent - counters_before.bytes_sent) / interval
            recv_speed = (counters_after.bytes_recv - counters_before.bytes_recv) / interval

            return {
                "timestamp": datetime.now().isoformat(),
                "interval_seconds": interval,
                "total": {
                    "upload_speed_bps": sent_speed,
                    "download_speed_bps": recv_speed,
                    "upload_speed_mbps": sent_speed / (1024 * 1024),
                    "download_speed_mbps": recv_speed / (1024 * 1024)
                }
            }

    def get_connections(self, kind: str = "inet") -> List[Dict]:
        """
        Get active network connections.

        Args:
            kind: Connection type ('inet', 'inet4', 'inet6', 'tcp', 'udp', 'unix', 'all')

        Returns:
            List of active connections
        """
        try:
            connections = psutil.net_connections(kind=kind)
            result = []

            for conn in connections:
                conn_info = {
                    "fd": conn.fd,
                    "family": str(conn.family),
                    "type": str(conn.type),
                    "local_address": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                    "remote_address": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    "status": conn.status,
                    "pid": conn.pid
                }
                result.append(conn_info)

            return result
        except (psutil.AccessDenied, PermissionError):
            return []

    def get_interface_addresses(self) -> Dict:
        """
        Get network interface addresses.

        Returns:
            Dictionary containing interface addresses
        """
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        result = {
            "timestamp": datetime.now().isoformat(),
            "interfaces": {}
        }

        for interface, addr_list in addrs.items():
            result["interfaces"][interface] = {
                "addresses": [],
                "stats": {}
            }

            for addr in addr_list:
                addr_info = {
                    "family": str(addr.family),
                    "address": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": addr.broadcast
                }
                result["interfaces"][interface]["addresses"].append(addr_info)

            if interface in stats:
                stat = stats[interface]
                result["interfaces"][interface]["stats"] = {
                    "is_up": stat.isup,
                    "duplex": str(stat.duplex),
                    "speed": stat.speed,
                    "mtu": stat.mtu
                }

        return result