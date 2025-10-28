"""CLI dashboard for system monitoring."""
import time
from typing import Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.progress import Progress, BarColumn, TextColumn
from datetime import datetime

from ..monitors.cpu import CPUMonitor
from ..monitors.memory import MemoryMonitor
from ..monitors.disk import DiskMonitor
from ..monitors.network import NetworkMonitor
from ..monitors.gpu import GPUMonitor
from ..alerts.alert_manager import AlertManager, AlertLevel


class Dashboard:
    """Real-time monitoring dashboard."""

    def __init__(self, refresh_rate: float = 1.0, alert_manager: AlertManager = None):
        """
        Initialize the dashboard.

        Args:
            refresh_rate: Refresh rate in seconds
            alert_manager: Alert manager instance
        """
        self.console = Console()
        self.refresh_rate = refresh_rate
        self.alert_manager = alert_manager or AlertManager()

        # Initialize monitors
        self.cpu_monitor = CPUMonitor()
        self.memory_monitor = MemoryMonitor()
        self.disk_monitor = DiskMonitor()
        self.network_monitor = NetworkMonitor()
        self.gpu_monitor = GPUMonitor()

    def format_bytes(self, bytes_value: int) -> str:
        """Convert bytes to human readable format."""
        if bytes_value is None:
            return "N/A"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"

    def create_cpu_table(self, cpu_data: Dict) -> Table:
        """Create CPU information table."""
        table = Table(title="CPU", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        usage = cpu_data.get("usage_percent", 0)
        usage_color = "red" if usage > 90 else "yellow" if usage > 70 else "green"

        table.add_row("Usage", f"[{usage_color}]{usage:.1f}%[/{usage_color}]")
        table.add_row("Physical Cores", str(cpu_data.get("cpu_count", {}).get("physical", "N/A")))
        table.add_row("Logical Cores", str(cpu_data.get("cpu_count", {}).get("logical", "N/A")))

        freq = cpu_data.get("frequency")
        if freq and freq.get("current"):
            table.add_row("Frequency", f"{freq.get('current'):.0f} MHz")

        load_avg = cpu_data.get("load_average")
        if load_avg:
            table.add_row("Load Avg (1m)", f"{load_avg.get('1min', 0):.2f}")

        return table

    def create_memory_table(self, memory_data: Dict) -> Table:
        """Create memory information table."""
        table = Table(title="Memory", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        virtual = memory_data.get("virtual", {})
        swap = memory_data.get("swap", {})

        virtual_percent = virtual.get("percent", 0)
        virtual_color = "red" if virtual_percent > 90 else "yellow" if virtual_percent > 75 else "green"

        table.add_row("RAM Usage", f"[{virtual_color}]{virtual_percent:.1f}%[/{virtual_color}]")
        table.add_row("RAM Used", self.format_bytes(virtual.get("used")))
        table.add_row("RAM Total", self.format_bytes(virtual.get("total")))
        table.add_row("RAM Available", self.format_bytes(virtual.get("available")))

        swap_percent = swap.get("percent", 0)
        swap_color = "red" if swap_percent > 90 else "yellow" if swap_percent > 75 else "green"

        table.add_row("Swap Usage", f"[{swap_color}]{swap_percent:.1f}%[/{swap_color}]")
        table.add_row("Swap Used", self.format_bytes(swap.get("used")))
        table.add_row("Swap Total", self.format_bytes(swap.get("total")))

        return table

    def create_disk_table(self, disk_data: Dict) -> Table:
        """Create disk information table."""
        table = Table(title="Disk", show_header=True, header_style="bold magenta")
        table.add_column("Mount Point", style="cyan")
        table.add_column("Usage", style="green")
        table.add_column("Used", style="green")
        table.add_column("Total", style="green")

        for partition in disk_data.get("partitions", []):
            usage = partition.get("usage", {})
            if "error" not in usage:
                percent = usage.get("percent", 0)
                color = "red" if percent > 95 else "yellow" if percent > 80 else "green"

                table.add_row(
                    partition.get("mountpoint", "N/A"),
                    f"[{color}]{percent:.1f}%[/{color}]",
                    self.format_bytes(usage.get("used")),
                    self.format_bytes(usage.get("total"))
                )

        return table

    def create_network_table(self, network_data: Dict) -> Table:
        """Create network information table."""
        table = Table(title="Network", show_header=True, header_style="bold magenta")
        table.add_column("Interface", style="cyan")
        table.add_column("Sent", style="green")
        table.add_column("Received", style="green")

        interfaces = network_data.get("interfaces", {})
        if interfaces:
            for interface, stats in list(interfaces.items())[:5]:  # Show top 5
                table.add_row(
                    interface,
                    self.format_bytes(stats.get("bytes_sent")),
                    self.format_bytes(stats.get("bytes_recv"))
                )
        else:
            total = network_data.get("total", {})
            table.add_row(
                "Total",
                self.format_bytes(total.get("bytes_sent")),
                self.format_bytes(total.get("bytes_recv"))
            )

        return table

    def create_gpu_table(self, gpu_data: Dict) -> Table:
        """Create GPU information table."""
        table = Table(title="GPU", show_header=True, header_style="bold magenta")

        if not gpu_data.get("available"):
            table.add_column("Status", style="yellow")
            table.add_row("No GPU detected or drivers not available")
            return table

        table.add_column("GPU", style="cyan")
        table.add_column("Usage", style="green")
        table.add_column("Memory", style="green")
        table.add_column("Temp", style="green")

        for gpu in gpu_data.get("gpus", []):
            if "error" not in gpu:
                util = gpu.get("utilization", {})
                memory = gpu.get("memory", {})

                gpu_percent = util.get("gpu", 0)
                mem_percent = memory.get("percent", 0)

                gpu_color = "red" if gpu_percent > 95 else "yellow" if gpu_percent > 80 else "green"
                mem_color = "red" if mem_percent > 95 else "yellow" if mem_percent > 80 else "green"

                temp = gpu.get("temperature")
                temp_str = f"{temp}°C" if temp else "N/A"

                table.add_row(
                    f"GPU {gpu.get('index', 0)}",
                    f"[{gpu_color}]{gpu_percent:.1f}%[/{gpu_color}]",
                    f"[{mem_color}]{mem_percent:.1f}%[/{mem_color}]",
                    temp_str
                )

        return table

    def create_alerts_panel(self, alerts: list) -> Panel:
        """Create alerts panel."""
        if not alerts:
            return Panel("[green]No active alerts[/green]", title="Alerts", border_style="green")

        alert_text = Text()
        for alert in alerts[-5:]:  # Show last 5 alerts
            if alert.level == AlertLevel.CRITICAL:
                alert_text.append(f"[CRITICAL] {alert.message}\n", style="bold red")
            elif alert.level == AlertLevel.WARNING:
                alert_text.append(f"[WARNING] {alert.message}\n", style="bold yellow")
            else:
                alert_text.append(f"[INFO] {alert.message}\n", style="bold blue")

        border_color = "red" if any(a.level == AlertLevel.CRITICAL for a in alerts) else "yellow"
        return Panel(alert_text, title=f"Alerts ({len(alerts)})", border_style=border_color)

    def get_snapshot(self) -> Dict:
        """Get current system snapshot."""
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": self.cpu_monitor.get_usage(interval=0.1),
            "memory": self.memory_monitor.get_memory(),
            "disk": self.disk_monitor.get_complete_stats(),
            "network": self.network_monitor.get_io_counters(per_nic=True),
            "gpu": self.gpu_monitor.get_all_gpus()
        }

    def display_snapshot(self):
        """Display a one-time snapshot of system stats."""
        snapshot = self.get_snapshot()

        self.console.print(Panel(f"[bold]System Monitor Snapshot[/bold]\n{snapshot['timestamp']}",
                                 style="bold blue"))
        self.console.print()

        # Display tables
        self.console.print(self.create_cpu_table(snapshot["cpu"]))
        self.console.print()
        self.console.print(self.create_memory_table(snapshot["memory"]))
        self.console.print()
        self.console.print(self.create_disk_table(snapshot["disk"]))
        self.console.print()
        self.console.print(self.create_network_table(snapshot["network"]))
        self.console.print()
        self.console.print(self.create_gpu_table(snapshot["gpu"]))

        # Check for alerts
        alerts = self.alert_manager.check_all(snapshot)
        if alerts:
            self.console.print()
            self.console.print(self.create_alerts_panel(alerts))

    def run_dashboard(self):
        """Run the real-time dashboard."""
        self.console.clear()
        self.console.print("[bold green]Starting Real-Time System Monitor Dashboard[/bold green]")
        self.console.print("Press Ctrl+C to exit\n")

        try:
            with Live(console=self.console, refresh_per_second=1/self.refresh_rate) as live:
                while True:
                    snapshot = self.get_snapshot()
                    alerts = self.alert_manager.check_all(snapshot)

                    # Create layout
                    layout = Layout()
                    layout.split_column(
                        Layout(name="header", size=3),
                        Layout(name="main"),
                        Layout(name="alerts", size=8)
                    )

                    layout["header"].update(
                        Panel(f"[bold]System Monitor - Live Dashboard[/bold]\n{snapshot['timestamp']}",
                              style="bold blue")
                    )

                    # Split main into columns
                    layout["main"].split_row(
                        Layout(name="left"),
                        Layout(name="right")
                    )

                    # Left column
                    layout["left"].split_column(
                        Layout(self.create_cpu_table(snapshot["cpu"])),
                        Layout(self.create_memory_table(snapshot["memory"]))
                    )

                    # Right column
                    layout["right"].split_column(
                        Layout(self.create_disk_table(snapshot["disk"])),
                        Layout(self.create_network_table(snapshot["network"])),
                        Layout(self.create_gpu_table(snapshot["gpu"]))
                    )

                    # Alerts panel
                    layout["alerts"].update(self.create_alerts_panel(alerts))

                    live.update(layout)
                    time.sleep(self.refresh_rate)

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Dashboard stopped by user[/yellow]")
