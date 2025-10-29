#!/bin/bash
# GPU Stress Testing Automation Script
# Runs comprehensive GPU stress tests and saves results

API_ENDPOINT="https://port8000-92732dbb-f4a3-4594-83de-f33d0ff100fe.slyd.cloud"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="./gpu_stress_results_${TIMESTAMP}"
mkdir -p "$RESULTS_DIR"

echo "=========================================="
echo "  GPU Stress Testing Suite"
echo "  Timestamp: $TIMESTAMP"
echo "  API: $API_ENDPOINT"
echo "=========================================="
echo ""

# Check GPU stress capabilities
echo "[1/6] Checking GPU stress testing capabilities..."
curl -s "${API_ENDPOINT}/api/gpu/stress/info" | tee "$RESULTS_DIR/gpu_stress_info.json" | jq '.'
echo ""
sleep 2

# Mixed Precision Benchmark
echo "[2/6] Running Mixed Precision Benchmark (FP32, FP16, BF16)..."
echo "  This tests TFLOPS performance across different precision modes"
curl -s -X POST "${API_ENDPOINT}/api/gpu/stress/mixed-precision?device_id=0&size=4096&iterations=100" \
  | tee "$RESULTS_DIR/01_mixed_precision.json" | jq '.test_name, .results'
echo ""
sleep 2

# Memory Stress Test
echo "[3/6] Running Memory Stress Test..."
echo "  Filling 90% of GPU memory and running continuous operations for 2 minutes"
curl -s -X POST "${API_ENDPOINT}/api/gpu/stress/memory-stress?device_id=0&fill_percentage=0.9&duration_seconds=120" \
  | tee "$RESULTS_DIR/02_memory_stress.json" | jq '.test_name, .memory_allocated_gb, .operations_completed'
echo ""
sleep 2

# Sustained Load Test
echo "[4/6] Running Sustained Load Test..."
echo "  High intensity sustained load for 5 minutes to test thermal behavior"
curl -s -X POST "${API_ENDPOINT}/api/gpu/stress/sustained-load?device_id=0&duration_minutes=5&workload_intensity=high" \
  | tee "$RESULTS_DIR/03_sustained_load.json" | jq '.test_name, .duration_minutes, .workload_intensity, .metrics_summary'
echo ""
sleep 2

# Quick Suite
echo "[5/6] Running Quick Benchmark Suite..."
echo "  This runs a quick version of all tests"
curl -s -X POST "${API_ENDPOINT}/api/gpu/stress/suite?device_id=0&suite_type=quick" \
  | tee "$RESULTS_DIR/04_quick_suite.json" | jq '.suite_type, .tests | keys'
echo ""
sleep 2

# Standard Suite with Export
echo "[6/6] Running Standard Benchmark Suite with Export..."
echo "  This is the full standard test suite - will take several minutes"
curl -s -X POST "${API_ENDPOINT}/api/gpu/stress/suite?device_id=0&suite_type=standard&export_results=true&output_dir=/opt/SystemMonitor/benchmark_results" \
  | tee "$RESULTS_DIR/05_standard_suite.json" | jq '.suite_type, .total_duration_seconds, .tests | keys'
echo ""

# Final GPU Status
echo "[FINAL] Checking GPU status after stress tests..."
curl -s "${API_ENDPOINT}/api/gpu" | tee "$RESULTS_DIR/final_gpu_status.json" | jq '.'
echo ""

echo "=========================================="
echo "  All Tests Complete!"
echo "=========================================="
echo ""
echo "Results saved to: $RESULTS_DIR"
echo ""
echo "Summary of test files:"
ls -lh "$RESULTS_DIR"
echo ""
echo "To view any result:"
echo "  cat $RESULTS_DIR/<filename>.json | jq '.'"
echo ""
