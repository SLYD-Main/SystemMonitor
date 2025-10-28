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
from src.monitors.gpu_benchmark import GPUBenchmark


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
@click.option('--device-id', '-d', default=0, type=int, help='GPU device ID')
@click.option('--test', '-t', type=click.Choice(['info', 'memory', 'compute', 'stress', 'full']),
              default='full', help='Type of benchmark to run')
@click.option('--format', '-f', type=click.Choice(['json', 'table']), default='table',
              help='Output format')
@click.option('--duration', default=10, type=int, help='Stress test duration in seconds')
def gpu_benchmark(device_id, test, format, duration):
    """Run GPU benchmark tests."""
    try:
        benchmark = GPUBenchmark()

        if not benchmark.is_available():
            click.echo("Error: No GPU or GPU libraries available", err=True)
            click.echo("\nTo enable GPU benchmarks:")
            click.echo("1. Install PyTorch with CUDA: pip install torch torchvision")
            click.echo("2. Or install pynvml: pip install pynvml")
            return

        if not benchmark.torch_available and test != 'info':
            click.echo("Warning: PyTorch with CUDA not available", err=True)
            click.echo("Only GPU info is available. Install PyTorch for compute benchmarks.")
            test = 'info'

        # Run selected benchmark
        if test == 'info':
            result = benchmark.get_gpu_info(device_id)
        elif test == 'memory':
            click.echo(f"Running memory bandwidth benchmark on GPU {device_id}...")
            result = benchmark.benchmark_memory_bandwidth(device_id)
        elif test == 'compute':
            click.echo(f"Running compute performance benchmark on GPU {device_id}...")
            result = benchmark.benchmark_compute_performance(device_id)
        elif test == 'stress':
            click.echo(f"Running stress test on GPU {device_id} for {duration} seconds...")
            result = benchmark.stress_test(device_id, duration_seconds=duration)
        else:  # full
            click.echo(f"Running full benchmark suite on GPU {device_id}...")
            click.echo("This may take 30-60 seconds...\n")
            result = benchmark.run_full_benchmark(device_id)

        # Output results
        if format == 'json':
            click.echo(json.dumps(result, indent=2, default=str))
        else:
            _print_benchmark_results(result, test)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        import traceback
        traceback.print_exc()


