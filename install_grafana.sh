#!/bin/bash
# Grafana and Prometheus Installation Script
# This script installs and configures Grafana and Prometheus for System Monitor

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="${INSTALL_DIR:-/opt/SystemMonitor}"
PROMETHEUS_VERSION="2.48.0"
GRAFANA_VERSION="10.2.2"
PROMETHEUS_PORT="${PROMETHEUS_PORT:-9090}"
GRAFANA_PORT="${GRAFANA_PORT:-3000}"

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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root (use sudo)"
    exit 1
fi

echo "========================================="
echo "  Grafana & Prometheus Installation"
echo "========================================="
echo ""
print_info "This will install:"
print_info "  - Prometheus (metrics database)"
print_info "  - Grafana (visualization)"
print_info "  - Pre-configured dashboards"
echo ""

# Update system
print_msg "Updating package database..."
apt-get update -qq

# Install dependencies
print_msg "Installing dependencies..."
apt-get install -y -qq wget apt-transport-https software-properties-common

# Install Prometheus
print_msg "Installing Prometheus..."

# Download Prometheus
cd /tmp
wget -q https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz

# Extract
tar -xzf prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz

# Move to install directory
mv prometheus-${PROMETHEUS_VERSION}.linux-amd64 /opt/prometheus

# Create Prometheus user
if ! id "prometheus" &>/dev/null; then
    useradd --no-create-home --shell /bin/false prometheus
fi

# Create directories
mkdir -p /var/lib/prometheus
chown prometheus:prometheus /var/lib/prometheus

# Copy Prometheus configuration
print_msg "Configuring Prometheus..."
cp "${INSTALL_DIR}/grafana/prometheus.yml" /opt/prometheus/prometheus.yml
chown prometheus:prometheus /opt/prometheus/prometheus.yml

# Create Prometheus systemd service
cat > /etc/systemd/system/prometheus.service <<EOF
[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/opt/prometheus/prometheus \\
    --config.file=/opt/prometheus/prometheus.yml \\
    --storage.tsdb.path=/var/lib/prometheus/ \\
    --web.console.templates=/opt/prometheus/consoles \\
    --web.console.libraries=/opt/prometheus/console_libraries \\
    --web.listen-address=0.0.0.0:${PROMETHEUS_PORT}

[Install]
WantedBy=multi-user.target
EOF

# Start Prometheus
print_msg "Starting Prometheus..."
systemctl daemon-reload
systemctl enable prometheus
systemctl start prometheus

# Wait for Prometheus to start
sleep 3

# Check Prometheus status
if systemctl is-active --quiet prometheus; then
    print_msg "Prometheus started successfully!"
else
    print_error "Prometheus failed to start"
    exit 1
fi

# Install Grafana
print_msg "Installing Grafana..."

# Add Grafana GPG key
wget -q -O /usr/share/keyrings/grafana.key https://apt.grafana.com/gpg.key

# Add Grafana repository
echo "deb [signed-by=/usr/share/keyrings/grafana.key] https://apt.grafana.com stable main" | tee /etc/apt/sources.list.d/grafana.list

# Update and install
apt-get update -qq
apt-get install -y -qq grafana

# Configure Grafana
print_msg "Configuring Grafana..."

# Set Grafana port
sed -i "s/;http_port = 3000/http_port = ${GRAFANA_PORT}/" /etc/grafana/grafana.ini

# Copy datasource configuration
mkdir -p /etc/grafana/provisioning/datasources
cp "${INSTALL_DIR}/grafana/datasources/prometheus.yml" /etc/grafana/provisioning/datasources/

# Copy dashboard configurations
mkdir -p /etc/grafana/provisioning/dashboards

# Create dashboard provider configuration
cat > /etc/grafana/provisioning/dashboards/system-monitor.yml <<EOF
apiVersion: 1

providers:
  - name: 'System Monitor'
    orgId: 1
    folder: 'System Monitor'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: true
EOF

# Copy dashboard JSON files
mkdir -p /var/lib/grafana/dashboards
cp "${INSTALL_DIR}/grafana/dashboards/"*.json /var/lib/grafana/dashboards/
chown -R grafana:grafana /var/lib/grafana/dashboards

# Start Grafana
print_msg "Starting Grafana..."
systemctl daemon-reload
systemctl enable grafana-server
systemctl start grafana-server

# Wait for Grafana to start
sleep 5

# Check Grafana status
if systemctl is-active --quiet grafana-server; then
    print_msg "Grafana started successfully!"
else
    print_error "Grafana failed to start"
    exit 1
fi

# Configure firewall (if UFW is active)
if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
    print_msg "Configuring firewall..."
    ufw allow ${PROMETHEUS_PORT}/tcp comment 'Prometheus'
    ufw allow ${GRAFANA_PORT}/tcp comment 'Grafana'
fi

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "========================================="
print_msg "Installation Complete!"
echo "========================================="
echo ""
print_info "Services:"
echo "  Prometheus: http://${SERVER_IP}:${PROMETHEUS_PORT}"
echo "  Grafana:    http://${SERVER_IP}:${GRAFANA_PORT}"
echo ""
print_info "Grafana Login:"
echo "  Username: admin"
echo "  Password: admin"
echo "  (You will be prompted to change the password on first login)"
echo ""
print_info "Pre-installed Dashboards:"
echo "  - System Overview"
echo "  - GPU Monitoring"
echo ""
print_info "Service Management:"
echo "  Prometheus:"
echo "    Status:  sudo systemctl status prometheus"
echo "    Restart: sudo systemctl restart prometheus"
echo "    Logs:    sudo journalctl -u prometheus -f"
echo ""
echo "  Grafana:"
echo "    Status:  sudo systemctl status grafana-server"
echo "    Restart: sudo systemctl restart grafana-server"
echo "    Logs:    sudo journalctl -u grafana-server -f"
echo ""
print_warning "Make sure your System Monitor API is running on port 8000"
print_warning "Prometheus will start scraping metrics automatically"
echo ""

# Ask if user wants to install DCGM Exporter
if command -v nvidia-smi &> /dev/null; then
    print_info "NVIDIA GPU detected!"
    echo ""
    echo "Would you like to install NVIDIA DCGM Exporter for advanced GPU metrics?"
    echo "  (Provides comprehensive GPU monitoring including NVLink, PCIe, ECC errors, etc.)"
    echo ""
    read -p "Install DCGM Exporter? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_msg "Installing NVIDIA DCGM Exporter..."
        if [ -f "${INSTALL_DIR}/install_dcgm_exporter.sh" ]; then
            bash "${INSTALL_DIR}/install_dcgm_exporter.sh"
        else
            print_warning "DCGM installer not found. You can install it manually later:"
            print_info "  sudo ${INSTALL_DIR}/install_dcgm_exporter.sh"
        fi
    fi
fi

exit 0