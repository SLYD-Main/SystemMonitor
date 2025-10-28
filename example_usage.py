#!/usr/bin/env python3
"""
Example usage of the System Monitor library.

This script demonstrates how to use the monitoring modules programmatically.
"""
from src.monitors.cpu import CPUMonitor
from src.monitors.memory import MemoryMonitor
from src.monitors.disk import DiskMonitor
from src.monitors.network import NetworkMonitor
from src.monitors.gpu import GPUMonitor
from src.alerts.alert_manager import AlertManager
from src.config import Config
import json


def main():
    """Example usage of monitoring modules."""
    print("System Monitor - Example Usage\n")
    print("=" * 60)

    # Initialize monitors
    cpu = CPUMonitor()
    memory = MemoryMonitor()
    disk = DiskMonitor()
    network = NetworkMonitor()
    gpu = GPUMonitor()

    # Initialize config and alert manager
    config = Config()
    alert_manager = AlertManager(config.get_thresholds())

    # 1. Get CPU information
    print("\n1. CPU Information:")
    print("-" * 60)
    cpu_data = cpu.get_usage(interval=1.0, per_cpu=False)
    print(f"   CPU Usage: {cpu_data['usage_percent']:.1f}%")
    print(f"   Physical Cores: {cpu_data['cpu_count']['physical']}")
    print(f"   Logical Cores: {cpu_data['cpu_count']['logical']}")
    if cpu_data.get('frequency'):
        print(f"   Current Frequency: {cpu_data['frequency']['current']:.0f} MHz")

    # 2. Get Memory information
    print("\n2. Memory Information:")
    print("-" * 60)
    memory_data = memory.get_memory()
    virtual = memory_data['virtual']
    print(f"   RAM Usage: {virtual['percent']:.1f}%")
    print(f"   RAM Used: {virtual['used'] / (1024**3):.2f} GB")
    print(f"   RAM Total: {virtual['total'] / (1024**3):.2f} GB")
    print(f"   RAM Available: {virtual['available'] / (1024**3):.2f} GB")

    # 3. Get Disk information
    print("\n3. Disk Information:")
    print("-" * 60)
    disk_data = disk.get_complete_stats()
    for partition in disk_data['partitions'][:3]:  # Show first 3 partitions
        usage = partition['usage']
        if 'error' not in usage:
            print(f"   Mount: {partition['mountpoint']}")
            print(f"   Usage: {usage['percent']:.1f}%")
            print(f"   Total: {usage['total'] / (1024**3):.2f} GB")
            print()

    # 4. Get Network information
    print("4. Network Information:")
    print("-" * 60)
    network_data = network.get_io_counters(per_nic=True)
    interfaces = network_data['interfaces']
    for iface_name, iface_data in list(interfaces.items())[:3]:  # Show first 3 interfaces
        print(f"   Interface: {iface_name}")
        print(f"   Sent: {iface_data['bytes_sent'] / (1024**2):.2f} MB")
        print(f"   Received: {iface_data['bytes_recv'] / (1024**2):.2f} MB")
        print()

    # 5. Get GPU information (if available)
    print("5. GPU Information:")
    print("-" * 60)
    gpu_data = gpu.get_all_gpus()
    if gpu_data['available']:
        print(f"   Driver Version: {gpu_data.get('driver', 'N/A')}")
        for gpu_info in gpu_data['gpus']:
            if 'error' not in gpu_info:
                print(f"   GPU {gpu_info['index']}: {gpu_info['name']}")
                print(f"   Utilization: {gpu_info['utilization']['gpu']:.1f}%")
                print(f"   Memory Usage: {gpu_info['memory']['percent']:.1f}%")
                if gpu_info.get('temperature'):
                    print(f"   Temperature: {gpu_info['temperature']}°C")
                print()
    else:
        print("   No GPU available or drivers not installed")

    # 6. Check for alerts
    print("\n6. Alerts:")
    print("-" * 60)
    monitoring_data = {
        "cpu": cpu_data,
        "memory": memory_data,
        "disk": disk_data,
        "gpu": gpu_data
    }

    alerts = alert_manager.check_all(monitoring_data)
    if alerts:
        print(f"   Found {len(alerts)} alert(s):")
        for alert in alerts:
            print(f"   [{alert.level.value.upper()}] {alert.message}")
    else:
        print("   No alerts triggered - system is healthy!")

    # 7. Export snapshot to JSON
    print("\n7. Exporting snapshot to JSON:")
    print("-" * 60)
    snapshot = {
        "cpu": cpu_data,
        "memory": memory_data,
        "disk": disk_data,
        "network": network_data,
        "gpu": gpu_data
    }

    with open("snapshot_example.json", "w") as f:
        json.dump(snapshot, f, indent=2, default=str)
    print("   Snapshot exported to: snapshot_example.json")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("\nFor more features, try:")
    print("  - python main.py dashboard    # Real-time dashboard")
    print("  - python main.py api          # REST API server")
    print("  - python main.py --help       # Show all commands")


if __name__ == "__main__":
    main()
