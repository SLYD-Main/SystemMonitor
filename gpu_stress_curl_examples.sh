#!/bin/bash
# Individual GPU Stress Test Commands
# Copy and paste these commands to run specific tests

API="https://port8000-92732dbb-f4a3-4594-83de-f33d0ff100fe.slyd.cloud"

# Check GPU stress capabilities
echo "# Check GPU stress capabilities"
echo "curl -s ${API}/api/gpu/stress/info | jq '.'"
echo ""

# Mixed Precision Benchmark
echo "# Mixed Precision Benchmark (FP32, FP16, BF16)"
echo "curl -s -X POST '${API}/api/gpu/stress/mixed-precision?device_id=0' | jq '.'"
echo ""

# Memory Stress Test (90% fill, 2 minutes)
echo "# Memory Stress Test - 90% fill for 2 minutes"
echo "curl -s -X POST '${API}/api/gpu/stress/memory-stress?device_id=0&fill_percentage=0.9&duration_seconds=120' | jq '.'"
echo ""

# Memory Stress Test (95% fill, 10 minutes) - EXTREME
echo "# Memory Stress Test - EXTREME (95% fill for 10 minutes)"
echo "curl -s -X POST '${API}/api/gpu/stress/memory-stress?device_id=0&fill_percentage=0.95&duration_seconds=600' | jq '.'"
echo ""

# Sustained Load - High intensity for 10 minutes
echo "# Sustained Load - High intensity for 10 minutes"
echo "curl -s -X POST '${API}/api/gpu/stress/sustained-load?device_id=0&duration_minutes=10&workload_intensity=high' | jq '.'"
echo ""

# Sustained Load - EXTREME intensity for 30 minutes
echo "# Sustained Load - EXTREME intensity for 30 minutes"
echo "curl -s -X POST '${API}/api/gpu/stress/sustained-load?device_id=0&duration_minutes=30&workload_intensity=extreme' | jq '.'"
echo ""

# Quick Suite
echo "# Quick Benchmark Suite (fastest)"
echo "curl -s -X POST '${API}/api/gpu/stress/suite?device_id=0&suite_type=quick' | jq '.'"
echo ""

# Standard Suite
echo "# Standard Benchmark Suite"
echo "curl -s -X POST '${API}/api/gpu/stress/suite?device_id=0&suite_type=standard' | jq '.'"
echo ""

# Comprehensive Suite with Export
echo "# Comprehensive Benchmark Suite with Export"
echo "curl -s -X POST '${API}/api/gpu/stress/suite?device_id=0&suite_type=comprehensive&export_results=true' | jq '.'"
echo ""

# Check GPU status
echo "# Check current GPU status"
echo "curl -s ${API}/api/gpu | jq '.'"
echo ""

# Monitor GPU while testing (run in separate terminal)
echo "# Monitor GPU during tests (run in separate terminal)"
echo "watch -n 1 'curl -s ${API}/api/gpu | jq \".gpus[0] | {name, temperature, utilization, memory_used, power_draw}\"'"
echo ""