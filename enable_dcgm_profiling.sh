#!/bin/bash
# Enable DCGM Profiling Metrics Configuration
#
# This script configures DCGM exporter to use a metrics file that includes
# profiling metrics (SM Activity, Compute Pipes, DRAM utilization, etc.)
#
# IMPORTANT: Profiling metrics require DCGM's profiling module, which may not
# be available on all GPU models or DCGM versions. Known limitations:
# - RTX PRO 6000 Blackwell: Profiling module not supported in DCGM 3.3.5-3.4.2
# - Consumer/Gaming GPUs: Profiling typically not supported
# - Datacenter GPUs (A100, H100, V100, L4, L40): Usually supported
#
# If profiling metrics are not available, the exporter will log warnings but
# will still export all standard metrics (temperature, utilization, power, etc.)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_msg() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[*]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root (use sudo)"
    exit 1
fi

echo "========================================="
echo "  Enable DCGM Profiling Metrics"
echo "========================================="
echo ""

DCGM_PORT="${DCGM_PORT:-9400}"

# Check if DCGM exporter is installed
if ! command -v dcgm-exporter &> /dev/null; then
    print_error "DCGM exporter is not installed"
    print_info "Install it first: sudo /opt/SystemMonitor/install_dcgm_exporter_native.sh"
    exit 1
fi

# Check if DCGM service is running
if ! systemctl is-active --quiet nvidia-dcgm; then
    print_error "DCGM service is not running"
    exit 1
fi

print_msg "DCGM service is running"

# Copy profiling metrics configuration
print_msg "Installing profiling metrics configuration..."
if [ -f "/opt/SystemMonitor/dcgm-metrics-profiling.csv" ]; then
    cp /opt/SystemMonitor/dcgm-metrics-profiling.csv /etc/dcgm-exporter/dcgm-metrics-profiling.csv
    print_msg "Metrics configuration installed"
else
    print_error "Profiling metrics CSV not found at /opt/SystemMonitor/dcgm-metrics-profiling.csv"
    exit 1
fi

# Update systemd service to use profiling configuration
print_msg "Updating DCGM Exporter service configuration..."
cat > /etc/systemd/system/dcgm-exporter.service <<EOF
[Unit]
Description=NVIDIA DCGM Exporter with Profiling
Requires=nvidia-dcgm.service
After=nvidia-dcgm.service

[Service]
Type=simple
User=root
Restart=always
RestartSec=10
ExecStart=/usr/local/bin/dcgm-exporter \\
    -a 0.0.0.0:${DCGM_PORT} \\
    -f /etc/dcgm-exporter/dcgm-metrics-profiling.csv
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and restart service
print_msg "Restarting DCGM Exporter with profiling enabled..."
systemctl daemon-reload
systemctl restart dcgm-exporter

# Wait for service to start
sleep 3

# Check if service is running
if systemctl is-active --quiet dcgm-exporter; then
    print_msg "DCGM Exporter restarted successfully with profiling enabled!"
else
    print_error "DCGM Exporter failed to start"
    print_info "Check logs: sudo journalctl -u dcgm-exporter -n 50"
    exit 1
fi

# Test for profiling metrics
print_msg "Testing for profiling metrics..."
sleep 5

if curl -s http://localhost:${DCGM_PORT}/metrics | grep -q "DCGM_FI_PROF_SM_ACTIVE\|DCGM_FI_PROF_PIPE"; then
    print_msg "Profiling metrics are available!"
    echo ""
    print_info "Sample profiling metrics:"
    curl -s http://localhost:${DCGM_PORT}/metrics | grep -E "DCGM_FI_PROF_(SM_ACTIVE|SM_OCCUPANCY|PIPE_TENSOR_ACTIVE|DRAM_ACTIVE)" | head -8
else
    print_warning "Profiling metrics not yet available"
    print_info "Some GPUs may not support all profiling metrics"
    print_info "Wait 10-15 seconds and check: curl http://localhost:${DCGM_PORT}/metrics | grep DCGM_FI_PROF"
fi

echo ""
echo "========================================="
print_msg "Profiling Configuration Complete"
echo "========================================="
echo ""
print_info "Enabled profiling metrics:"
echo "  - SM Activity & Occupancy"
echo "  - Compute Pipe Activity (Tensor, FP64, FP32, FP16)"
echo "  - DRAM Activity"
echo "  - PCIe & NVLink Profiling"
echo ""
print_info "Wait 10-15 seconds for Prometheus to scrape new metrics"
print_info "Then refresh your Grafana dashboard"
echo ""
print_info "Service management:"
echo "  Status:  sudo systemctl status dcgm-exporter"
echo "  Restart: sudo systemctl restart dcgm-exporter"
echo "  Logs:    sudo journalctl -u dcgm-exporter -f"
echo ""

exit 0
