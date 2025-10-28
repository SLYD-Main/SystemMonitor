#!/usr/bin/env python3
"""
System Monitor - Hardware monitoring tool for CPU, Memory, Disk, Network, and GPU.

This tool provides both CLI and REST API interfaces for monitoring system hardware.
"""
import click
import json
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler

from src.cli.dashboard import Dashboard
from src.api.server import MonitoringAPI
from src.config import Config
from src.storage.database import HistoricalDatabase
from src.storage.exporter import DataExporter
from src.alerts.alert_manager import AlertManager
from src.monitors.cpu import CPUMonitor
from src.monitors.memory import MemoryMonitor
from src.monitors.disk import DiskMonitor
from src.monitors.network import NetworkMonitor
from src.monitors.gpu import GPUMonitor
from src.monitors.speedtest import SpeedTestMonitor


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """System Monitor - Hardware monitoring tool for CPU, Memory, Disk, Network, and GPU."""
    pass


@cli.command()
@click.option('--refresh-rate', '-r', default=1.0, type=float, help='Dashboard refresh rate in seconds')
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file')
def dashboard(refresh_rate, config):
    """Launch the real-time monitoring dashboard."""
    try:
        cfg = Config(config)
        alert_manager = AlertManager(cfg.get_thresholds())
        dash = Dashboard(refresh_rate=refresh_rate, alert_manager=alert_manager)
        dash.run_dashboard()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'table']), default='table',
              help='Output format')
@click.option('--output', '-o', type=click.Path(), help='Output file (JSON format only)')
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file')
def snapshot(format, output, config):
    """Display a one-time snapshot of system statistics."""
    try:
        cfg = Config(config)
        alert_manager = AlertManager(cfg.get_thresholds())
        dash = Dashboard(alert_manager=alert_manager)

        if format == 'table':
            dash.display_snapshot()
        else:  # json
            snapshot_data = dash.get_snapshot()
            if output:
                with open(output, 'w') as f:
                    json.dump(snapshot_data, f, indent=2, default=str)
                click.echo(f"Snapshot saved to {output}")
            else:
                click.echo(json.dumps(snapshot_data, indent=2, default=str))

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option('--host', '-h', default=None, help='API host address')
@click.option('--port', '-p', default=None, type=int, help='API port number')
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file')
@click.option('--enable-history', is_flag=True, help='Enable historical data logging')
def api(host, port, config, enable_history):
    """Start the REST API server."""
    try:
        cfg = Config(config)

        scheduler = None
        if enable_history:
            click.echo("Historical data logging enabled")
            # Set up background task for data collection
            db = HistoricalDatabase()
            cpu_monitor = CPUMonitor()
            memory_monitor = MemoryMonitor()
            disk_monitor = DiskMonitor()
            network_monitor = NetworkMonitor()
            gpu_monitor = GPUMonitor()

            def collect_data():
                """Background task to collect and store monitoring data."""
                try:
                    db.store_cpu_data(cpu_monitor.get_usage(interval=0.1))
                    db.store_memory_data(memory_monitor.get_memory())
                    db.store_disk_data(disk_monitor.get_complete_stats())
                    db.store_network_data(network_monitor.get_io_counters(per_nic=True))
                    db.store_gpu_data(gpu_monitor.get_all_gpus())
                except Exception as e:
                    click.echo(f"Error collecting data: {e}", err=True)

            scheduler = BackgroundScheduler()
            interval = cfg.get("history.interval_seconds", 5)
            scheduler.add_job(collect_data, 'interval', seconds=interval)
            scheduler.start()

            # Also set up cleanup task
            retention_hours = cfg.get("history.retention_hours", 24)
            scheduler.add_job(
                lambda: db.cleanup_old_data(retention_hours),
                'interval',
                hours=1
            )

        api_instance = MonitoringAPI(cfg)

        click.echo(f"Starting API server on {host or cfg.get('api.host')}:{port or cfg.get('api.port')}")
        click.echo("API documentation available at http://localhost:8000/docs")

        try:
            api_instance.run(host=host, port=port)
        finally:
            if scheduler:
                scheduler.shutdown()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'csv']), default='json',
              help='Export format')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file')
