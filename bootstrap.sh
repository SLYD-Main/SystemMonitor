#!/bin/bash
# System Monitor Bootstrap Script
# This script should be placed in cloud-init runcmd

set -e

echo "========================================="
echo "System Monitor Bootstrap Starting..."
echo "========================================="

echo "[1/8] Navigating to /opt directory..."
cd /opt

echo "[2/8] Cloning repository from GitHub..."
git clone https://github.com/SLYD-Main/SystemMonitor.git
echo "Repository cloned successfully"

echo "[3/8] Navigating to SystemMonitor directory..."
cd SystemMonitor

echo "[4/8] Creating Python virtual environment..."
python3 -m venv venv
echo "Virtual environment created"

echo "[5/8] Upgrading pip..."
venv/bin/pip install --upgrade pip

echo "[6/8] Installing Python dependencies (this may take a few minutes)..."
venv/bin/pip install -r requirements.txt
echo "Dependencies installed successfully"

echo "[7/8] Creating necessary directories..."
mkdir -p exports
echo "Directories created"

echo "[8/8] Setting permissions..."
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
echo "========================================="
