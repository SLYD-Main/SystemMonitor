#!/usr/bin/env python3
"""Test script for GPU benchmark functionality."""

from src.monitors.gpu_benchmark import GPUBenchmark
import json

print("Testing GPU Benchmark Module...")
print("=" * 70)

benchmark = GPUBenchmark()

print(f"\nGPU Available: {benchmark.is_available()}")
print(f"PyTorch Available: {benchmark.torch_available}")
print(f"pynvml Available: {benchmark.pynvml_available}")
print(f"GPU Count: {benchmark.gpu_count}")

if not benchmark.is_available():
    print("\nNo GPU or GPU libraries available.")
    print("\nTo enable GPU benchmarks:")
    print("1. Install PyTorch with CUDA:")
    print("   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")
    print("2. Or install pynvml:")
    print("   pip install pynvml")
    exit(0)

print("\n" + "=" * 70)
print("Getting GPU Info...")
print("=" * 70)

try:
    info = benchmark.get_gpu_info(0)
    print(json.dumps(info, indent=2, default=str))

    if benchmark.torch_available:
        print("\n" + "=" * 70)
        print("PyTorch is available - Full benchmarks can be run!")
        print("=" * 70)
        print("\nTo run benchmarks:")
        print("  python main.py gpu-benchmark --test info")
        print("  python main.py gpu-benchmark --test memory")
        print("  python main.py gpu-benchmark --test compute")
        print("  python main.py gpu-benchmark --test stress")
        print("  python main.py gpu-benchmark --test full")
    else:
        print("\n" + "=" * 70)
        print("PyTorch not available - Only GPU info available")
        print("=" * 70)
        print("\nInstall PyTorch to run compute benchmarks:")
        print("  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