def _print_benchmark_results(result: dict, test_type: str):
    """Print benchmark results in table format."""
    if 'error' in result:
        click.echo(f"Error: {result['error']}", err=True)
        if 'message' in result:
            click.echo(result['message'])
        return

    click.echo("\n" + "=" * 70)
    click.echo("GPU Benchmark Results")
    click.echo("=" * 70)

    # GPU Info
    if 'gpu_info' in result:
        info = result['gpu_info']
        click.echo(f"\nGPU: {info.get('name', 'Unknown')}")
        if 'total_memory_gb' in info:
            click.echo(f"Memory: {info['total_memory_gb']:.2f} GB")
        if 'compute_capability' in info:
            click.echo(f"Compute Capability: {info['compute_capability']}")
        if 'multi_processor_count' in info:
            click.echo(f"Multiprocessors: {info['multi_processor_count']}")

    # Info only
    if test_type == 'info':
        click.echo(f"\nDevice ID: {result.get('device_id', 0)}")
        click.echo(f"Name: {result.get('name', 'Unknown')}")
        if 'total_memory_gb' in result:
            click.echo(f"Total Memory: {result['total_memory_gb']:.2f} GB")
        if 'compute_capability' in result:
            click.echo(f"Compute Capability: {result['compute_capability']}")
        click.echo("=" * 70)
        return

    # Memory Bandwidth
    if 'benchmarks' in result and 'memory_bandwidth' in result['benchmarks']:
        mem = result['benchmarks']['memory_bandwidth']
        if 'tests' in mem:
            click.echo("\nMemory Bandwidth:")
            if 'host_to_device' in mem['tests']:
                h2d = mem['tests']['host_to_device']
                click.echo(f"  Host -> Device: {h2d['bandwidth_gb_per_sec']:.2f} GB/s")
            if 'device_to_host' in mem['tests']:
                d2h = mem['tests']['device_to_host']
                click.echo(f"  Device -> Host: {d2h['bandwidth_gb_per_sec']:.2f} GB/s")
            if 'device_to_device' in mem['tests']:
                d2d = mem['tests']['device_to_device']
                click.echo(f"  Device -> Device: {d2d['bandwidth_gb_per_sec']:.2f} GB/s")
    elif test_type == 'memory' and 'tests' in result:
        click.echo("\nMemory Bandwidth:")
        if 'host_to_device' in result['tests']:
            h2d = result['tests']['host_to_device']
            click.echo(f"  Host -> Device: {h2d['bandwidth_gb_per_sec']:.2f} GB/s")
        if 'device_to_host' in result['tests']:
            d2h = result['tests']['device_to_host']
            click.echo(f"  Device -> Host: {d2h['bandwidth_gb_per_sec']:.2f} GB/s")
        if 'device_to_device' in result['tests']:
            d2d = result['tests']['device_to_device']
            click.echo(f"  Device -> Device: {d2d['bandwidth_gb_per_sec']:.2f} GB/s")

    # Compute Performance
    if 'benchmarks' in result and 'compute_performance' in result['benchmarks']:
        compute = result['benchmarks']['compute_performance']
        if 'operations' in compute:
            click.echo("\nCompute Performance:")
            if 'matmul_fp32' in compute['operations']:
                matmul = compute['operations']['matmul_fp32']
                click.echo(f"  Matrix Multiply (FP32): {matmul['tflops']:.2f} TFLOPS")
                click.echo(f"  Average Time: {matmul['avg_time_seconds']*1000:.2f} ms")
    elif test_type == 'compute' and 'operations' in result:
        click.echo("\nCompute Performance:")
        if 'matmul_fp32' in result['operations']:
            matmul = result['operations']['matmul_fp32']
            click.echo(f"  Matrix Multiply (FP32): {matmul['tflops']:.2f} TFLOPS")
            click.echo(f"  Average Time: {matmul['avg_time_seconds']*1000:.2f} ms")

    # Stress Test
    if 'benchmarks' in result and 'stress_test' in result['benchmarks']:
        stress = result['benchmarks']['stress_test']
        if 'statistics' in stress:
            click.echo("\nStress Test Results:")
            stats = stress['statistics']
            click.echo(f"  Iterations: {stats['iterations']}")
            if 'temperature' in stats:
                temp = stats['temperature']
                click.echo(f"  Temperature: Min={temp['min']}°C, Max={temp['max']}°C, Avg={temp['avg']:.1f}°C")
            if stats.get('power'):
                power = stats['power']
                click.echo(f"  Power: Min={power['min']:.1f}W, Max={power['max']:.1f}W, Avg={power['avg']:.1f}W")
            if stats.get('utilization'):
                util = stats['utilization']
                click.echo(f"  Utilization: Min={util['min']}%, Max={util['max']}%, Avg={util['avg']:.1f}%")
    elif test_type == 'stress' and 'statistics' in result:
        click.echo("\nStress Test Results:")
        stats = result['statistics']
        click.echo(f"  Iterations: {stats['iterations']}")
        if 'temperature' in stats:
            temp = stats['temperature']
            click.echo(f"  Temperature: Min={temp['min']}°C, Max={temp['max']}°C, Avg={temp['avg']:.1f}°C")
        if stats.get('power'):
            power = stats['power']
            click.echo(f"  Power: Min={power['min']:.1f}W, Max={power['max']:.1f}W, Avg={power['avg']:.1f}W")
        if stats.get('utilization'):
            util = stats['utilization']
            click.echo(f"  Utilization: Min={util['min']}%, Max={util['max']}%, Avg={util['avg']:.1f}%")

    click.echo("=" * 70)


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
        click.echo("  dashboard     - Real-time monitoring dashboard")
        click.echo("  snapshot      - One-time system snapshot")
        click.echo("  api           - Start REST API server")
        click.echo("  speedtest     - Run internet speed test")
        click.echo("  gpu-benchmark - Run GPU performance benchmarks")
        click.echo("  export        - Export current snapshot")
        click.echo("  history       - View historical data")
        click.echo("  alerts        - Check system alerts")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


if __name__ == '__main__':
    cli()
