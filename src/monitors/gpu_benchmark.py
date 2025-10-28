"""GPU benchmarking module."""
import time
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import threading


class GPUBenchmark:
    """GPU benchmarking tool for performance testing."""

    def __init__(self):
        """Initialize GPU benchmark."""
        self.torch_available = False
        self.pynvml_available = False
        self.gpu_count = 0

        # Try to import PyTorch for GPU compute benchmarks
        try:
            import torch
            self.torch = torch
            self.torch_available = torch.cuda.is_available()
            if self.torch_available:
                self.gpu_count = torch.cuda.device_count()
        except ImportError:
            pass

        # Try to import pynvml for GPU monitoring
        try:
            import pynvml
            pynvml.nvmlInit()
            self.pynvml = pynvml
            self.pynvml_available = True
            if not self.torch_available and self.pynvml_available:
                self.gpu_count = pynvml.nvmlDeviceGetCount()
        except:
            pass

    def is_available(self) -> bool:
        """Check if GPU benchmarking is available."""
        return self.torch_available or self.pynvml_available

    def get_gpu_info(self, device_id: int = 0) -> Dict:
        """
        Get GPU information.

        Args:
            device_id: GPU device ID

        Returns:
            Dictionary with GPU information
        """
        info = {
            "device_id": device_id,
            "timestamp": datetime.now().isoformat()
        }

        if self.torch_available:
            props = self.torch.cuda.get_device_properties(device_id)
            info.update({
                "name": props.name,
                "compute_capability": f"{props.major}.{props.minor}",
                "total_memory": props.total_memory,
                "total_memory_gb": props.total_memory / (1024**3),
                "multi_processor_count": props.multi_processor_count,
                "cuda_available": True
            })
        elif self.pynvml_available:
            handle = self.pynvml.nvmlDeviceGetHandleByIndex(device_id)
            name = self.pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode('utf-8')
            memory = self.pynvml.nvmlDeviceGetMemoryInfo(handle)
            info.update({
                "name": name,
                "total_memory": memory.total,
                "total_memory_gb": memory.total / (1024**3),
                "cuda_available": False
            })

        return info

    def benchmark_memory_bandwidth(self, device_id: int = 0, size_mb: int = 100) -> Dict:
        """
        Benchmark GPU memory bandwidth.

        Args:
            device_id: GPU device ID
            size_mb: Size of data to transfer in MB

        Returns:
            Dictionary with benchmark results
        """
        if not self.torch_available:
            return {
                "error": "PyTorch with CUDA not available",
                "message": "Install torch with CUDA support for GPU compute benchmarks"
            }

        try:
            device = self.torch.device(f'cuda:{device_id}')
            size = size_mb * 1024 * 1024 // 4  # Convert MB to number of float32 elements

            results = {
                "device_id": device_id,
                "timestamp": datetime.now().isoformat(),
                "size_mb": size_mb,
                "tests": {}
            }

            # Host to Device transfer
            cpu_data = self.torch.randn(size)
            self.torch.cuda.synchronize()
            start = time.time()
            gpu_data = cpu_data.to(device)
            self.torch.cuda.synchronize()
            h2d_time = time.time() - start
            h2d_bandwidth = size_mb / h2d_time

            results["tests"]["host_to_device"] = {
                "time_seconds": h2d_time,
                "bandwidth_mb_per_sec": h2d_bandwidth,
                "bandwidth_gb_per_sec": h2d_bandwidth / 1024
            }

            # Device to Host transfer
            self.torch.cuda.synchronize()
            start = time.time()
            cpu_result = gpu_data.cpu()
            self.torch.cuda.synchronize()
            d2h_time = time.time() - start
            d2h_bandwidth = size_mb / d2h_time

            results["tests"]["device_to_host"] = {
                "time_seconds": d2h_time,
                "bandwidth_mb_per_sec": d2h_bandwidth,
                "bandwidth_gb_per_sec": d2h_bandwidth / 1024
            }

            # Device to Device copy
            self.torch.cuda.synchronize()
            start = time.time()
            gpu_copy = gpu_data.clone()
            self.torch.cuda.synchronize()
            d2d_time = time.time() - start
            d2d_bandwidth = size_mb / d2d_time

            results["tests"]["device_to_device"] = {
                "time_seconds": d2d_time,
                "bandwidth_mb_per_sec": d2d_bandwidth,
                "bandwidth_gb_per_sec": d2d_bandwidth / 1024
            }

            # Clean up
            del cpu_data, gpu_data, cpu_result, gpu_copy
            self.torch.cuda.empty_cache()

            return results

        except Exception as e:
            return {
                "error": str(e),
                "device_id": device_id
            }

    def benchmark_compute_performance(self, device_id: int = 0, matrix_size: int = 4096) -> Dict:
        """
        Benchmark GPU compute performance using matrix operations.

        Args:
            device_id: GPU device ID
            matrix_size: Size of matrices for computation

        Returns:
            Dictionary with benchmark results
        """
        if not self.torch_available:
            return {
                "error": "PyTorch with CUDA not available",
                "message": "Install torch with CUDA support for GPU compute benchmarks"
            }

        try:
            device = self.torch.device(f'cuda:{device_id}')

            results = {
                "device_id": device_id,
                "timestamp": datetime.now().isoformat(),
                "matrix_size": matrix_size,
                "operations": {}
            }

            # Matrix multiplication benchmark (FP32)
            a = self.torch.randn(matrix_size, matrix_size, device=device)
            b = self.torch.randn(matrix_size, matrix_size, device=device)

            # Warmup
            _ = self.torch.matmul(a, b)
            self.torch.cuda.synchronize()

            # Benchmark
            iterations = 10
            start = time.time()
            for _ in range(iterations):
                c = self.torch.matmul(a, b)
            self.torch.cuda.synchronize()
            elapsed = time.time() - start

            # Calculate FLOPS
            ops_per_matmul = 2 * matrix_size ** 3  # FLOPs for matrix multiplication
            total_ops = ops_per_matmul * iterations
            flops = total_ops / elapsed

            results["operations"]["matmul_fp32"] = {
                "iterations": iterations,
                "total_time_seconds": elapsed,
                "avg_time_seconds": elapsed / iterations,
                "gflops": flops / 1e9,
                "tflops": flops / 1e12
            }

            # Element-wise operations
            self.torch.cuda.synchronize()
            start = time.time()
            for _ in range(iterations):
                d = a + b
                d = d * 2.0
                d = self.torch.sin(d)
            self.torch.cuda.synchronize()
            elapsed = time.time() - start

            results["operations"]["elementwise"] = {
                "iterations": iterations,
                "total_time_seconds": elapsed,
                "avg_time_seconds": elapsed / iterations
            }

            # Clean up
            del a, b, c, d
            self.torch.cuda.empty_cache()

            return results

        except Exception as e:
            return {
                "error": str(e),
                "device_id": device_id
            }

    def stress_test(self, device_id: int = 0, duration_seconds: int = 10) -> Dict:
        """
        Run a GPU stress test.

        Args:
            device_id: GPU device ID
            duration_seconds: Duration of stress test

        Returns:
            Dictionary with stress test results
        """
        if not self.torch_available:
            return {
                "error": "PyTorch with CUDA not available",
                "message": "Install torch with CUDA support for GPU compute benchmarks"
            }

        try:
            device = self.torch.device(f'cuda:{device_id}')

            results = {
                "device_id": device_id,
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": duration_seconds,
                "metrics": {
                    "temperature": [],
                    "power": [],
                    "utilization": [],
                    "memory_used": []
                }
            }

            # Monitoring function
            stop_monitoring = threading.Event()

            def monitor_gpu():
                if self.pynvml_available:
                    handle = self.pynvml.nvmlDeviceGetHandleByIndex(device_id)
                    while not stop_monitoring.is_set():
                        try:
                            temp = self.pynvml.nvmlDeviceGetTemperature(handle, self.pynvml.NVML_TEMPERATURE_GPU)
                            power = self.pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
                            util = self.pynvml.nvmlDeviceGetUtilizationRates(handle)
                            memory = self.pynvml.nvmlDeviceGetMemoryInfo(handle)

                            results["metrics"]["temperature"].append(temp)
                            results["metrics"]["power"].append(power)
                            results["metrics"]["utilization"].append(util.gpu)
                            results["metrics"]["memory_used"].append(memory.used / (1024**3))
                        except:
                            pass
                        time.sleep(0.5)

            # Start monitoring
            monitor_thread = threading.Thread(target=monitor_gpu)
            monitor_thread.start()

            # Run stress test
            size = 4096
            end_time = time.time() + duration_seconds
            iterations = 0

            while time.time() < end_time:
                a = self.torch.randn(size, size, device=device)
                b = self.torch.randn(size, size, device=device)
                c = self.torch.matmul(a, b)
                d = self.torch.sin(c)
                iterations += 1
                del a, b, c, d

            self.torch.cuda.synchronize()

            # Stop monitoring
            stop_monitoring.set()
            monitor_thread.join()

            # Calculate statistics
            if results["metrics"]["temperature"]:
                results["statistics"] = {
                    "iterations": iterations,
                    "temperature": {
                        "min": min(results["metrics"]["temperature"]),
                        "max": max(results["metrics"]["temperature"]),
                        "avg": sum(results["metrics"]["temperature"]) / len(results["metrics"]["temperature"])
                    },
                    "power": {
                        "min": min(results["metrics"]["power"]),
                        "max": max(results["metrics"]["power"]),
                        "avg": sum(results["metrics"]["power"]) / len(results["metrics"]["power"])
                    } if results["metrics"]["power"] else None,
                    "utilization": {
                        "min": min(results["metrics"]["utilization"]),
                        "max": max(results["metrics"]["utilization"]),
                        "avg": sum(results["metrics"]["utilization"]) / len(results["metrics"]["utilization"])
                    } if results["metrics"]["utilization"] else None
                }

            self.torch.cuda.empty_cache()

            return results

        except Exception as e:
            return {
                "error": str(e),
                "device_id": device_id
            }

    def run_full_benchmark(self, device_id: int = 0) -> Dict:
        """
        Run a comprehensive GPU benchmark suite.

        Args:
            device_id: GPU device ID

        Returns:
            Dictionary with all benchmark results
        """
        if not self.is_available():
            return {
                "error": "No GPU or GPU libraries available",
                "torch_available": self.torch_available,
                "pynvml_available": self.pynvml_available
            }

        results = {
            "timestamp": datetime.now().isoformat(),
            "device_id": device_id,
            "gpu_info": self.get_gpu_info(device_id),
            "benchmarks": {}
        }

        if self.torch_available:
            results["benchmarks"]["memory_bandwidth"] = self.benchmark_memory_bandwidth(device_id)
            results["benchmarks"]["compute_performance"] = self.benchmark_compute_performance(device_id)
            results["benchmarks"]["stress_test"] = self.stress_test(device_id, duration_seconds=5)
        else:
            results["message"] = "PyTorch with CUDA not available. Install torch for compute benchmarks."

        return results
