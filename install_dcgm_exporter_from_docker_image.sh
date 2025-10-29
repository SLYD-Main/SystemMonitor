#!/bin/bash
# NVIDIA DCGM Exporter Installation Script
# Extracts binary from Docker image (no Docker runtime required)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DCGM_EXPORTER_VERSION="${DCGM_EXPORTER_VERSION:-3.3.5-3.4.2}"
DCGM_PORT="${DCGM_PORT:-9400}"

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
echo "  NVIDIA DCGM Exporter Installation"
echo "  (Binary extracted from Docker image)"
echo "========================================="
echo ""

# Check if NVIDIA GPU is available
if ! command -v nvidia-smi &> /dev/null; then
    print_error "NVIDIA drivers not found. Please install NVIDIA drivers first."
    exit 1
fi

# Check GPU
print_msg "Detecting NVIDIA GPUs..."
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader

# Check if DCGM is installed and running
if ! systemctl is-active --quiet nvidia-dcgm; then
    print_error "DCGM service is not running. Please install and start DCGM first:"
    print_info "  sudo apt-get install datacenter-gpu-manager"
    print_info "  sudo systemctl --now enable nvidia-dcgm"
    exit 1
fi

print_msg "DCGM service is running"

# Install Docker temporarily if needed (just to extract binary)
DOCKER_INSTALLED=false
if ! command -v docker &> /dev/null; then
    print_msg "Installing Docker temporarily to extract binary..."
    apt-get update -qq
    apt-get install -y -qq docker.io
    systemctl start docker
    DOCKER_INSTALLED=true
else
    print_info "Docker already installed"
fi

# Pull DCGM exporter image
print_msg "Pulling DCGM exporter image..."
docker pull nvcr.io/nvidia/k8s/dcgm-exporter:${DCGM_EXPORTER_VERSION}-ubuntu22.04

# Extract binary from image
print_msg "Extracting binary from Docker image..."
CONTAINER_ID=$(docker create nvcr.io/nvidia/k8s/dcgm-exporter:${DCGM_EXPORTER_VERSION}-ubuntu22.04)
docker cp ${CONTAINER_ID}:/usr/bin/dcgm-exporter /usr/local/bin/dcgm-exporter
docker cp ${CONTAINER_ID}:/etc/dcgm-exporter/default-counters.csv /tmp/default-counters.csv 2>/dev/null || true
docker cp ${CONTAINER_ID}:/etc/dcgm-exporter/dcp-metrics-included.csv /tmp/dcp-metrics-included.csv 2>/dev/null || true
docker rm ${CONTAINER_ID} >/dev/null

# Set permissions
chmod +x /usr/local/bin/dcgm-exporter

# Copy config files
mkdir -p /etc/dcgm-exporter
if [ -f "/tmp/default-counters.csv" ]; then
    mv /tmp/default-counters.csv /etc/dcgm-exporter/
fi
if [ -f "/tmp/dcp-metrics-included.csv" ]; then
    mv /tmp/dcp-metrics-included.csv /etc/dcgm-exporter/
fi

# Clean up Docker if we installed it
if [ "$DOCKER_INSTALLED" = true ]; then
    print_msg "Removing temporary Docker installation..."
    systemctl stop docker
    apt-get purge -y -qq docker.io
    apt-get autoremove -y -qq
fi

print_msg "Binary extracted successfully"

# Create systemd service
print_msg "Creating systemd service..."
cat > /etc/systemd/system/dcgm-exporter.service <<EOF
[Unit]
Description=NVIDIA DCGM Exporter
Requires=nvidia-dcgm.service
After=nvidia-dcgm.service

[Service]
Type=simple
User=root
Restart=always
RestartSec=10
ExecStart=/usr/local/bin/dcgm-exporter \\
    -a 0.0.0.0:${DCGM_PORT} \\
    -c /etc/dcgm-exporter/default-counters.csv \\
    -d f
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start service
print_msg "Starting DCGM Exporter..."
systemctl daemon-reload
systemctl enable dcgm-exporter
systemctl start dcgm-exporter

