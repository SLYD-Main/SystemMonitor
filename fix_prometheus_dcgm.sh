#!/bin/bash
# Fix Prometheus configuration to include DCGM exporter
# Run this if DCGM metrics aren't showing in Grafana

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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root (use sudo)"
    exit 1
fi

echo "========================================="
echo "  Prometheus DCGM Configuration Fix"
echo "========================================="
echo ""

DCGM_PORT="${DCGM_PORT:-9400}"

# Check if Prometheus config exists
if [ ! -f "/opt/prometheus/prometheus.yml" ]; then
    print_error "Prometheus configuration not found at /opt/prometheus/prometheus.yml"
    print_info "Is Prometheus installed? Run: sudo /opt/SystemMonitor/install_grafana.sh"
    exit 1
fi

# Check if DCGM exporter is running
if ! systemctl is-active --quiet dcgm-exporter; then
    print_error "DCGM exporter is not running"
    print_info "Install it with: sudo /opt/SystemMonitor/install_dcgm_exporter_native.sh"
    exit 1
fi

print_msg "DCGM exporter is running on port ${DCGM_PORT}"

# Check if DCGM is already in Prometheus config
if grep -q "job_name: 'dcgm-exporter'" /opt/prometheus/prometheus.yml; then
    print_info "DCGM exporter is already configured in Prometheus"
    print_info "Checking if target is being scraped..."

    # Wait for Prometheus to scrape
    sleep 2

    # Check if target is UP
    if curl -s 'http://localhost:9090/api/v1/targets' | grep -q '"job":"dcgm-exporter"'; then
        print_msg "DCGM target is being scraped by Prometheus!"

        # Check if metrics are available
        if curl -s 'http://localhost:9090/api/v1/query?query=DCGM_FI_DEV_GPU_TEMP' | grep -q '"result":\['; then
            print_msg "DCGM metrics are available in Prometheus!"
            echo ""
            print_info "Test query:"
            curl -s 'http://localhost:9090/api/v1/query?query=DCGM_FI_DEV_GPU_TEMP' | jq '.data.result[] | {gpu: .metric.gpu, temp: .value[1]}'
        else
            print_error "DCGM target is configured but no metrics are being collected"
            print_info "Wait 10-15 seconds for initial scrape, then check Prometheus targets at:"
            print_info "  http://$(hostname -I | awk '{print $1}'):9090/targets"
        fi
    else
        print_error "DCGM target is configured but not being scraped"
        print_info "Restarting Prometheus..."
        systemctl restart prometheus
        sleep 3
        print_msg "Prometheus restarted. Wait 10-15 seconds for scraping to start."
    fi
else
    print_info "Adding DCGM exporter to Prometheus configuration..."

    # Add DCGM exporter job
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

    print_msg "DCGM configuration added"

    # Restart Prometheus
    print_msg "Restarting Prometheus..."
    systemctl restart prometheus

    sleep 3

    if systemctl is-active --quiet prometheus; then
        print_msg "Prometheus restarted successfully"
        print_info "Wait 10-15 seconds for metrics to be scraped, then check:"
        print_info "  curl -s 'http://localhost:9090/api/v1/query?query=DCGM_FI_DEV_GPU_TEMP' | jq '.data.result'"
    else
        print_error "Prometheus failed to restart"
        print_info "Check logs: sudo journalctl -u prometheus -n 50"
        exit 1
    fi
fi

echo ""
echo "========================================="
print_msg "Configuration Complete"
echo "========================================="
echo ""
print_info "Next steps:"
echo "  1. Wait 10-15 seconds for Prometheus to scrape DCGM metrics"
echo "  2. Refresh your Grafana dashboard (Ctrl+Shift+R)"
echo "  3. Set time range to 'Last 5 minutes'"
echo "  4. Check Prometheus targets: http://$(hostname -I | awk '{print $1}'):9090/targets"
echo ""

exit 0
