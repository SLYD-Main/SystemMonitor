"""Advanced GPU stress testing and benchmarking suite."""
import time
import json
import csv
import threading
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime
import numpy as np


class GPUStressBenchmark:
    """Advanced GPU stress testing and benchmarking tool."""

    def __init__(self):
        """Initialize GPU stress benchmark."""
        self.torch_available = False
        self.pynvml_available = False
        self.gpu_count = 0
        self.metrics_history = []
        self.stop_monitoring = threading.Event()

        # Try to import PyTorch
        try:
            import torch
            self.torch = torch
            self.torch_available = torch.cuda.is_available()
            if self.torch_available:
                self.gpu_count = torch.cuda.device_count()
        except ImportError:
            pass

        # Try to import pynvml
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
        """
        Check if GPU stress benchmarking is available.

        Returns:
            True if PyTorch with CUDA is available
        """
        return self.torch_available

    @property
    def cuda_available(self) -> bool:
        """Check if CUDA is available."""
        return self.torch_available

    def monitor_gpu_metrics(self, device_id: int = 0, interval: float = 0.5):
        """
        Background thread to monitor GPU metrics during benchmarks.

        Args:
            device_id: GPU device ID
            interval: Sampling interval in seconds
        """
        if not self.pynvml_available:
            return

        handle = self.pynvml.nvmlDeviceGetHandleByIndex(device_id)

        while not self.stop_monitoring.is_set():
            try:
                metrics = {
                    'timestamp': time.time(),
                    'temperature': self.pynvml.nvmlDeviceGetTemperature(
                        handle, self.pynvml.NVML_TEMPERATURE_GPU
                    ),
                    'power_usage': self.pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0,
                    'utilization': self.pynvml.nvmlDeviceGetUtilizationRates(handle).gpu,
                    'memory_utilization': self.pynvml.nvmlDeviceGetUtilizationRates(handle).memory,
                }

                # Get memory info
                memory = self.pynvml.nvmlDeviceGetMemoryInfo(handle)
                metrics['memory_used_mb'] = memory.used / (1024**2)
                metrics['memory_free_mb'] = memory.free / (1024**2)

                # Get clock speeds
                try:
                    metrics['gpu_clock_mhz'] = self.pynvml.nvmlDeviceGetClockInfo(
                        handle, self.pynvml.NVML_CLOCK_GRAPHICS
                    )
                    metrics['memory_clock_mhz'] = self.pynvml.nvmlDeviceGetClockInfo(
                        handle, self.pynvml.NVML_CLOCK_MEM
                    )
                except:
                    pass

                # Check for throttling
                try:
                    perf_state = self.pynvml.nvmlDeviceGetPerformanceState(handle)
                    metrics['performance_state'] = perf_state
                except:
                    pass

                self.metrics_history.append(metrics)

            except Exception as e:
                print(f"Error monitoring metrics: {e}")

            time.sleep(interval)

    def benchmark_mixed_precision(
        self,
        device_id: int = 0,
        size: int = 8192,
        iterations: int = 100
    ) -> Dict:
        """
        Benchmark mixed precision performance (FP32, FP16, BF16).

        Args:
            device_id: GPU device ID
            size: Matrix size
            iterations: Number of iterations

        Returns:
            Benchmark results
        """
        if not self.torch_available:
            return {"error": "PyTorch with CUDA not available"}

        device = self.torch.device(f'cuda:{device_id}')
        results = {
            "device_id": device_id,
            "timestamp": datetime.now().isoformat(),
            "matrix_size": size,
            "iterations": iterations,
            "precisions": {}
        }

        # FP32 (Float32)
        print(f"Testing FP32 precision...")
        a_fp32 = self.torch.randn(size, size, device=device, dtype=self.torch.float32)
        b_fp32 = self.torch.randn(size, size, device=device, dtype=self.torch.float32)

        self.torch.cuda.synchronize()
        start = time.time()
        for _ in range(iterations):
            c = self.torch.matmul(a_fp32, b_fp32)
        self.torch.cuda.synchronize()
        fp32_time = time.time() - start

        fp32_tflops = (2 * size ** 3 * iterations) / (fp32_time * 1e12)
        results["precisions"]["fp32"] = {
            "total_time_seconds": fp32_time,
            "avg_time_ms": (fp32_time / iterations) * 1000,
            "tflops": fp32_tflops
        }

        # FP16 (Float16)
        print(f"Testing FP16 precision...")
        a_fp16 = self.torch.randn(size, size, device=device, dtype=self.torch.float16)
        b_fp16 = self.torch.randn(size, size, device=device, dtype=self.torch.float16)

        self.torch.cuda.synchronize()
        start = time.time()
        for _ in range(iterations):
            c = self.torch.matmul(a_fp16, b_fp16)
        self.torch.cuda.synchronize()
        fp16_time = time.time() - start

        fp16_tflops = (2 * size ** 3 * iterations) / (fp16_time * 1e12)
        results["precisions"]["fp16"] = {
            "total_time_seconds": fp16_time,
            "avg_time_ms": (fp16_time / iterations) * 1000,
            "tflops": fp16_tflops,
            "speedup_vs_fp32": fp32_time / fp16_time
        }

        # BF16 (BFloat16) - if supported
        try:
            print(f"Testing BF16 precision...")
            a_bf16 = self.torch.randn(size, size, device=device, dtype=self.torch.bfloat16)
            b_bf16 = self.torch.randn(size, size, device=device, dtype=self.torch.bfloat16)

            self.torch.cuda.synchronize()
            start = time.time()
            for _ in range(iterations):
                c = self.torch.matmul(a_bf16, b_bf16)
            self.torch.cuda.synchronize()
            bf16_time = time.time() - start

            bf16_tflops = (2 * size ** 3 * iterations) / (bf16_time * 1e12)
            results["precisions"]["bf16"] = {
                "total_time_seconds": bf16_time,
                "avg_time_ms": (bf16_time / iterations) * 1000,
                "tflops": bf16_tflops,
                "speedup_vs_fp32": fp32_time / bf16_time
            }
        except Exception as e:
            results["precisions"]["bf16"] = {"error": str(e)}

        # Cleanup
        del a_fp32, b_fp32, a_fp16, b_fp16
        if 'a_bf16' in locals():
            del a_bf16, b_bf16
        self.torch.cuda.empty_cache()

        return results

    def benchmark_memory_stress(
        self,
        device_id: int = 0,
        fill_percentage: float = 90.0,
        duration_seconds: int = 60
    ) -> Dict:
        """
        Stress test GPU memory by filling it and running operations.

        Args:
            device_id: GPU device ID
            fill_percentage: Percentage of memory to fill
            duration_seconds: Duration of stress test

        Returns:
            Stress test results
        """
        if not self.torch_available:
            return {"error": "PyTorch with CUDA not available"}

        device = self.torch.device(f'cuda:{device_id}')

        # Get total memory
        total_memory = self.torch.cuda.get_device_properties(device_id).total_memory
        target_memory = int(total_memory * (fill_percentage / 100.0))

        results = {
            "device_id": device_id,
            "timestamp": datetime.now().isoformat(),
            "total_memory_gb": total_memory / (1024**3),
            "target_memory_gb": target_memory / (1024**3),
            "fill_percentage": fill_percentage,
            "duration_seconds": duration_seconds
        }

        print(f"Allocating {target_memory / (1024**3):.2f} GB of GPU memory...")

        # Allocate tensors to fill memory
        tensors = []
        allocated = 0
        tensor_size = 100 * 1024 * 1024  # 100 MB chunks

        try:
            while allocated < target_memory:
                remaining = target_memory - allocated
                current_size = min(tensor_size, remaining) // 4  # 4 bytes per float32
                tensor = self.torch.randn(current_size, device=device)
                tensors.append(tensor)
                allocated += current_size * 4

            print(f"Allocated {allocated / (1024**3):.2f} GB")

            # Start monitoring
            self.metrics_history = []
            self.stop_monitoring.clear()
            monitor_thread = threading.Thread(
                target=self.monitor_gpu_metrics,
                args=(device_id, 0.5)
            )
            monitor_thread.start()

            # Run stress operations
            print(f"Running memory stress operations for {duration_seconds} seconds...")
            end_time = time.time() + duration_seconds
            operations = 0

            while time.time() < end_time:
                # Random memory operations
                idx1 = np.random.randint(0, len(tensors))
                idx2 = np.random.randint(0, len(tensors))

                # Perform operations that stress memory bandwidth
                _ = tensors[idx1] + tensors[idx2][:len(tensors[idx1])]
                operations += 1

            self.torch.cuda.synchronize()

            # Stop monitoring
            self.stop_monitoring.set()
            monitor_thread.join()

            results["operations_completed"] = operations
            results["metrics"] = self._analyze_metrics()

        except Exception as e:
            results["error"] = str(e)
        finally:
            # Cleanup
            del tensors
            self.torch.cuda.empty_cache()

        return results

    def benchmark_sustained_load(
        self,
        device_id: int = 0,
        duration_minutes: int = 10,
        workload_intensity: str = "high"
    ) -> Dict:
        """
        Run sustained load benchmark to test thermal throttling and stability.

        Args:
            device_id: GPU device ID
            duration_minutes: Test duration in minutes
            workload_intensity: "low", "medium", "high", or "extreme"

        Returns:
            Sustained load results
        """
        if not self.torch_available:
            return {"error": "PyTorch with CUDA not available"}

        device = self.torch.device(f'cuda:{device_id}')
        duration_seconds = duration_minutes * 60

        # Set workload size based on intensity
        intensity_configs = {
            "low": {"size": 2048, "batch_ops": 10},
            "medium": {"size": 4096, "batch_ops": 20},
            "high": {"size": 8192, "batch_ops": 50},
            "extreme": {"size": 16384, "batch_ops": 100}
        }

        config = intensity_configs.get(workload_intensity, intensity_configs["high"])
        size = config["size"]
        batch_ops = config["batch_ops"]

        results = {
            "device_id": device_id,
            "timestamp": datetime.now().isoformat(),
            "duration_minutes": duration_minutes,
            "workload_intensity": workload_intensity,
            "matrix_size": size
        }

        print(f"Starting {duration_minutes} minute sustained load test ({workload_intensity} intensity)...")
        print("This will push the GPU to maximum utilization...")

        # Start monitoring
        self.metrics_history = []
        self.stop_monitoring.clear()
        monitor_thread = threading.Thread(
            target=self.monitor_gpu_metrics,
            args=(device_id, 1.0)  # Sample every second
        )
        monitor_thread.start()

        try:
            # Allocate matrices
            a = self.torch.randn(size, size, device=device)
            b = self.torch.randn(size, size, device=device)

            end_time = time.time() + duration_seconds
            iterations = 0
            start_time = time.time()

            while time.time() < end_time:
                # Batch operations to maximize utilization
                for _ in range(batch_ops):
                    c = self.torch.matmul(a, b)
                    a = self.torch.sin(c)
                    iterations += 1

                # Print progress every minute
                elapsed = time.time() - start_time
                if int(elapsed) % 60 == 0 and iterations % 100 == 0:
                    remaining = (end_time - time.time()) / 60
                    print(f"  Progress: {elapsed/60:.1f}/{duration_minutes} minutes, "
                          f"{remaining:.1f} minutes remaining")

            self.torch.cuda.synchronize()

            # Stop monitoring
            self.stop_monitoring.set()
            monitor_thread.join()

            results["iterations_completed"] = iterations
            results["metrics"] = self._analyze_metrics()
            results["avg_iterations_per_second"] = iterations / duration_seconds

            # Check for throttling
            if self.metrics_history:
                temps = [m['temperature'] for m in self.metrics_history]
                results["thermal_throttling_detected"] = max(temps) > 85  # Typical throttle point

        except Exception as e:
            results["error"] = str(e)
            self.stop_monitoring.set()
            monitor_thread.join()
        finally:
            # Cleanup
            if 'a' in locals():
                del a, b, c
            self.torch.cuda.empty_cache()

        return results

    def benchmark_multi_gpu(self, duration_seconds: int = 60) -> Dict:
        """
        Benchmark all available GPUs simultaneously.

        Args:
            duration_seconds: Test duration

        Returns:
            Multi-GPU benchmark results
        """
        if not self.torch_available:
            return {"error": "PyTorch with CUDA not available"}

        if self.gpu_count < 2:
            return {"error": f"Only {self.gpu_count} GPU(s) available"}

        results = {
            "timestamp": datetime.now().isoformat(),
            "gpu_count": self.gpu_count,
            "duration_seconds": duration_seconds,
            "gpus": {}
        }

        print(f"Running multi-GPU benchmark on {self.gpu_count} GPUs...")

        def gpu_workload(gpu_id: int):
            """Workload for a single GPU."""
            device = self.torch.device(f'cuda:{gpu_id}')
            size = 4096

            a = self.torch.randn(size, size, device=device)
            b = self.torch.randn(size, size, device=device)

            end_time = time.time() + duration_seconds
            iterations = 0

            while time.time() < end_time:
                c = self.torch.matmul(a, b)
                a = self.torch.sin(c)
                iterations += 1

            self.torch.cuda.synchronize(device)
            return iterations

        # Run on all GPUs in parallel
        threads = []
        gpu_results = {}

        for gpu_id in range(self.gpu_count):
            def worker(gid=gpu_id):
                gpu_results[gid] = gpu_workload(gid)

            thread = threading.Thread(target=worker)
            thread.start()
            threads.append(thread)

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Collect results
        for gpu_id, iterations in gpu_results.items():
            results["gpus"][f"gpu_{gpu_id}"] = {
                "iterations": iterations,
                "avg_iterations_per_second": iterations / duration_seconds
            }

        return results

    def run_benchmark_suite(
        self,
        device_id: int = 0,
        suite_type: str = "standard"
    ) -> Dict:
        """
        Run a complete benchmark suite.

        Args:
            device_id: GPU device ID
            suite_type: "quick", "standard", or "comprehensive"

        Returns:
            Complete benchmark suite results
        """
        suites = {
            "quick": {
                "mixed_precision": {"size": 4096, "iterations": 50},
                "memory_stress": {"fill_percentage": 80, "duration_seconds": 30},
                "sustained_load": {"duration_minutes": 2, "intensity": "medium"}
            },
            "standard": {
                "mixed_precision": {"size": 8192, "iterations": 100},
                "memory_stress": {"fill_percentage": 90, "duration_seconds": 60},
                "sustained_load": {"duration_minutes": 5, "intensity": "high"}
            },
            "comprehensive": {
                "mixed_precision": {"size": 16384, "iterations": 200},
                "memory_stress": {"fill_percentage": 95, "duration_seconds": 120},
                "sustained_load": {"duration_minutes": 10, "intensity": "extreme"}
            }
        }

        suite_config = suites.get(suite_type, suites["standard"])

        results = {
            "timestamp": datetime.now().isoformat(),
            "device_id": device_id,
            "suite_type": suite_type,
            "benchmarks": {}
        }

        print(f"\n{'='*60}")
        print(f"Running {suite_type.upper()} benchmark suite on GPU {device_id}")
        print(f"{'='*60}\n")

        # Mixed precision
        print("[1/3] Mixed Precision Benchmark")
        results["benchmarks"]["mixed_precision"] = self.benchmark_mixed_precision(
            device_id, **suite_config["mixed_precision"]
        )

        # Memory stress
        print("\n[2/3] Memory Stress Test")
        results["benchmarks"]["memory_stress"] = self.benchmark_memory_stress(
            device_id, **suite_config["memory_stress"]
        )

        # Sustained load
        print("\n[3/3] Sustained Load Test")
        results["benchmarks"]["sustained_load"] = self.benchmark_sustained_load(
            device_id, **suite_config["sustained_load"]
        )

        print(f"\n{'='*60}")
        print("Benchmark suite complete!")
        print(f"{'='*60}\n")

        return results

    def export_results(
        self,
        results: Dict,
        output_dir: str = "./benchmark_results",
        formats: List[str] = ["json", "csv"]
    ) -> Dict[str, str]:
        """
        Export benchmark results to files.

        Args:
            results: Benchmark results dictionary
            output_dir: Output directory
            formats: List of formats ("json", "csv")

        Returns:
            Dictionary of format -> filepath
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepaths = {}

        # JSON export
        if "json" in formats:
            json_file = output_path / f"benchmark_{timestamp}.json"
            with open(json_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            filepaths["json"] = str(json_file)

        # CSV export (metrics history)
        if "csv" in formats and self.metrics_history:
            csv_file = output_path / f"metrics_{timestamp}.csv"
            with open(csv_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.metrics_history[0].keys())
                writer.writeheader()
                writer.writerows(self.metrics_history)
            filepaths["csv"] = str(csv_file)

        return filepaths

    def _analyze_metrics(self) -> Dict:
        """Analyze collected metrics history."""
        if not self.metrics_history:
            return {}

        temps = [m['temperature'] for m in self.metrics_history]
        power = [m['power_usage'] for m in self.metrics_history]
        util = [m['utilization'] for m in self.metrics_history]

        return {
            "temperature": {
                "min": min(temps),
                "max": max(temps),
                "avg": np.mean(temps),
                "std": np.std(temps)
            },
            "power_usage": {
                "min": min(power),
                "max": max(power),
                "avg": np.mean(power),
                "std": np.std(power)
            },
            "utilization": {
                "min": min(util),
                "max": max(util),
                "avg": np.mean(util),
                "std": np.std(util)
            },
            "total_samples": len(self.metrics_history)
        }
