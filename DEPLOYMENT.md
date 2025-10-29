# System Monitor Deployment Guide

This guide covers deploying System Monitor on cloud instances using cloud-init or manual installation.

## Table of Contents
- [Cloud-Init Deployment](#cloud-init-deployment)
- [Manual Installation](#manual-installation)
- [Service Management](#service-management)
- [GPU Support](#gpu-support)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## Cloud-Init Deployment

Cloud-init is the industry standard method for cloud instance initialization. Use this for AWS EC2, Google Cloud, Azure, DigitalOcean, and other cloud providers.

### AWS EC2

**1. Create EC2 Instance with Cloud-Init:**

```bash
# Using AWS CLI
aws ec2 run-instances \
    --image-id ami-xxxxxxxxx \
    --instance-type t3.medium \
    --key-name your-key \
    --security-group-ids sg-xxxxxxxxx \
    --user-data file://cloud-init.yaml \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=SystemMonitor}]'
```

**2. Via AWS Console:**
- Launch new EC2 instance
- Select Ubuntu 22.04 LTS AMI
- Under "Advanced Details" → "User data", paste contents of `cloud-init.yaml`
- Configure security group to allow port 8000
- Launch instance

### Google Cloud Platform

```bash
# Create instance with cloud-init
gcloud compute instances create system-monitor \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --machine-type=n1-standard-2 \
    --metadata-from-file user-data=cloud-init.yaml \
    --tags=http-server
```

### Azure

```bash
# Create VM with cloud-init
az vm create \
    --resource-group myResourceGroup \
    --name system-monitor \
    --image UbuntuLTS \
    --size Standard_B2s \
    --custom-data cloud-init.yaml \
    --generate-ssh-keys
```

### DigitalOcean

```bash
# Create droplet with cloud-init
doctl compute droplet create system-monitor \
    --image ubuntu-22-04-x64 \
    --size s-2vcpu-4gb \
    --region nyc1 \
    --user-data-file cloud-init.yaml
```

### What Cloud-Init Does

The cloud-init configuration uses the bootstrap script to automate deployment:

1. Updates system packages
2. Installs required dependencies (via packages directive)
3. Downloads and executes bootstrap.sh from GitHub
4. Bootstrap script handles:
   - Cloning the repository
   - Creating Python virtual environment
   - Installing Python packages
   - Creating systemd service
   - Starting API server automatically

### Cloud-Init Customization

You can customize the deployment by modifying the runcmd in cloud-init.yaml:

```yaml
runcmd:
  - |
    curl -fsSL https://raw.githubusercontent.com/SLYD-Main/SystemMonitor/master/bootstrap.sh \
    | bash -s -- \
      --non-interactive \
      --api-port 8080 \
      --enable-history \
      --timezone America/New_York \
      --install-gpu-drivers
```

For GPU support:
```yaml
runcmd:
  - |
    curl -fsSL https://raw.githubusercontent.com/SLYD-Main/SystemMonitor/master/bootstrap.sh \
    | bash -s -- --non-interactive --enable-history --install-gpu-drivers
```

## Manual Installation

For bare metal servers or manual deployments:

### Quick Install (Recommended)

The bootstrap script supports customization via command-line arguments:

```bash
# Simple installation with defaults
curl -fsSL https://raw.githubusercontent.com/SLYD-Main/SystemMonitor/master/bootstrap.sh | sudo bash

# Custom installation with options
curl -fsSL https://raw.githubusercontent.com/SLYD-Main/SystemMonitor/master/bootstrap.sh \
| sudo bash -s -- \
  --non-interactive \
  --install-dir /opt/SystemMonitor \
  --api-port 8000 \
  --enable-history \
  --timezone America/New_York \
  --install-gpu-drivers
```

#### Bootstrap Script Options

- `--install-dir DIR` - Installation directory (default: /opt/SystemMonitor)
- `--api-port PORT` - API server port (default: 8000)
- `--enable-history` - Enable historical data logging (default: true)
- `--disable-history` - Disable historical data logging
- `--service-user USER` - Service user name (default: sysmonitor)
- `--repo-url URL` - GitHub repository URL
- `--repo-branch BRANCH` - Git branch to use (default: master)
- `--timezone TZ` - Set system timezone (e.g., America/New_York)
- `--install-gpu-drivers` - Install NVIDIA GPU drivers
- `--non-interactive` - Run without interactive prompts

### Alternative: Interactive Installer

```bash
# Download and run interactive installation script
curl -fsSL https://raw.githubusercontent.com/SLYD-Main/SystemMonitor/master/install.sh | sudo bash
```

### Step-by-Step Installation

```bash
# 1. Clone repository
sudo git clone https://github.com/SLYD-Main/SystemMonitor.git /opt/SystemMonitor
cd /opt/SystemMonitor

# 2. Make bootstrap script executable
sudo chmod +x bootstrap.sh

# 3. Run installation
sudo ./bootstrap.sh --enable-history
```

The script will:
- Install system dependencies
- Create virtual environment
- Install Python packages
- Set up systemd service
- Start the API server
- Optionally install NVIDIA drivers

## Service Management

### Systemd Commands

```bash
# Check status
sudo systemctl status system-monitor

# Start service
sudo systemctl start system-monitor

# Stop service
sudo systemctl stop system-monitor

# Restart service
sudo systemctl restart system-monitor

# Enable auto-start on boot
sudo systemctl enable system-monitor

# Disable auto-start
sudo systemctl disable system-monitor

# View logs (follow mode)
sudo journalctl -u system-monitor -f

# View last 100 lines
sudo journalctl -u system-monitor -n 100

# View logs since boot
sudo journalctl -u system-monitor -b
```

### Service Configuration

Edit service file:
```bash
sudo systemctl edit --full system-monitor.service
```

After editing, reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart system-monitor
```

## GPU Support

### NVIDIA GPU Setup

**Option 1: During cloud-init (recommended)**

Edit `cloud-init.yaml` and uncomment GPU driver installation:
```yaml
runcmd:
  - apt-get install -y ubuntu-drivers-common
  - ubuntu-drivers autoinstall
  - reboot
```

**Option 2: After installation**

```bash
# Install drivers
sudo apt-get install -y ubuntu-drivers-common
sudo ubuntu-drivers autoinstall

# Reboot
sudo reboot

# Verify installation
nvidia-smi

# Install PyTorch for GPU benchmarks
cd /opt/SystemMonitor
source venv/bin/activate

# For Blackwell GPUs (RTX 50-series, B200, etc.) use CUDA 12.8+
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128

# For older GPUs, CUDA 12.1 is sufficient
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

**Note:** Blackwell GPUs (compute capability 12.0) require PyTorch 2.7.0+ with CUDA 12.8 or later for MLPerf benchmarks.

### Verify GPU Support

```bash
cd /opt/SystemMonitor
source venv/bin/activate

# Check GPU info and verify CUDA availability
python main.py gpu-benchmark --test info

# Run full benchmark (includes memory, compute, stress tests)
python main.py gpu-benchmark --test full

# Run MLPerf benchmarks (ResNet-50 + BERT)
python main.py gpu-benchmark --test mlperf
```

## Configuration

### Edit Configuration

```bash
sudo nano /opt/SystemMonitor/config.yaml
```

### Key Configuration Options

```yaml
# API settings
api:
  host: "0.0.0.0"  # Listen on all interfaces
  port: 8000        # API port
  enable_cors: true

# Alert thresholds
thresholds:
  cpu:
    warning: 70
    critical: 90
  memory:
    warning: 75
    critical: 90

# Historical data
history:
  enabled: true
  retention_hours: 24
  interval_seconds: 5
```

After editing, restart service:
```bash
sudo systemctl restart system-monitor
```

## Firewall Configuration

### UFW (Ubuntu Firewall)

```bash
# Allow API port
sudo ufw allow 8000/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### AWS Security Group

Allow inbound traffic on port 8000:
```
Type: Custom TCP
Port Range: 8000
Source: Your IP or 0.0.0.0/0 (caution: public access)
```

### Cloud Provider Firewalls

- **GCP**: Create firewall rule for port 8000
- **Azure**: Add inbound rule to Network Security Group
- **DigitalOcean**: Configure Cloud Firewall

## API Access

Once deployed, access the API at:
```
http://your-instance-ip:8000
```

Interactive documentation:
```
http://your-instance-ip:8000/docs
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status system-monitor

# View detailed logs
sudo journalctl -u system-monitor -n 50 --no-pager

# Check if port is in use
sudo netstat -tlnp | grep 8000

# Verify Python dependencies
cd /opt/SystemMonitor
source venv/bin/activate
pip list
```

### Permission Issues

```bash
# Fix ownership
sudo chown -R sysmonitor:sysmonitor /opt/SystemMonitor

# Restart service
sudo systemctl restart system-monitor
```

### Can't Access API

```bash
# Check if service is running
sudo systemctl status system-monitor

# Check if port is listening
sudo ss -tlnp | grep 8000

# Test locally
curl http://localhost:8000

# Check firewall
sudo ufw status
```

### GPU Not Detected

```bash
# Verify NVIDIA drivers
nvidia-smi

# If not installed
sudo ubuntu-drivers autoinstall
sudo reboot

# Check PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"
```

### High Memory Usage

```bash
# Check resource usage
top
htop

# Adjust history retention in config.yaml
history:
  retention_hours: 12  # Reduce from 24
  interval_seconds: 10  # Increase from 5

# Restart service
sudo systemctl restart system-monitor
```

## Updating the Application

### Using the Update Script (Recommended)

The easiest way to update is using the included update script:

```bash
sudo /opt/SystemMonitor/update.sh
```

This script automatically:
- Fixes git repository ownership
- Resets any local changes and pulls latest code
- Updates Python dependencies
- Updates Grafana dashboards (if installed)
- Restarts all services

### Manual Update

If you prefer to update manually:

```bash
# Fix git ownership (important - prevents permission errors)
cd /opt/SystemMonitor
sudo chown -R sysmonitor:sysmonitor .git

# Reset local changes and pull latest
# Note: Use 'git reset --hard' instead of 'git pull' to avoid merge conflicts
# from local changes made by scripts running as root
sudo -u sysmonitor git fetch origin
sudo -u sysmonitor git reset --hard origin/master

# Update Python dependencies
sudo -u sysmonitor bash -c "source venv/bin/activate && pip install -q --upgrade pip && pip install -q -r requirements.txt"

# Update Grafana dashboards (if installed)
if [ -d /var/lib/grafana/dashboards ]; then
  sudo cp grafana/dashboards/*.json /var/lib/grafana/dashboards/
  sudo chown -R grafana:grafana /var/lib/grafana/dashboards
  sudo systemctl restart grafana-server
fi

# Restart System Monitor
sudo systemctl restart system-monitor
```

**Important**: Always use `git reset --hard origin/master` instead of `git pull`. This prevents merge conflicts that occur when installation scripts modify files as root.

## Uninstallation

```bash
# Stop and disable service
sudo systemctl stop system-monitor
sudo systemctl disable system-monitor

# Remove service file
sudo rm /etc/systemd/system/system-monitor.service
sudo systemctl daemon-reload

# Remove installation
sudo rm -rf /opt/SystemMonitor

# Remove service user (optional)
sudo userdel sysmonitor
```

## Production Best Practices

1. **Use HTTPS**: Put behind nginx/Apache with SSL
2. **Authentication**: Implement API key authentication
3. **Monitoring**: Set up monitoring for the monitor!
4. **Backups**: Backup config.yaml and database
5. **Log Rotation**: Configure logrotate
6. **Resource Limits**: Set memory/CPU limits in systemd
7. **Health Checks**: Monitor `/health` endpoint
8. **Updates**: Regularly update dependencies

## Example Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name monitor.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/SLYD-Main/SystemMonitor/issues
- Documentation: README.md

## License

See LICENSE file in repository.