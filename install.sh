#!/bin/bash
# System Monitor Installation Script
# This script installs and configures the System Monitor application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/SystemMonitor"
REPO_URL="https://github.com/SLYD-Main/SystemMonitor.git"
SERVICE_USER="sysmonitor"

# Print colored message
print_msg() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[*]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root (use sudo)"
    exit 1
fi

print_msg "Starting System Monitor installation..."

# Update system
print_msg "Updating package database..."
apt-get update

# Install dependencies
print_msg "Installing system dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    build-essential \
    python3-dev

# Create service user if it doesn't exist
if ! id "$SERVICE_USER" &>/dev/null; then
    print_msg "Creating service user: $SERVICE_USER"
    useradd -r -s /bin/bash -d $INSTALL_DIR $SERVICE_USER
fi

# Clone or update repository
if [ -d "$INSTALL_DIR" ]; then
    print_warning "Installation directory exists. Updating..."
    cd $INSTALL_DIR
    sudo -u $SERVICE_USER git pull
else
    print_msg "Cloning repository..."
    git clone $REPO_URL $INSTALL_DIR
fi

cd $INSTALL_DIR

# Create virtual environment
print_msg "Creating Python virtual environment..."
sudo -u $SERVICE_USER python3 -m venv venv

# Activate virtual environment and install dependencies
print_msg "Installing Python dependencies..."
sudo -u $SERVICE_USER bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"

# Create necessary directories
print_msg "Creating directories..."
sudo -u $SERVICE_USER mkdir -p exports

# Set permissions
print_msg "Setting permissions..."
chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR

# Create systemd service
print_msg "Creating systemd service..."
cat > /etc/systemd/system/system-monitor.service <<EOF
[Unit]
Description=System Monitor API Service
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
ExecStart=$INSTALL_DIR/venv/bin/python main.py api --enable-history
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
print_msg "Reloading systemd..."
systemctl daemon-reload

# Enable and start service
print_msg "Enabling and starting system-monitor service..."
systemctl enable system-monitor.service
systemctl start system-monitor.service

# Wait a moment for service to start
sleep 2

# Check service status
if systemctl is-active --quiet system-monitor.service; then
    print_msg "Service started successfully!"
else
    print_error "Service failed to start. Check logs with: sudo journalctl -u system-monitor -n 50"
fi

# Print completion message
echo ""
echo "========================================"
print_msg "System Monitor Installation Complete!"
echo "========================================"
echo ""
echo "Installation Directory: $INSTALL_DIR"
echo "API Server: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo ""
echo "Service Management:"
echo "  Status:  sudo systemctl status system-monitor"
echo "  Start:   sudo systemctl start system-monitor"
echo "  Stop:    sudo systemctl stop system-monitor"
echo "  Restart: sudo systemctl restart system-monitor"
echo "  Logs:    sudo journalctl -u system-monitor -f"
echo ""
echo "CLI Usage:"
echo "  cd $INSTALL_DIR"
echo "  source venv/bin/activate"
echo "  python main.py --help"
echo ""
echo "Configuration File:"
echo "  $INSTALL_DIR/config.yaml"
echo ""

# Ask about GPU support
echo ""
read -p "Do you want to install NVIDIA GPU drivers? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_msg "Installing NVIDIA drivers..."
    apt-get install -y ubuntu-drivers-common
    ubuntu-drivers autoinstall
    print_warning "GPU drivers installed. Reboot required!"
    echo ""
    read -p "Reboot now? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_msg "Rebooting..."
        reboot
    fi
fi

print_msg "Installation complete!"