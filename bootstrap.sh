#!/bin/bash
# System Monitor Bootstrap Script
# Can be run standalone or via cloud-init
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/SLYD-Main/SystemMonitor/master/bootstrap.sh | sudo bash
#
# Or with options:
#   curl -fsSL https://raw.githubusercontent.com/SLYD-Main/SystemMonitor/master/bootstrap.sh \
#   | sudo bash -s -- \
#     --non-interactive \
#     --install-dir /opt/SystemMonitor \
#     --api-port 8000 \
#     --enable-history \
#     --install-gpu-drivers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
INSTALL_DIR="/opt/SystemMonitor"
REPO_URL="https://github.com/SLYD-Main/SystemMonitor.git"
SERVICE_USER="sysmonitor"
API_PORT="8000"
ENABLE_HISTORY="true"
NON_INTERACTIVE="false"
INSTALL_GPU_DRIVERS="false"
TIMEZONE=""
REPO_BRANCH="master"

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

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# Print usage
usage() {
    cat << EOF
System Monitor Bootstrap Script

Usage:
    $0 [OPTIONS]

Options:
    --install-dir DIR          Installation directory (default: /opt/SystemMonitor)
    --api-port PORT           API server port (default: 8000)
    --enable-history          Enable historical data logging (default: true)
    --disable-history         Disable historical data logging
    --service-user USER       Service user name (default: sysmonitor)
    --repo-url URL            GitHub repository URL
    --repo-branch BRANCH      Git branch to use (default: master)
    --timezone TZ             Set system timezone (e.g., America/New_York)
    --install-gpu-drivers     Install NVIDIA GPU drivers
    --non-interactive         Run without interactive prompts
    -h, --help                Show this help message

Examples:
    # Simple installation
    curl -fsSL https://raw.githubusercontent.com/SLYD-Main/SystemMonitor/master/bootstrap.sh | sudo bash

    # Custom installation
    curl -fsSL https://raw.githubusercontent.com/SLYD-Main/SystemMonitor/master/bootstrap.sh \\
    | sudo bash -s -- \\
      --non-interactive \\
      --install-dir /opt/SystemMonitor \\
      --api-port 8080 \\
      --enable-history \\
      --timezone America/New_York \\
      --install-gpu-drivers

EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --api-port)
            API_PORT="$2"
            shift 2
            ;;
        --enable-history)
            ENABLE_HISTORY="true"
            shift
            ;;
        --disable-history)
            ENABLE_HISTORY="false"
            shift
            ;;
        --service-user)
            SERVICE_USER="$2"
            shift 2
            ;;
        --repo-url)
            REPO_URL="$2"
            shift 2
            ;;
        --repo-branch)
            REPO_BRANCH="$2"
            shift 2
            ;;
        --timezone)
            TIMEZONE="$2"
            shift 2
            ;;
        --install-gpu-drivers)
            INSTALL_GPU_DRIVERS="true"
            shift
            ;;
        --non-interactive)
            NON_INTERACTIVE="true"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root (use sudo)"
    exit 1
fi

echo "========================================="
echo "  System Monitor Bootstrap"
echo "========================================="
echo ""
print_info "Configuration:"
print_info "  Install Directory: $INSTALL_DIR"
print_info "  Repository URL: $REPO_URL"
print_info "  Branch: $REPO_BRANCH"
print_info "  Service User: $SERVICE_USER"
print_info "  API Port: $API_PORT"
print_info "  History Logging: $ENABLE_HISTORY"
print_info "  GPU Drivers: $INSTALL_GPU_DRIVERS"
if [ -n "$TIMEZONE" ]; then
    print_info "  Timezone: $TIMEZONE"
fi
echo ""

# Set timezone if specified
if [ -n "$TIMEZONE" ]; then
    print_msg "Setting timezone to $TIMEZONE..."
    timedatectl set-timezone "$TIMEZONE" || print_warning "Failed to set timezone"
fi

# Update system
print_msg "Updating package database..."
apt-get update -qq