def export(format, output, config):
    """Export current system snapshot to file."""
    try:
        cfg = Config(config)

        # Collect data
        cpu_monitor = CPUMonitor()
        memory_monitor = MemoryMonitor()
        disk_monitor = DiskMonitor()
        network_monitor = NetworkMonitor()
        gpu_monitor = GPUMonitor()

        snapshot_data = {
            "cpu": cpu_monitor.get_usage(interval=0.1),
            "memory": memory_monitor.get_memory(),
            "disk": disk_monitor.get_complete_stats(),
            "network": network_monitor.get_io_counters(per_nic=True),
            "gpu": gpu_monitor.get_all_gpus()
        }

        # Export
        exporter = DataExporter(cfg.get("export.directory", "./exports"))
        filepath = exporter.export_snapshot(snapshot_data, format=format)

        if output:
            # Move to specified path
            Path(filepath).rename(output)
            click.echo(f"Exported to: {output}")
        else:
            click.echo(f"Exported to: {filepath}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument('metric', type=click.Choice(['cpu', 'memory', 'disk', 'network', 'gpu']))
@click.option('--hours', '-h', default=24, type=int, help='Hours of history to retrieve')
@click.option('--limit', '-l', type=int, help='Maximum number of records')
@click.option('--format', '-f', type=click.Choice(['json', 'csv']), default='json',
              help='Output format')
@click.option('--output', '-o', type=click.Path(), help='Output file')
def history(metric, hours, limit, format, output):
    """View historical monitoring data."""
    try:
        db = HistoricalDatabase()
        table_name = f"{metric}_history"

        history_data = db.get_history(table_name, hours=hours, limit=limit)

        if not history_data:
            click.echo(f"No historical data found for {metric}")
            return

        if format == 'json':
            output_data = json.dumps(history_data, indent=2, default=str)
            if output:
                with open(output, 'w') as f:
                    f.write(output_data)
                click.echo(f"History exported to: {output}")
            else:
                click.echo(output_data)
        else:  # csv
            exporter = DataExporter()
            filepath = exporter.export_to_csv(history_data, filename=output)
            click.echo(f"History exported to: {filepath}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file')
def alerts(config):
    """Check current system alerts."""
    try:
        cfg = Config(config)
        alert_manager = AlertManager(cfg.get_thresholds())

        # Collect current data
        cpu_monitor = CPUMonitor()
        memory_monitor = MemoryMonitor()
        disk_monitor = DiskMonitor()
        network_monitor = NetworkMonitor()
        gpu_monitor = GPUMonitor()

        snapshot_data = {
            "cpu": cpu_monitor.get_usage(interval=0.1),
            "memory": memory_monitor.get_memory(),
            "disk": disk_monitor.get_complete_stats(),
            "network": network_monitor.get_io_counters(per_nic=True),
            "gpu": gpu_monitor.get_all_gpus()
        }

        # Check for alerts
        triggered_alerts = alert_manager.check_all(snapshot_data)

        if not triggered_alerts:
            click.echo("No alerts triggered")
        else:
            click.echo(f"Found {len(triggered_alerts)} alert(s):\n")
            for alert in triggered_alerts:
                color = 'red' if alert.level.value == 'critical' else 'yellow'
                click.secho(str(alert), fg=color)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'table']), default='table',
              help='Output format')
@click.option('--server-id', '-s', type=int, help='Specific server ID to test against')
def speedtest(format, server_id):
    """Run an internet speed test."""
    try:
        speed_monitor = SpeedTestMonitor()

        click.echo("Running speed test... (this may take 30-60 seconds)")

        result = speed_monitor.run_speedtest(server_id=server_id)

        if 'error' in result:
            click.echo(f"Error: {result['error']}", err=True)
            if 'details' in result:
                click.echo(f"Details: {result['details']}", err=True)
            return

        if format == 'json':
            click.echo(json.dumps(result, indent=2, default=str))
        else:
            click.echo("\n" + "=" * 60)
            click.echo("Internet Speed Test Results")
            click.echo("=" * 60)
            click.echo(f"\nDownload: {result['download']['formatted']}")
            click.echo(f"Upload:   {result['upload']['formatted']}")
            click.echo(f"Ping:     {result['ping']['formatted']}")

            click.echo(f"\nServer:")
            click.echo(f"  Name:    {result['server']['sponsor']}")
            click.echo(f"  Location: {result['server']['name']}, {result['server']['country']}")
            click.echo(f"  Distance: {result['server']['distance']:.2f} km")

            click.echo(f"\nClient:")
            click.echo(f"  ISP:     {result['client']['isp']}")
            click.echo(f"  IP:      {result['client']['ip']}")
            click.echo(f"  Country: {result['client']['country']}")

            click.echo("=" * 60)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
def info():
    """Display system information and available monitors."""
    try:
        cpu_monitor = CPUMonitor()
        gpu_monitor = GPUMonitor()

        click.echo("System Monitor Information")
        click.echo("=" * 50)
        click.echo(f"\nCPU Cores: {cpu_monitor.cpu_count_physical} physical, "
                   f"{cpu_monitor.cpu_count_logical} logical")
        click.echo(f"GPU Available: {gpu_monitor.is_available()}")

        if gpu_monitor.is_available():
            click.echo(f"GPU Count: {gpu_monitor.get_gpu_count()}")
            gpu_data = gpu_monitor.get_all_gpus()
            if gpu_data.get("driver"):
                click.echo(f"GPU Driver: {gpu_data['driver']}")

        click.echo("\nAvailable Monitors:")
        click.echo("  - CPU (usage, frequency, load average)")
        click.echo("  - Memory (RAM and Swap)")
        click.echo("  - Disk (usage and I/O)")
        click.echo("  - Network (traffic and speed)")
        click.echo("  - Internet Speed (download, upload, ping)")
        if gpu_monitor.is_available():
            click.echo("  - GPU (utilization, memory, temperature)")

        click.echo("\nAvailable Commands:")
        click.echo("  dashboard  - Real-time monitoring dashboard")
        click.echo("  snapshot   - One-time system snapshot")
        click.echo("  api        - Start REST API server")
        click.echo("  speedtest  - Run internet speed test")
        click.echo("  export     - Export current snapshot")
        click.echo("  history    - View historical data")
        click.echo("  alerts     - Check system alerts")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


if __name__ == '__main__':
    cli()
