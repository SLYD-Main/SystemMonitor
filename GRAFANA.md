# Grafana Dashboard Guide

System Monitor includes pre-built Grafana dashboards for visualizing system and GPU metrics in real-time.

## Table of Contents
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Accessing Dashboards](#accessing-dashboards)
- [Available Dashboards](#available-dashboards)
- [Metrics Reference](#metrics-reference)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Automatic Installation (Recommended)

Install System Monitor with Grafana in one command:

```bash
curl -fsSL https://raw.githubusercontent.com/SLYD-Main/SystemMonitor/master/bootstrap.sh \
| sudo bash -s -- \
  --non-interactive \
  --enable-history \
  --install-pytorch \
  --install-grafana
```

After installation:
1. Access Grafana at: `http://your-server-ip:3000`
2. Login with: `admin` / `admin` (you'll be prompted to change password)
3. Navigate to Dashboards → System Monitor folder
4. Open "System Overview" or "GPU Monitoring" dashboards

### Manual Installation

If you already have System Monitor installed:

```bash
cd /opt/SystemMonitor
sudo ./install_grafana.sh
```

## Installation

### What Gets Installed

The Grafana installation includes:

1. **Prometheus** (port 9090)
   - Time-series database for metrics
   - Scrapes `/metrics` endpoint from System Monitor API
   - 15-day data retention by default

2. **Grafana** (port 3000)
   - Visualization and dashboard platform
   - Pre-configured Prometheus datasource
   - Two pre-built dashboards

3. **Dashboards**
   - System Overview: CPU, Memory, Disk, Network
   - GPU Monitoring: Temperature, Utilization, Memory, Power

### Installation Options

```bash
# With custom ports
curl -fsSL https://raw.githubusercontent.com/SLYD-Main/SystemMonitor/master/bootstrap.sh \
| sudo bash -s -- \
  --install-grafana \
  --prometheus-port 9090 \
  --grafana-port 3000

# Standalone Grafana installation
sudo /opt/SystemMonitor/install_grafana.sh
```

### Requirements

- Ubuntu 20.04+ or Debian-based system
- System Monitor API running on port 8000
- 500MB free disk space
- Root/sudo access

## Accessing Dashboards

### First Login

1. Open browser to `http://your-server-ip:3000`
2. Login with default credentials:
   - **Username**: `admin`
   - **Password**: `admin`
3. You'll be prompted to set a new password
4. Click on the dashboard icon (four squares) in the left sidebar
5. Navigate to "System Monitor" folder
6. Select a dashboard

### Direct URLs

After installation, dashboards are available at:

```
System Overview:
http://your-server-ip:3000/d/system-overview

GPU Monitoring:
http://your-server-ip:3000/d/gpu-monitoring

Prometheus:
http://your-server-ip:9090
```

## Available Dashboards

### 1. System Overview Dashboard

**Purpose**: Real-time monitoring of system resources

**Panels**:
- **CPU Usage Gauge**: Overall CPU utilization percentage
- **Memory Usage Gauge**: RAM utilization percentage
- **Disk Usage Gauge**: Root filesystem usage
- **CPU Frequency**: Current CPU clock speeds
- **CPU Usage Per Core**: Individual core utilization over time
- **Memory Usage**: Used vs Available memory over time
- **Network Traffic**: Bytes sent/received per interface
- **Disk I/O**: Read/write operations per device

**Refresh Rate**: 10 seconds
**Default Time Range**: Last 1 hour

**Use Cases**:
- System performance monitoring
- Resource capacity planning
- Troubleshooting performance issues
- Identifying resource bottlenecks

### 2. GPU Monitoring Dashboard

**Purpose**: Comprehensive GPU metrics and performance

**Panels**:
- **GPU Temperature Gauge**: Current temperature with thresholds
- **GPU Utilization Gauge**: Compute utilization percentage
- **GPU Memory Usage Gauge**: VRAM utilization
- **GPU Power Draw Gauge**: Current power consumption
- **Temperature Over Time**: Thermal behavior tracking
- **Utilization Over Time**: Workload patterns
- **Memory Usage**: Used/Free VRAM trends
- **Power Consumption**: Power draw vs limit
- **Clock Speeds**: Graphics and memory clock frequencies
- **Fan Speed**: Cooling system monitoring

**Refresh Rate**: 10 seconds
**Default Time Range**: Last 1 hour

**Use Cases**:
- GPU stress testing monitoring
- Thermal throttling detection
- Performance benchmarking
- Power consumption analysis
- Multi-GPU comparison

## Metrics Reference

### CPU Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| `system_cpu_percent` | CPU utilization percentage | percent |
| `system_cpu_frequency_mhz` | CPU clock frequency | MHz |
| `system_cpu_count` | Number of CPU cores | count |
| `system_cpu_load_average` | System load average | float |

### Memory Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| `system_memory_total_bytes` | Total RAM | bytes |
| `system_memory_used_bytes` | Used RAM | bytes |
| `system_memory_available_bytes` | Available RAM | bytes |
| `system_memory_percent` | Memory utilization | percent |
| `system_swap_total_bytes` | Total swap space | bytes |
| `system_swap_used_bytes` | Used swap space | bytes |
| `system_swap_percent` | Swap utilization | percent |

### Disk Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| `system_disk_total_bytes` | Total disk space | bytes |
| `system_disk_used_bytes` | Used disk space | bytes |
| `system_disk_free_bytes` | Free disk space | bytes |
| `system_disk_percent` | Disk utilization | percent |
| `system_disk_read_bytes_total` | Bytes read (counter) | bytes |
| `system_disk_write_bytes_total` | Bytes written (counter) | bytes |

### Network Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| `system_network_bytes_sent_total` | Bytes transmitted (counter) | bytes |
| `system_network_bytes_recv_total` | Bytes received (counter) | bytes |
| `system_network_packets_sent_total` | Packets transmitted | count |
| `system_network_packets_recv_total` | Packets received | count |
| `system_network_errors_in_total` | Incoming errors | count |
| `system_network_errors_out_total` | Outgoing errors | count |

### GPU Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| `system_gpu_temperature_celsius` | GPU temperature | celsius |
| `system_gpu_utilization_percent` | GPU compute usage | percent |
| `system_gpu_memory_total_mb` | Total VRAM | MB |
| `system_gpu_memory_used_mb` | Used VRAM | MB |
| `system_gpu_memory_free_mb` | Free VRAM | MB |
| `system_gpu_memory_percent` | VRAM utilization | percent |
| `system_gpu_power_draw_watts` | Current power draw | watts |
| `system_gpu_power_limit_watts` | Power limit | watts |
| `system_gpu_clock_graphics_mhz` | Graphics clock | MHz |
| `system_gpu_clock_memory_mhz` | Memory clock | MHz |
| `system_gpu_fan_speed_percent` | Fan speed | percent |

## Customization

### Creating Custom Dashboards

1. In Grafana, click "+" → "Dashboard"
2. Add Panel → Add Visualization
3. Select "Prometheus" as datasource
4. Enter a Prometheus query (e.g., `system_cpu_percent{cpu="overall"}`)
5. Configure visualization type and options
6. Save dashboard

### Example Queries

**CPU Usage by Core**:
```promql
system_cpu_percent{cpu!="overall"}
```

**Memory Usage Percentage**:
```promql
system_memory_percent
```

**Network Traffic Rate**:
```promql
rate(system_network_bytes_sent_total[1m])
```

**GPU Temperature (All GPUs)**:
```promql
system_gpu_temperature_celsius
```

**GPU Memory Used (GB)**:
```promql
system_gpu_memory_used_mb / 1024
```

**Disk I/O Rate (MB/s)**:
```promql
rate(system_disk_read_bytes_total[1m]) / 1024 / 1024
```

### Modifying Dashboards

1. Open a dashboard
2. Click gear icon (⚙️) → Settings
3. Make changes to panels, variables, or layout
4. Click "Save dashboard"

### Alerting

Configure alerts to notify when thresholds are exceeded:

1. Edit a panel
2. Click "Alert" tab
3. Create alert rule with conditions
4. Configure notification channels
5. Save

**Example Alert**: CPU > 90% for 5 minutes

```
WHEN max() OF query(A, 5m, now) IS ABOVE 90
```

## Troubleshooting

### Dashboards Not Showing Data

**Check if System Monitor API is running**:
```bash
curl http://localhost:8000/metrics
```

You should see Prometheus metrics. If not:
```bash
sudo systemctl status system-monitor
sudo systemctl restart system-monitor
```

**Check if Prometheus is scraping**:
1. Open http://your-server-ip:9090
2. Go to Status → Targets
3. Verify "system-monitor" target is UP

If DOWN:
```bash
sudo systemctl status prometheus
sudo journalctl -u prometheus -n 50
```

**Check Prometheus configuration**:
```bash
cat /opt/prometheus/prometheus.yml
```

Verify the `system-monitor` job targets `localhost:8000`.

### Grafana Not Accessible

**Check Grafana service**:
```bash
sudo systemctl status grafana-server
```

If not running:
```bash
sudo systemctl start grafana-server
```

**Check firewall**:
```bash
sudo ufw status
sudo ufw allow 3000/tcp
```

**Check port binding**:
```bash
sudo netstat -tlnp | grep 3000
```

### Prometheus Scrape Errors

**Check System Monitor /metrics endpoint**:
```bash
curl -v http://localhost:8000/metrics
```

**Verify prometheus-client installed**:
```bash
cd /opt/SystemMonitor
source venv/bin/activate
pip list | grep prometheus-client
```

If not installed:
```bash
pip install prometheus-client
sudo systemctl restart system-monitor
```

### GPU Metrics Missing

**Check if GPU monitoring is working**:
```bash
curl http://localhost:8000/api/gpu | jq '.'
```

**Verify NVIDIA drivers**:
```bash
nvidia-smi
```

**Check pynvml**:
```bash
cd /opt/SystemMonitor
source venv/bin/activate
python -c "import pynvml; pynvml.nvmlInit(); print('OK')"
```

### Dashboard Load Errors

**Check Grafana logs**:
```bash
sudo journalctl -u grafana-server -f
```

**Verify dashboard files**:
```bash
ls -l /var/lib/grafana/dashboards/
```

**Re-import dashboards**:
1. Go to Dashboards → Import
2. Upload dashboard JSON from `/opt/SystemMonitor/grafana/dashboards/`

### High Memory Usage

Prometheus stores time-series data in memory. To reduce usage:

**Edit retention policy**:
```bash
sudo nano /etc/systemd/system/prometheus.service
```

Add to ExecStart:
```
--storage.tsdb.retention.time=7d
```

Restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart prometheus
```

## Advanced Configuration

### Custom Scrape Intervals

Edit `/opt/prometheus/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'system-monitor'
    scrape_interval: 5s  # Faster updates
    static_configs:
      - targets: ['localhost:8000']
```

Restart Prometheus:
```bash
sudo systemctl restart prometheus
```

### Multiple System Monitor Instances

Add multiple targets to Prometheus:

```yaml
scrape_configs:
  - job_name: 'system-monitor'
    static_configs:
      - targets:
        - 'server1:8000'
        - 'server2:8000'
        - 'server3:8000'
```

### HTTPS for Grafana

1. Generate SSL certificate
2. Edit `/etc/grafana/grafana.ini`:

```ini
[server]
protocol = https
cert_file = /path/to/cert.pem
cert_key = /path/to/key.pem
```

3. Restart Grafana:
```bash
sudo systemctl restart grafana-server
```

### Authentication

Configure authentication in `/etc/grafana/grafana.ini`:

```ini
[auth.anonymous]
enabled = false

[auth.basic]
enabled = true
```

## Service Management

### Systemd Commands

**Prometheus**:
```bash
sudo systemctl status prometheus
sudo systemctl start prometheus
sudo systemctl stop prometheus
sudo systemctl restart prometheus
sudo journalctl -u prometheus -f
```

**Grafana**:
```bash
sudo systemctl status grafana-server
sudo systemctl start grafana-server
sudo systemctl stop grafana-server
sudo systemctl restart grafana-server
sudo journalctl -u grafana-server -f
```

**System Monitor API**:
```bash
sudo systemctl status system-monitor
sudo systemctl restart system-monitor
sudo journalctl -u system-monitor -f
```

### Ports

| Service | Default Port | Protocol |
|---------|-------------|----------|
| System Monitor API | 8000 | HTTP |
| Prometheus | 9090 | HTTP |
| Grafana | 3000 | HTTP |

## Best Practices

1. **Change default Grafana password** immediately after installation
2. **Configure firewall** to restrict Grafana/Prometheus access
3. **Set up SSL/TLS** for production deployments
4. **Regular backups** of Grafana dashboards and Prometheus data
5. **Monitor disk space** - Prometheus data grows over time
6. **Use reverse proxy** (nginx/Apache) for production
7. **Configure alerts** for critical thresholds
8. **Document custom dashboards** for team members

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)

## Support

For issues or questions:
- GitHub Issues: https://github.com/SLYD-Main/SystemMonitor/issues
- Documentation: README.md, DEPLOYMENT.md
