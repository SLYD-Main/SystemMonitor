"""Prometheus metrics exporter for system monitoring."""
from prometheus_client import Counter, Gauge, Histogram, Info, generate_latest, CONTENT_TYPE_LATEST
from typing import Dict, Optional
import time

from ..monitors.cpu import CPUMonitor
from ..monitors.memory import MemoryMonitor
from ..monitors.disk import DiskMonitor
from ..monitors.network import NetworkMonitor
from ..monitors.gpu import GPUMonitor


class PrometheusExporter:
    """Export system metrics in Prometheus format."""

    def __init__(self):
        """Initialize Prometheus metrics."""
        # CPU Metrics
        self.cpu_percent = Gauge('system_cpu_percent', 'CPU usage percentage', ['cpu'])
        self.cpu_frequency = Gauge('system_cpu_frequency_mhz', 'CPU frequency in MHz', ['cpu', 'type'])
        self.cpu_count = Gauge('system_cpu_count', 'Number of CPUs', ['type'])
        self.cpu_load_avg = Gauge('system_cpu_load_average', 'CPU load average', ['interval'])

        # Memory Metrics
        self.memory_total = Gauge('system_memory_total_bytes', 'Total memory in bytes')
        self.memory_available = Gauge('system_memory_available_bytes', 'Available memory in bytes')
        self.memory_used = Gauge('system_memory_used_bytes', 'Used memory in bytes')
        self.memory_percent = Gauge('system_memory_percent', 'Memory usage percentage')
        self.swap_total = Gauge('system_swap_total_bytes', 'Total swap in bytes')
        self.swap_used = Gauge('system_swap_used_bytes', 'Used swap in bytes')
        self.swap_percent = Gauge('system_swap_percent', 'Swap usage percentage')

        # Disk Metrics
        self.disk_total = Gauge('system_disk_total_bytes', 'Total disk space in bytes', ['device', 'mountpoint'])
        self.disk_used = Gauge('system_disk_used_bytes', 'Used disk space in bytes', ['device', 'mountpoint'])
        self.disk_free = Gauge('system_disk_free_bytes', 'Free disk space in bytes', ['device', 'mountpoint'])
        self.disk_percent = Gauge('system_disk_percent', 'Disk usage percentage', ['device', 'mountpoint'])
        self.disk_read_bytes = Counter('system_disk_read_bytes_total', 'Total bytes read from disk', ['device'])
        self.disk_write_bytes = Counter('system_disk_write_bytes_total', 'Total bytes written to disk', ['device'])
        self.disk_read_count = Counter('system_disk_read_count_total', 'Total read operations', ['device'])
        self.disk_write_count = Counter('system_disk_write_count_total', 'Total write operations', ['device'])

        # Network Metrics
        self.network_bytes_sent = Counter('system_network_bytes_sent_total', 'Total bytes sent', ['interface'])
        self.network_bytes_recv = Counter('system_network_bytes_recv_total', 'Total bytes received', ['interface'])
        self.network_packets_sent = Counter('system_network_packets_sent_total', 'Total packets sent', ['interface'])
        self.network_packets_recv = Counter('system_network_packets_recv_total', 'Total packets received', ['interface'])
        self.network_errors_in = Counter('system_network_errors_in_total', 'Total incoming errors', ['interface'])
        self.network_errors_out = Counter('system_network_errors_out_total', 'Total outgoing errors', ['interface'])
        self.network_drops_in = Counter('system_network_drops_in_total', 'Total incoming drops', ['interface'])
        self.network_drops_out = Counter('system_network_drops_out_total', 'Total outgoing drops', ['interface'])

        # GPU Metrics
        self.gpu_temperature = Gauge('system_gpu_temperature_celsius', 'GPU temperature in Celsius', ['gpu_id', 'gpu_name'])
        self.gpu_utilization = Gauge('system_gpu_utilization_percent', 'GPU utilization percentage', ['gpu_id', 'gpu_name'])
        self.gpu_memory_total = Gauge('system_gpu_memory_total_mb', 'Total GPU memory in MB', ['gpu_id', 'gpu_name'])
        self.gpu_memory_used = Gauge('system_gpu_memory_used_mb', 'Used GPU memory in MB', ['gpu_id', 'gpu_name'])
        self.gpu_memory_free = Gauge('system_gpu_memory_free_mb', 'Free GPU memory in MB', ['gpu_id', 'gpu_name'])
        self.gpu_memory_percent = Gauge('system_gpu_memory_percent', 'GPU memory usage percentage', ['gpu_id', 'gpu_name'])
        self.gpu_power_draw = Gauge('system_gpu_power_draw_watts', 'GPU power draw in watts', ['gpu_id', 'gpu_name'])
        self.gpu_power_limit = Gauge('system_gpu_power_limit_watts', 'GPU power limit in watts', ['gpu_id', 'gpu_name'])
        self.gpu_clock_graphics = Gauge('system_gpu_clock_graphics_mhz', 'GPU graphics clock in MHz', ['gpu_id', 'gpu_name'])
        self.gpu_clock_memory = Gauge('system_gpu_clock_memory_mhz', 'GPU memory clock in MHz', ['gpu_id', 'gpu_name'])
        self.gpu_fan_speed = Gauge('system_gpu_fan_speed_percent', 'GPU fan speed percentage', ['gpu_id', 'gpu_name'])

        # System Info
        self.system_info = Info('system_monitor', 'System monitor information')

        # Initialize monitors
        self.cpu_monitor = CPUMonitor()
        self.memory_monitor = MemoryMonitor()
        self.disk_monitor = DiskMonitor()
        self.network_monitor = NetworkMonitor()
        self.gpu_monitor = GPUMonitor()

        # Store last network/disk values for counter updates
        self.last_network_counters = {}
        self.last_disk_counters = {}

    def update_metrics(self):
        """Update all Prometheus metrics with current system values."""
        self._update_cpu_metrics()
        self._update_memory_metrics()
        self._update_disk_metrics()
        self._update_network_metrics()
        self._update_gpu_metrics()

    def _update_cpu_metrics(self):
        """Update CPU metrics."""
        try:
            # Overall CPU usage
            cpu_data = self.cpu_monitor.get_usage(interval=0.1, per_cpu=True)

            if 'overall' in cpu_data:
                self.cpu_percent.labels(cpu='overall').set(cpu_data['overall'])

            # Per-CPU usage
            if 'per_cpu' in cpu_data:
                for i, percent in enumerate(cpu_data['per_cpu']):
                    self.cpu_percent.labels(cpu=f'cpu{i}').set(percent)

            # CPU stats
            stats = self.cpu_monitor.get_stats()

            # CPU count
            if 'cpu_count' in stats:
                self.cpu_count.labels(type='logical').set(stats['cpu_count'].get('logical', 0))
                self.cpu_count.labels(type='physical').set(stats['cpu_count'].get('physical', 0))

            # CPU frequency
            if 'frequency' in stats:
                freq = stats['frequency']
                self.cpu_frequency.labels(cpu='overall', type='current').set(freq.get('current', 0))
                self.cpu_frequency.labels(cpu='overall', type='min').set(freq.get('min', 0))
                self.cpu_frequency.labels(cpu='overall', type='max').set(freq.get('max', 0))

            # Load average
            if 'load_average' in stats:
                load = stats['load_average']
                self.cpu_load_avg.labels(interval='1min').set(load.get('1min', 0))
                self.cpu_load_avg.labels(interval='5min').set(load.get('5min', 0))
                self.cpu_load_avg.labels(interval='15min').set(load.get('15min', 0))

        except Exception as e:
            print(f"Error updating CPU metrics: {e}")

    def _update_memory_metrics(self):
        """Update memory metrics."""
        try:
            memory_data = self.memory_monitor.get_memory()

            # Virtual memory
            if 'virtual' in memory_data:
                vm = memory_data['virtual']
                self.memory_total.set(vm.get('total', 0))
                self.memory_available.set(vm.get('available', 0))
                self.memory_used.set(vm.get('used', 0))
                self.memory_percent.set(vm.get('percent', 0))

            # Swap memory
            if 'swap' in memory_data:
                swap = memory_data['swap']
                self.swap_total.set(swap.get('total', 0))
                self.swap_used.set(swap.get('used', 0))
                self.swap_percent.set(swap.get('percent', 0))

        except Exception as e:
            print(f"Error updating memory metrics: {e}")

    def _update_disk_metrics(self):
        """Update disk metrics."""
        try:
            disk_data = self.disk_monitor.get_complete_stats()

            # Disk usage by partition
            if 'partitions' in disk_data:
                for partition in disk_data['partitions']:
                    device = partition.get('device', 'unknown')
                    mountpoint = partition.get('mountpoint', 'unknown')
                    usage = partition.get('usage', {})

                    self.disk_total.labels(device=device, mountpoint=mountpoint).set(usage.get('total', 0))
                    self.disk_used.labels(device=device, mountpoint=mountpoint).set(usage.get('used', 0))
                    self.disk_free.labels(device=device, mountpoint=mountpoint).set(usage.get('free', 0))
                    self.disk_percent.labels(device=device, mountpoint=mountpoint).set(usage.get('percent', 0))

            # Disk I/O counters
            if 'io_counters' in disk_data:
                for device, counters in disk_data['io_counters'].items():
                    # Use counter's _value attribute or set directly
                    read_bytes = counters.get('read_bytes', 0)
                    write_bytes = counters.get('write_bytes', 0)
                    read_count = counters.get('read_count', 0)
                    write_count = counters.get('write_count', 0)

                    # Store current values and calculate delta
                    if device in self.last_disk_counters:
                        last = self.last_disk_counters[device]
                        if read_bytes >= last['read_bytes']:
                            self.disk_read_bytes.labels(device=device).inc(read_bytes - last['read_bytes'])
                        if write_bytes >= last['write_bytes']:
                            self.disk_write_bytes.labels(device=device).inc(write_bytes - last['write_bytes'])
                        if read_count >= last['read_count']:
                            self.disk_read_count.labels(device=device).inc(read_count - last['read_count'])
                        if write_count >= last['write_count']:
                            self.disk_write_count.labels(device=device).inc(write_count - last['write_count'])

                    self.last_disk_counters[device] = {
                        'read_bytes': read_bytes,
                        'write_bytes': write_bytes,
                        'read_count': read_count,
                        'write_count': write_count
                    }

        except Exception as e:
            print(f"Error updating disk metrics: {e}")

    def _update_network_metrics(self):
        """Update network metrics."""
        try:
            network_data = self.network_monitor.get_io_counters(per_nic=True)

            for interface, counters in network_data.items():
                if interface == 'total':
                    continue

                bytes_sent = counters.get('bytes_sent', 0)
                bytes_recv = counters.get('bytes_recv', 0)
                packets_sent = counters.get('packets_sent', 0)
                packets_recv = counters.get('packets_recv', 0)
                errin = counters.get('errin', 0)
                errout = counters.get('errout', 0)
                dropin = counters.get('dropin', 0)
                dropout = counters.get('dropout', 0)

                # Calculate deltas and update counters
                if interface in self.last_network_counters:
                    last = self.last_network_counters[interface]
                    if bytes_sent >= last['bytes_sent']:
                        self.network_bytes_sent.labels(interface=interface).inc(bytes_sent - last['bytes_sent'])
                    if bytes_recv >= last['bytes_recv']:
                        self.network_bytes_recv.labels(interface=interface).inc(bytes_recv - last['bytes_recv'])
                    if packets_sent >= last['packets_sent']:
                        self.network_packets_sent.labels(interface=interface).inc(packets_sent - last['packets_sent'])
                    if packets_recv >= last['packets_recv']:
                        self.network_packets_recv.labels(interface=interface).inc(packets_recv - last['packets_recv'])
                    if errin >= last['errin']:
                        self.network_errors_in.labels(interface=interface).inc(errin - last['errin'])
                    if errout >= last['errout']:
                        self.network_errors_out.labels(interface=interface).inc(errout - last['errout'])
                    if dropin >= last['dropin']:
                        self.network_drops_in.labels(interface=interface).inc(dropin - last['dropin'])
                    if dropout >= last['dropout']:
                        self.network_drops_out.labels(interface=interface).inc(dropout - last['dropout'])

                self.last_network_counters[interface] = {
                    'bytes_sent': bytes_sent,
                    'bytes_recv': bytes_recv,
                    'packets_sent': packets_sent,
                    'packets_recv': packets_recv,
                    'errin': errin,
                    'errout': errout,
                    'dropin': dropin,
                    'dropout': dropout
                }

        except Exception as e:
            print(f"Error updating network metrics: {e}")

    def _update_gpu_metrics(self):
        """Update GPU metrics."""
        try:
            if not self.gpu_monitor.is_available():
                return

            gpu_data = self.gpu_monitor.get_all_gpus()

            if 'gpus' in gpu_data:
                for gpu in gpu_data['gpus']:
                    gpu_id = str(gpu.get('id', 0))
                    gpu_name = gpu.get('name', 'unknown')

                    # Temperature
                    if 'temperature' in gpu and gpu['temperature'] is not None:
                        self.gpu_temperature.labels(gpu_id=gpu_id, gpu_name=gpu_name).set(gpu['temperature'])

                    # Utilization
                    if 'utilization' in gpu and gpu['utilization'] is not None:
                        self.gpu_utilization.labels(gpu_id=gpu_id, gpu_name=gpu_name).set(gpu['utilization'])

                    # Memory
                    if 'memory' in gpu:
                        mem = gpu['memory']
                        self.gpu_memory_total.labels(gpu_id=gpu_id, gpu_name=gpu_name).set(mem.get('total', 0))
                        self.gpu_memory_used.labels(gpu_id=gpu_id, gpu_name=gpu_name).set(mem.get('used', 0))
                        self.gpu_memory_free.labels(gpu_id=gpu_id, gpu_name=gpu_name).set(mem.get('free', 0))
                        self.gpu_memory_percent.labels(gpu_id=gpu_id, gpu_name=gpu_name).set(mem.get('percent', 0))

                    # Power
                    if 'power_draw' in gpu and gpu['power_draw'] is not None:
                        self.gpu_power_draw.labels(gpu_id=gpu_id, gpu_name=gpu_name).set(gpu['power_draw'])
                    if 'power_limit' in gpu and gpu['power_limit'] is not None:
                        self.gpu_power_limit.labels(gpu_id=gpu_id, gpu_name=gpu_name).set(gpu['power_limit'])

                    # Clock speeds
                    if 'clocks' in gpu:
                        clocks = gpu['clocks']
                        if 'graphics' in clocks and clocks['graphics'] is not None:
                            self.gpu_clock_graphics.labels(gpu_id=gpu_id, gpu_name=gpu_name).set(clocks['graphics'])
                        if 'memory' in clocks and clocks['memory'] is not None:
                            self.gpu_clock_memory.labels(gpu_id=gpu_id, gpu_name=gpu_name).set(clocks['memory'])

                    # Fan speed
                    if 'fan_speed' in gpu and gpu['fan_speed'] is not None:
                        self.gpu_fan_speed.labels(gpu_id=gpu_id, gpu_name=gpu_name).set(gpu['fan_speed'])

        except Exception as e:
            print(f"Error updating GPU metrics: {e}")

    def generate_metrics(self) -> bytes:
        """
        Generate Prometheus metrics.

        Returns:
            Metrics in Prometheus text format
        """
        self.update_metrics()
        return generate_latest()

    def get_content_type(self) -> str:
        """Get the content type for Prometheus metrics."""
        return CONTENT_TYPE_LATEST
