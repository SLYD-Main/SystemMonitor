#!/bin/bash
# Complete System Monitor Bootstrap Script
# Includes all prerequisites: packages, user creation, and setup

set -e

echo "========================================="
echo "System Monitor Complete Bootstrap"
echo "========================================="

# Step 1: Install required packages
echo "[Prerequisites] Installing system packages..."
apt-get update
apt-get install -y python3 python3-pip python3-venv git curl build-essential python3-dev
echo "System packages installed successfully"

# Step 2: Create service user if it doesn't exist
echo "[Prerequisites] Creating sysmonitor user..."
if ! id "sysmonitor" &>/dev/null; then
    useradd -r -m -s /bin/bash sysmonitor
    echo "User sysmonitor created"
else
    echo "User sysmonitor already exists"
fi

echo "========================================="
echo "System Monitor Bootstrap Starting..."
echo "========================================="

echo "[1/8] Navigating to /opt directory..."
cd /opt

echo "[2/8] Cloning repository from GitHub..."
if [ -d "SystemMonitor" ]; then
    echo "Repository already exists, pulling latest changes..."
    cd SystemMonitor
    sudo -u sysmonitor git pull
else
    git clone https://github.com/SLYD-Main/SystemMonitor.git
    echo "Repository cloned successfully"
    cd SystemMonitor
fi

echo "[3/8] Creating Python virtual environment..."
sudo -u sysmonitor python3 -m venv venv
echo "Virtual environment created"

echo "[4/8] Upgrading pip..."
sudo -u sysmonitor venv/bin/pip install --upgrade pip

echo "[5/8] Installing Python dependencies (this may take a few minutes)..."
sudo -u sysmonitor venv/bin/pip install -r requirements.txt
echo "Dependencies installed successfully"

echo "[6/8] Creating necessary directories..."
sudo -u sysmonitor mkdir -p exports
echo "Directories created"

echo "[7/8] Setting permissions..."
chown -R sysmonitor:sysmonitor /opt/SystemMonitor
echo "Permissions set"

echo "========================================="
echo "Setup Phase Complete!"
echo "========================================="

echo "========================================="
echo "Creating systemd service..."
echo "========================================="

cat > /etc/systemd/system/system-monitor.service <<'EOF'
[Unit]
Description=System Monitor API Service
After=network.target

[Service]
Type=simple
User=sysmonitor
WorkingDirectory=/opt/SystemMonitor
Environment="PATH=/opt/SystemMonitor/venv/bin"
ExecStart=/opt/SystemMonitor/venv/bin/python main.py api --enable-history
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "Systemd service file created at /etc/systemd/system/system-monitor.service"

echo "========================================="
echo "Starting System Monitor Service..."
echo "========================================="

echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Enabling system-monitor service..."
systemctl enable system-monitor.service

echo "Starting system-monitor service..."
systemctl start system-monitor.service

echo "Waiting for service to initialize..."
sleep 5

echo "========================================="
echo "Service Status:"
echo "========================================="
systemctl status system-monitor.service --no-pager || true

echo ""
echo "========================================="
echo "Bootstrap Complete!"
echo "API should be available at http://localhost:8000"
echo "Logs: /home/ubuntu/bootstrap_logs"
echo "========================================="

echo "__BOOTSTRAP_DONE__"