# Wait for service to start
sleep 3

# Check if service is running
if systemctl is-active --quiet dcgm-exporter; then
    print_msg "DCGM Exporter started successfully!"
else
    print_error "DCGM Exporter failed to start"
    systemctl status dcgm-exporter --no-pager
    journalctl -u dcgm-exporter -n 50
    exit 1
fi

# Test metrics endpoint
print_msg "Testing metrics endpoint..."
sleep 2
if curl -s http://localhost:${DCGM_PORT}/metrics | grep -q "DCGM_FI_DEV_GPU_TEMP\|dcgm_gpu_temp"; then
    print_msg "Metrics endpoint is working!"
else
    print_warning "Metrics endpoint may not be responding yet. Check logs: sudo journalctl -u dcgm-exporter -f"
fi

# Update Prometheus config if it exists
if [ -f "/opt/prometheus/prometheus.yml" ]; then
    print_msg "Updating Prometheus configuration..."

    # Check if DCGM job already exists
    if ! grep -q "job_name: 'dcgm-exporter'" /opt/prometheus/prometheus.yml; then
        # Add DCGM exporter job to Prometheus config
        cat >> /opt/prometheus/prometheus.yml <<EOF

  # NVIDIA DCGM Exporter (GPU metrics)
  - job_name: 'dcgm-exporter'
    static_configs:
      - targets: ['localhost:${DCGM_PORT}']
        labels:
          service: 'dcgm-exporter'
          environment: 'production'
    scrape_interval: 10s
    scrape_timeout: 10s
EOF

        # Restart Prometheus
        print_msg "Restarting Prometheus..."
        systemctl restart prometheus
        print_msg "Prometheus configuration updated"
    else
        print_info "DCGM exporter already configured in Prometheus"
    fi
fi

# Configure firewall if UFW is active
if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
    print_msg "Configuring firewall..."
    ufw allow ${DCGM_PORT}/tcp comment 'DCGM Exporter'
fi

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "========================================="
print_msg "DCGM Exporter Installation Complete!"
echo "========================================="
echo ""
print_info "DCGM Exporter Endpoint:"
echo "  http://${SERVER_IP}:${DCGM_PORT}/metrics"
echo ""
print_info "Service Management:"
echo "  Status:  sudo systemctl status dcgm-exporter"
echo "  Restart: sudo systemctl restart dcgm-exporter"
echo "  Logs:    sudo journalctl -u dcgm-exporter -f"
echo ""
print_info "Key Metrics Exported:"
echo "  - GPU Temperature:        DCGM_FI_DEV_GPU_TEMP"
echo "  - GPU Utilization:        DCGM_FI_DEV_GPU_UTIL"
echo "  - Memory Usage:           DCGM_FI_DEV_MEM_COPY_UTIL"
echo "  - Power Usage:            DCGM_FI_DEV_POWER_USAGE"
echo "  - SM Clock:               DCGM_FI_DEV_SM_CLOCK"
echo "  - Memory Clock:           DCGM_FI_DEV_MEM_CLOCK"
echo "  - PCIe TX/RX:             DCGM_FI_DEV_PCIE_TX_THROUGHPUT"
echo "  - ECC Errors:             DCGM_FI_DEV_ECC_DBE_VOL_TOTAL"
echo "  - NVLink Throughput:      DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL"
echo ""
print_info "Test the endpoint:"
echo "  curl http://localhost:${DCGM_PORT}/metrics | grep DCGM_FI_DEV_GPU_TEMP"
echo ""

# Show sample metrics
print_msg "Sample GPU Metrics:"
curl -s http://localhost:${DCGM_PORT}/metrics 2>/dev/null | grep -E "DCGM_FI_DEV_(GPU_TEMP|GPU_UTIL|POWER_USAGE|SM_CLOCK)" | head -10 || print_warning "Metrics not available yet, wait 30 seconds and try again"

echo ""
exit 0
