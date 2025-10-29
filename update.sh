#!/bin/bash
# System Monitor Update Script
# Safely updates the installation to the latest version from GitHub

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root (use sudo)"
    exit 1
fi

INSTALL_DIR="${INSTALL_DIR:-/opt/SystemMonitor}"
SERVICE_USER="${SERVICE_USER:-sysmonitor}"

echo "========================================="
echo "  System Monitor Update"
echo "========================================="
echo ""
print_info "Install Directory: $INSTALL_DIR"
print_info "Service User: $SERVICE_USER"
echo ""

# Check if installation exists
if [ ! -d "$INSTALL_DIR" ]; then
    print_error "Installation directory not found: $INSTALL_DIR"
    print_info "Please install System Monitor first using bootstrap.sh"
    exit 1
fi

cd "$INSTALL_DIR"

# Check if it's a git repository
if [ ! -d ".git" ]; then
    print_error "Not a git repository. Cannot update."
    exit 1
fi

# Fix git ownership (common issue when scripts run as root)
print_msg "Fixing repository ownership..."
chown -R "$SERVICE_USER":"$SERVICE_USER" .git

# Reset any local changes and pull latest
print_msg "Updating from GitHub..."
print_warning "Any local changes will be discarded"
sudo -u "$SERVICE_USER" git fetch origin
sudo -u "$SERVICE_USER" git reset --hard origin/master

# Update Grafana dashboards if installed
if [ -d "/var/lib/grafana/dashboards" ]; then
    print_msg "Updating Grafana dashboards..."
    if [ -f "grafana/dashboards/system-overview.json" ]; then
        cp grafana/dashboards/system-overview.json /var/lib/grafana/dashboards/
    fi
    if [ -f "grafana/dashboards/gpu-monitoring.json" ]; then
        cp grafana/dashboards/gpu-monitoring.json /var/lib/grafana/dashboards/
    fi
    chown -R grafana:grafana /var/lib/grafana/dashboards
    print_msg "Restarting Grafana..."
    systemctl restart grafana-server
fi

# Update Python dependencies
print_msg "Updating Python dependencies..."
sudo -u "$SERVICE_USER" bash -c "source venv/bin/activate && pip install -q --upgrade pip && pip install -q -r requirements.txt"

# Restart System Monitor service
print_msg "Restarting System Monitor service..."
systemctl restart system-monitor

# Wait for service to start
sleep 2

# Check service status
if systemctl is-active --quiet system-monitor; then
    print_msg "System Monitor updated and restarted successfully!"
else
    print_error "System Monitor failed to start after update"
    print_info "Check logs: sudo journalctl -u system-monitor -n 50"
    exit 1
fi

echo ""
echo "========================================="
print_msg "Update Complete!"
echo "========================================="
echo ""
print_info "Service Status:"
systemctl status system-monitor --no-pager | head -10
echo ""
print_info "Quick Update Command (for future use):"
echo "  sudo $INSTALL_DIR/update.sh"
echo ""

exit 0