# Install dependencies
print_msg "Installing system dependencies..."
apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    build-essential \
    python3-dev

print_msg "System packages installed successfully"

# Create service user if it doesn't exist
if ! id "$SERVICE_USER" &>/dev/null; then
    print_msg "Creating service user: $SERVICE_USER"
    useradd -r -m -s /bin/bash -d "$INSTALL_DIR" "$SERVICE_USER"
else
    print_info "Service user $SERVICE_USER already exists"
fi

# Clone or update repository
if [ -d "$INSTALL_DIR/.git" ]; then
    print_warning "Installation directory exists. Updating..."
    cd "$INSTALL_DIR"
    sudo -u "$SERVICE_USER" git fetch origin
    sudo -u "$SERVICE_USER" git checkout "$REPO_BRANCH"
    sudo -u "$SERVICE_USER" git pull
elif [ -d "$INSTALL_DIR" ]; then
    print_warning "Installation directory exists but is not a git repository. Removing and cloning fresh..."
    rm -rf "$INSTALL_DIR"
    print_msg "Cloning repository..."
    git clone -b "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR"
    chown -R "$SERVICE_USER":"$SERVICE_USER" "$INSTALL_DIR"
else
    print_msg "Cloning repository..."
    git clone -b "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR"
    chown -R "$SERVICE_USER":"$SERVICE_USER" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# Create virtual environment
print_msg "Creating Python virtual environment..."
sudo -u "$SERVICE_USER" python3 -m venv venv

# Activate virtual environment and install dependencies
print_msg "Installing Python dependencies (this may take a few minutes)..."
sudo -u "$SERVICE_USER" bash -c "source venv/bin/activate && pip install -q --upgrade pip && pip install -q -r requirements.txt"

# Create necessary directories
print_msg "Creating directories..."
sudo -u "$SERVICE_USER" mkdir -p exports

# Set permissions
print_msg "Setting permissions..."
chown -R "$SERVICE_USER":"$SERVICE_USER" "$INSTALL_DIR"

# Build ExecStart command
EXEC_START_CMD="$INSTALL_DIR/venv/bin/python main.py api --port $API_PORT"
if [ "$ENABLE_HISTORY" = "true" ]; then
    EXEC_START_CMD="$EXEC_START_CMD --enable-history"
fi

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
ExecStart=$EXEC_START_CMD
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

print_msg "Systemd service file created"

# Reload systemd
print_msg "Reloading systemd..."
systemctl daemon-reload

# Enable and start service
print_msg "Enabling and starting system-monitor service..."
systemctl enable system-monitor.service
systemctl start system-monitor.service

# Wait a moment for service to start
sleep 3

# Check service status
if systemctl is-active --quiet system-monitor.service; then
    print_msg "Service started successfully!"
else
    print_error "Service failed to start. Check logs with: sudo journalctl -u system-monitor -n 50"
fi

# Install GPU drivers if requested
if [ "$INSTALL_GPU_DRIVERS" = "true" ]; then
    print_msg "Installing NVIDIA GPU drivers..."
    apt-get install -y -qq ubuntu-drivers-common
    ubuntu-drivers autoinstall
    print_warning "GPU drivers installed. Reboot required for drivers to take effect!"
fi

# Print completion message
echo ""
echo "========================================="
print_msg "System Monitor Installation Complete!"
echo "========================================="
echo ""
echo "Installation Directory: $INSTALL_DIR"
echo "API Server: http://localhost:$API_PORT"
echo "API Documentation: http://localhost:$API_PORT/docs"
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
echo "Configuration:"
echo "  $INSTALL_DIR/config.yaml"
echo ""

if [ "$INSTALL_GPU_DRIVERS" = "true" ]; then
    echo ""
    print_warning "GPU drivers were installed. Please reboot the system:"
    echo "  sudo reboot"
    echo ""
fi

# Mark bootstrap as complete
echo "__BOOTSTRAP_COMPLETE__"

exit 0
