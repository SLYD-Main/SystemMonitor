"""Historical data storage and management."""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import threading


class HistoricalDatabase:
    """Manage historical monitoring data storage."""

    def __init__(self, db_path: str = "monitor_history.db"):
        """
        Initialize the historical database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()

    def _init_database(self):
        """Initialize database tables."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # CPU history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cpu_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    usage_percent REAL,
                    frequency_current REAL,
                    load_avg_1min REAL,
                    load_avg_5min REAL,
                    load_avg_15min REAL
                )
            """)

            # Memory history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    virtual_total INTEGER,
                    virtual_used INTEGER,
                    virtual_percent REAL,
                    swap_total INTEGER,
                    swap_used INTEGER,
                    swap_percent REAL
                )
            """)

            # Disk history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS disk_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    mountpoint TEXT,
                    total INTEGER,
                    used INTEGER,
                    percent REAL,
                    read_bytes INTEGER,
                    write_bytes INTEGER
                )
            """)

            # Network history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS network_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    interface TEXT,
                    bytes_sent INTEGER,
                    bytes_recv INTEGER,
                    upload_speed REAL,
                    download_speed REAL
                )
            """)

            # GPU history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gpu_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    gpu_index INTEGER,
                    gpu_name TEXT,
                    utilization_gpu REAL,
                    utilization_memory REAL,
                    memory_used INTEGER,
                    memory_total INTEGER,
                    temperature REAL,
                    power_usage REAL
                )
            """)

            # Create indexes for faster queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cpu_timestamp ON cpu_history(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_timestamp ON memory_history(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_disk_timestamp ON disk_history(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_network_timestamp ON network_history(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_gpu_timestamp ON gpu_history(timestamp)")

            conn.commit()
            conn.close()

    def store_cpu_data(self, data: Dict):
        """Store CPU monitoring data."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            load_avg = data.get("load_average", {})
            cursor.execute("""
                INSERT INTO cpu_history
                (timestamp, usage_percent, frequency_current, load_avg_1min, load_avg_5min, load_avg_15min)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data.get("timestamp"),
                data.get("usage_percent"),
                data.get("frequency", {}).get("current") if data.get("frequency") else None,
                load_avg.get("1min") if load_avg else None,
                load_avg.get("5min") if load_avg else None,
                load_avg.get("15min") if load_avg else None
            ))

            conn.commit()
            conn.close()

    def store_memory_data(self, data: Dict):
        """Store memory monitoring data."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            virtual = data.get("virtual", {})
            swap = data.get("swap", {})

            cursor.execute("""
                INSERT INTO memory_history
                (timestamp, virtual_total, virtual_used, virtual_percent, swap_total, swap_used, swap_percent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("timestamp"),
                virtual.get("total"),
                virtual.get("used"),
                virtual.get("percent"),
                swap.get("total"),
                swap.get("used"),
                swap.get("percent")
            ))

            conn.commit()
            conn.close()

    def store_disk_data(self, data: Dict):
        """Store disk monitoring data."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            timestamp = data.get("timestamp")
            io_stats = data.get("io_stats", {})
            total_io = io_stats.get("total", {}) if isinstance(io_stats, dict) else {}

            # Store data for each partition
            for partition in data.get("partitions", []):
                usage = partition.get("usage", {})
                if "error" not in usage:
                    cursor.execute("""
                        INSERT INTO disk_history
                        (timestamp, mountpoint, total, used, percent, read_bytes, write_bytes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        timestamp,
                        partition.get("mountpoint"),
                        usage.get("total"),
                        usage.get("used"),
                        usage.get("percent"),
                        total_io.get("read_bytes"),
                        total_io.get("write_bytes")
                    ))

            conn.commit()
            conn.close()

    def store_network_data(self, data: Dict):
        """Store network monitoring data."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            timestamp = data.get("timestamp")

            # Store per-interface data if available
            interfaces = data.get("interfaces", {})
            if interfaces:
                for interface, stats in interfaces.items():
                    cursor.execute("""
                        INSERT INTO network_history
                        (timestamp, interface, bytes_sent, bytes_recv, upload_speed, download_speed)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        timestamp,
                        interface,
                        stats.get("bytes_sent"),
                        stats.get("bytes_recv"),
                        stats.get("upload_speed_bps"),
                        stats.get("download_speed_bps")
                    ))
            else:
                # Store total data
                total = data.get("total", {})
                cursor.execute("""
                    INSERT INTO network_history
                    (timestamp, interface, bytes_sent, bytes_recv, upload_speed, download_speed)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    "total",
                    total.get("bytes_sent"),
                    total.get("bytes_recv"),
                    total.get("upload_speed_bps"),
                    total.get("download_speed_bps")
                ))

            conn.commit()
            conn.close()

    def store_gpu_data(self, data: Dict):
        """Store GPU monitoring data."""
        if not data.get("available"):
            return

        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            timestamp = data.get("timestamp")

            for gpu in data.get("gpus", []):
                if "error" not in gpu:
                    utilization = gpu.get("utilization", {})
                    memory = gpu.get("memory", {})
                    power = gpu.get("power", {})

                    cursor.execute("""
                        INSERT INTO gpu_history
                        (timestamp, gpu_index, gpu_name, utilization_gpu, utilization_memory,
                         memory_used, memory_total, temperature, power_usage)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        timestamp,
                        gpu.get("index"),
                        gpu.get("name"),
                        utilization.get("gpu"),
                        utilization.get("memory"),
                        memory.get("used"),
                        memory.get("total"),
                        gpu.get("temperature"),
                        power.get("usage") if power else None
                    ))

            conn.commit()
            conn.close()

    def get_history(self, table: str, hours: int = 24, limit: Optional[int] = None) -> List[Dict]:
        """
        Retrieve historical data from a table.

        Args:
            table: Table name (cpu_history, memory_history, etc.)
            hours: Number of hours to retrieve
            limit: Maximum number of records to return

        Returns:
            List of historical records
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

            query = f"SELECT * FROM {table} WHERE timestamp >= ? ORDER BY timestamp DESC"
            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query, (cutoff_time,))
            rows = cursor.fetchall()

            conn.close()

            return [dict(row) for row in rows]

    def cleanup_old_data(self, retention_hours: int = 24):
        """
        Remove data older than retention period.

        Args:
            retention_hours: Number of hours to retain
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_time = (datetime.now() - timedelta(hours=retention_hours)).isoformat()

            tables = ["cpu_history", "memory_history", "disk_history", "network_history", "gpu_history"]

            for table in tables:
                cursor.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff_time,))

            conn.commit()
            conn.close()

    def get_statistics(self, table: str, hours: int = 1) -> Dict:
        """
        Get statistical summary for a table.

        Args:
            table: Table name
            hours: Number of hours to analyze

        Returns:
            Dictionary with min, max, avg statistics
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()

            # Get numeric columns for the table
            if table == "cpu_history":
                metric = "usage_percent"
            elif table == "memory_history":
                metric = "virtual_percent"
            elif table == "disk_history":
                metric = "percent"
            elif table == "gpu_history":
                metric = "utilization_gpu"
            else:
                return {}

            cursor.execute(f"""
                SELECT
                    MIN({metric}) as min,
                    MAX({metric}) as max,
                    AVG({metric}) as avg,
                    COUNT(*) as count
                FROM {table}
                WHERE timestamp >= ?
            """, (cutoff_time,))

            row = cursor.fetchone()
            conn.close()

            return {
                "min": row[0],
                "max": row[1],
                "avg": row[2],
                "count": row[3],
                "hours": hours
            }