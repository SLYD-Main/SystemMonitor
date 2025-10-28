# System Monitor

A comprehensive hardware monitoring tool for Linux systems that tracks CPU, Memory, Disk, Network, and GPU usage. Provides both a CLI interface and REST API for accessing monitoring data.

## Features

- **Multi-Hardware Support**: Monitor CPU, Memory, Disk, Network, and GPU (NVIDIA)
- **Real-Time Dashboard**: Live terminal dashboard with auto-refresh
- **Snapshot Mode**: One-time system statistics snapshot
- **REST API**: Full-featured API with automatic documentation
- **Historical Data**: Store and query historical monitoring data
- **Alerts & Thresholds**: Configurable warning and critical alerts
- **Export Capabilities**: Export data to JSON or CSV formats
- **Cross-Platform**: Support for various hardware configurations

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd SystemMonitor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) For GPU monitoring, ensure NVIDIA drivers are installed:
```bash
nvidia-smi  # Should display GPU information
```

## Quick Start

### View System Information
```bash
python main.py info
```

### Real-Time Dashboard
Launch the live monitoring dashboard:
```bash
python main.py dashboard
```

With custom refresh rate:
```bash
python main.py dashboard --refresh-rate 2.0
```

### One-Time Snapshot
Display current system stats:
```bash
python main.py snapshot
```

Export snapshot to JSON:
```bash
python main.py snapshot --format json --output snapshot.json
```

### Start API Server
Start the REST API server:
```bash
python main.py api
```

With historical data logging:
```bash
python main.py api --enable-history
```

Custom host and port:
```bash
python main.py api --host 0.0.0.0 --port 9000
```

### Export Data
Export current snapshot:
```bash
python main.py export --format json
python main.py export --format csv --output mydata.csv
```

### View Historical Data
```bash
python main.py history cpu --hours 24
python main.py history memory --hours 12 --limit 100 --format csv
```

### Check Alerts
```bash
python main.py alerts
```

## Configuration

Edit `config.yaml` to customize thresholds, API settings, and more:

```yaml
# Alert thresholds (in percentage)
thresholds:
  cpu:
    warning: 70
    critical: 90
  memory:
    warning: 75
    critical: 90
  disk:
    warning: 80
    critical: 95
  gpu:
    warning: 80
    critical: 95

# Historical data settings
history:
  enabled: true
  retention_hours: 24
  interval_seconds: 5

# API settings
api:
  host: "0.0.0.0"
  port: 8000
  enable_cors: true

# CLI settings
cli:
  refresh_rate: 1  # seconds
  show_graphs: true
```

## REST API Usage

Once the API server is running, access the interactive documentation at:
```
http://localhost:8000/docs
```

### Key API Endpoints

#### Get System Snapshot
```bash
curl http://localhost:8000/api/snapshot
```

#### Get CPU Statistics
```bash
curl http://localhost:8000/api/cpu
curl http://localhost:8000/api/cpu?per_cpu=true
```

#### Get Memory Statistics
```bash
curl http://localhost:8000/api/memory
curl http://localhost:8000/api/memory?readable=true
```

#### Get Disk Statistics
```bash
curl http://localhost:8000/api/disk
```

#### Get Network Statistics
```bash
curl http://localhost:8000/api/network
curl http://localhost:8000/api/network/speed?interval=2.0
```

#### Get GPU Statistics
```bash
curl http://localhost:8000/api/gpu
```

#### Get Historical Data
```bash
curl http://localhost:8000/api/history/cpu?hours=24
curl http://localhost:8000/api/history/memory?hours=12&limit=100
```

#### Get Alerts
```bash
curl http://localhost:8000/api/alerts
curl http://localhost:8000/api/alerts?active_only=false
```

#### Export Data
```bash
curl -X POST "http://localhost:8000/api/export?format=json"
```

#### Health Check
```bash
curl http://localhost:8000/health
```

## Python API Usage

You can also use the monitoring modules directly in your Python code:

```python
from src.monitors.cpu import CPUMonitor
from src.monitors.memory import MemoryMonitor
from src.monitors.disk import DiskMonitor
from src.monitors.network import NetworkMonitor
from src.monitors.gpu import GPUMonitor

# Initialize monitors
cpu = CPUMonitor()
memory = MemoryMonitor()
disk = DiskMonitor()
network = NetworkMonitor()
gpu = GPUMonitor()

# Get data
cpu_data = cpu.get_usage(interval=1.0, per_cpu=False)
memory_data = memory.get_memory()
disk_data = disk.get_complete_stats()
network_data = network.get_io_counters(per_nic=True)
gpu_data = gpu.get_all_gpus()

print(f"CPU Usage: {cpu_data['usage_percent']}%")
print(f"Memory Usage: {memory_data['virtual']['percent']}%")
```

### Using Alerts

```python
from src.alerts.alert_manager import AlertManager
from src.config import Config

# Load config and create alert manager
config = Config()
alert_manager = AlertManager(config.get_thresholds())

# Check for alerts
monitoring_data = {
    "cpu": cpu.get_usage(interval=1.0),
    "memory": memory.get_memory(),
    "disk": disk.get_complete_stats(),
    "gpu": gpu.get_all_gpus()
}

alerts = alert_manager.check_all(monitoring_data)
for alert in alerts:
    print(alert)
```

### Using Historical Database

```python
from src.storage.database import HistoricalDatabase

db = HistoricalDatabase()

# Store data
db.store_cpu_data(cpu_data)
db.store_memory_data(memory_data)

# Retrieve history
cpu_history = db.get_history("cpu_history", hours=24)
memory_stats = db.get_statistics("memory_history", hours=1)
```

## Project Structure

```
SystemMonitor/
├── main.py                 # Main CLI entry point
├── config.yaml            # Configuration file
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── src/
│   ├── monitors/         # Hardware monitoring modules
│   │   ├── cpu.py       # CPU monitoring
│   │   ├── memory.py    # Memory monitoring
│   │   ├── disk.py      # Disk monitoring
│   │   ├── network.py   # Network monitoring
│   │   └── gpu.py       # GPU monitoring
│   ├── storage/          # Data storage and export
│   │   ├── database.py  # Historical data storage
│   │   └── exporter.py  # Data export functionality
│   ├── alerts/           # Alert management
│   │   └── alert_manager.py
│   ├── cli/              # CLI interface
│   │   └── dashboard.py # Terminal dashboard
│   ├── api/              # REST API
│   │   └── server.py    # FastAPI server
│   └── config.py         # Configuration management
└── exports/              # Export directory (created automatically)
```

## Requirements

- Python 3.7+
- psutil: Cross-platform system monitoring
- rich: Terminal UI
- click: CLI framework
- FastAPI: REST API framework
- uvicorn: ASGI server
- pynvml/GPUtil: GPU monitoring (optional, for NVIDIA GPUs)
- pandas: Data export
- pyyaml: Configuration
- apscheduler: Background tasks

## GPU Support

This tool primarily supports NVIDIA GPUs through `pynvml` and `GPUtil`. To enable GPU monitoring:

1. Install NVIDIA drivers
2. Verify with `nvidia-smi`
3. Install Python dependencies (already in requirements.txt)

If GPU monitoring libraries are not available, the tool will still work for other hardware monitoring.

## Troubleshooting

### Permission Issues
Some monitoring features may require elevated privileges:
```bash
sudo python main.py dashboard
```

### GPU Not Detected
- Ensure NVIDIA drivers are installed: `nvidia-smi`
- Verify Python packages: `pip install pynvml GPUtil`
- Check if GPU monitoring is available: `python main.py info`

### Port Already in Use
Change the API port:
```bash
python main.py api --port 8001
```

## CLI Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| `info` | Display system information | `python main.py info` |
| `dashboard` | Launch real-time dashboard | `python main.py dashboard -r 2.0` |
| `snapshot` | One-time system snapshot | `python main.py snapshot -f json` |
| `api` | Start REST API server | `python main.py api --enable-history` |
| `export` | Export current snapshot | `python main.py export -f csv -o data.csv` |
| `history` | View historical data | `python main.py history cpu --hours 24` |
| `alerts` | Check system alerts | `python main.py alerts` |

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

This project is open source and available under the MIT License.

## Acknowledgments

- Built with [psutil](https://github.com/giampaolo/psutil)
- UI powered by [rich](https://github.com/Textualize/rich)
- API built with [FastAPI](https://fastapi.tiangolo.com/)
- GPU monitoring via [pynvml](https://github.com/gpuopenanalytics/pynvml)
