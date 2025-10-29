"""REST API server for system monitoring."""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
from typing import Optional, Dict, List
from datetime import datetime
import uvicorn
from pathlib import Path

from ..monitors.cpu import CPUMonitor
from ..monitors.memory import MemoryMonitor
from ..monitors.disk import DiskMonitor
from ..monitors.network import NetworkMonitor
from ..monitors.gpu import GPUMonitor
from ..monitors.speedtest import SpeedTestMonitor
from ..monitors.gpu_benchmark import GPUBenchmark
from ..monitors.gpu_stress_benchmark import GPUStressBenchmark
from ..storage.database import HistoricalDatabase
from ..storage.exporter import DataExporter
from ..alerts.alert_manager import AlertManager
from ..metrics.prometheus_exporter import PrometheusExporter
from ..config import Config


class MonitoringAPI:
    """REST API for system monitoring."""

    def __init__(self, config: Config = None):
        """
        Initialize the monitoring API.

        Args:
            config: Configuration instance
        """
        self.config = config or Config()
        self.app = FastAPI(
            title="System Monitor API",
            description="Hardware monitoring API for CPU, Memory, Disk, Network, and GPU",
            version="1.0.0"
        )

        # Initialize monitors
        self.cpu_monitor = CPUMonitor()
        self.memory_monitor = MemoryMonitor()
        self.disk_monitor = DiskMonitor()
        self.network_monitor = NetworkMonitor()
        self.gpu_monitor = GPUMonitor()
        self.speedtest_monitor = SpeedTestMonitor()
        self.gpu_benchmark = GPUBenchmark()
        self.gpu_stress_benchmark = GPUStressBenchmark()

        # Initialize storage and alerts
        self.db = HistoricalDatabase()
        self.exporter = DataExporter(self.config.get("export.directory", "./exports"))
        self.alert_manager = AlertManager(self.config.get_thresholds())

        # Initialize Prometheus exporter
        self.prometheus_exporter = PrometheusExporter()

        # Configure CORS
        if self.config.get("api.enable_cors", True):
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        self._setup_routes()

    def _setup_routes(self):
        """Set up API routes."""

        @self.app.get("/")
        async def root():
            """API root endpoint."""
            return {
                "name": "System Monitor API",
                "version": "1.0.0",
                "endpoints": {
                    "snapshot": "/api/snapshot",
                    "cpu": "/api/cpu",
                    "memory": "/api/memory",
                    "disk": "/api/disk",
                    "network": "/api/network",
                    "gpu": "/api/gpu",
                    "gpu_benchmark": "/api/gpu/benchmark",
                    "gpu_stress": "/api/gpu/stress",
                    "speedtest": "/api/speedtest",
                    "history": "/api/history/{metric}",
                    "alerts": "/api/alerts",
                    "export": "/api/export",
                    "metrics": "/metrics"
                }
            }

        @self.app.get("/api/snapshot")
        async def get_snapshot():
            """Get complete system snapshot."""
            try:
                snapshot = {
                    "timestamp": datetime.now().isoformat(),
                    "cpu": self.cpu_monitor.get_usage(interval=0.1),
                    "memory": self.memory_monitor.get_memory(),
                    "disk": self.disk_monitor.get_complete_stats(),
                    "network": self.network_monitor.get_io_counters(per_nic=True),
                    "gpu": self.gpu_monitor.get_all_gpus()
                }

                # Check for alerts
                alerts = self.alert_manager.check_all(snapshot)

                return {
                    "data": snapshot,
                    "alerts": [alert.to_dict() for alert in alerts]
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/cpu")
        async def get_cpu(
            interval: float = Query(0.1, description="Measurement interval in seconds"),
            per_cpu: bool = Query(False, description="Get per-CPU statistics")
        ):
            """Get CPU statistics."""
            try:
                data = self.cpu_monitor.get_usage(interval=interval, per_cpu=per_cpu)
                return data
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/cpu/stats")
        async def get_cpu_stats():
            """Get detailed CPU statistics."""
            try:
                return self.cpu_monitor.get_stats()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/memory")
        async def get_memory(readable: bool = Query(False, description="Return human-readable format")):
            """Get memory statistics."""
            try:
                if readable:
                    return self.memory_monitor.get_readable_memory()
                return self.memory_monitor.get_memory()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/disk")
        async def get_disk():
            """Get disk statistics."""
            try:
                return self.disk_monitor.get_complete_stats()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/disk/usage")
        async def get_disk_usage(path: str = Query("/", description="Path to check")):
            """Get disk usage for specific path."""
            try:
                return self.disk_monitor.get_disk_usage(path)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/network")
        async def get_network(per_nic: bool = Query(False, description="Get per-interface statistics")):
            """Get network I/O statistics."""
            try:
                return self.network_monitor.get_io_counters(per_nic=per_nic)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/network/speed")
        async def get_network_speed(
            interval: float = Query(1.0, description="Measurement interval in seconds"),
            per_nic: bool = Query(False, description="Get per-interface speeds")
        ):
            """Get network speed."""
            try:
                return self.network_monitor.get_speed(interval=interval, per_nic=per_nic)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/network/interfaces")
        async def get_network_interfaces():
            """Get network interface information."""
            try:
                return self.network_monitor.get_interface_addresses()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/gpu")
        async def get_gpu():
            """Get GPU statistics."""
            try:
                return self.gpu_monitor.get_all_gpus()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/speedtest")
        async def run_speedtest(server_id: Optional[int] = Query(None, description="Specific server ID to test")):
            """Run an internet speed test (may take 30-60 seconds)."""
            try:
                result = self.speedtest_monitor.run_speedtest(server_id=server_id)
                if 'error' in result:
                    raise HTTPException(status_code=500, detail=result.get('error'))
                return result
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/speedtest/last")
        async def get_last_speedtest():
            """Get the last speed test results."""
            try:
                result = self.speedtest_monitor.get_last_test()
                if result is None:
                    return {
                        "message": "No speed test has been run yet",
                        "last_test": None
                    }
                return result
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/speedtest/servers")
        async def get_speedtest_servers(limit: int = Query(10, description="Maximum number of servers to return")):
            """Get list of available speed test servers."""
            try:
                return self.speedtest_monitor.get_available_servers(limit=limit)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/speedtest/client")
        async def get_client_info():
            """Get client IP and ISP information."""
            try:
                return self.speedtest_monitor.get_client_info()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/gpu/benchmark")
        async def run_gpu_benchmark(
            device_id: int = Query(0, description="GPU device ID"),
            test_type: str = Query("full", description="Benchmark type: info, memory, compute, stress, resnet, bert, mlperf, full"),
            duration: int = Query(10, description="Stress test duration in seconds"),
            include_mlperf: bool = Query(False, description="Include MLPerf benchmarks in full test")
        ):
            """Run GPU benchmark tests."""
            try:
                if not self.gpu_benchmark.is_available():
                    raise HTTPException(
                        status_code=400,
                        detail="No GPU or GPU libraries available. Install PyTorch with CUDA or pynvml."
                    )

                if test_type == "info":
                    result = self.gpu_benchmark.get_gpu_info(device_id)
                elif test_type == "memory":
                    result = self.gpu_benchmark.benchmark_memory_bandwidth(device_id)
                elif test_type == "compute":
                    result = self.gpu_benchmark.benchmark_compute_performance(device_id)
                elif test_type == "stress":
                    result = self.gpu_benchmark.stress_test(device_id, duration_seconds=duration)
                elif test_type == "resnet":
                    result = self.gpu_benchmark.benchmark_resnet_inference(device_id)
                elif test_type == "bert":
                    result = self.gpu_benchmark.benchmark_bert_inference(device_id)
                elif test_type == "mlperf":
                    result = self.gpu_benchmark.benchmark_mlperf_suite(device_id)
                elif test_type == "full":
                    result = self.gpu_benchmark.run_full_benchmark(device_id, include_mlperf=include_mlperf)
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid test_type. Must be one of: info, memory, compute, stress, resnet, bert, mlperf, full"
                    )

                if 'error' in result:
                    raise HTTPException(status_code=500, detail=result.get('error'))

                return result
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/gpu/benchmark/mlperf")
        async def run_mlperf_benchmark(
            device_id: int = Query(0, description="GPU device ID")
        ):
            """Run MLPerf-style inference benchmark suite."""
            try:
                if not self.gpu_benchmark.is_available():
                    raise HTTPException(
                        status_code=400,
                        detail="No GPU or GPU libraries available"
                    )

                if not self.gpu_benchmark.torch_available:
                    raise HTTPException(
                        status_code=400,
                        detail="PyTorch with CUDA not available. Install torch and torchvision for MLPerf benchmarks."
                    )

                result = self.gpu_benchmark.benchmark_mlperf_suite(device_id)

                if 'error' in result:
                    raise HTTPException(status_code=500, detail=result.get('error'))

                return result
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/gpu/benchmark/resnet")
        async def run_resnet_benchmark(
            device_id: int = Query(0, description="GPU device ID"),
            batch_size: int = Query(32, description="Batch size for inference"),
            iterations: int = Query(100, description="Number of iterations")
        ):
            """Run ResNet-50 inference benchmark."""
            try:
                if not self.gpu_benchmark.torch_available:
                    raise HTTPException(
                        status_code=400,
                        detail="PyTorch with CUDA not available"
                    )

                result = self.gpu_benchmark.benchmark_resnet_inference(
                    device_id=device_id,
                    batch_size=batch_size,
                    iterations=iterations
                )

                if 'error' in result:
                    raise HTTPException(status_code=500, detail=result.get('error'))

                return result
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/gpu/benchmark/bert")
        async def run_bert_benchmark(
            device_id: int = Query(0, description="GPU device ID"),
            batch_size: int = Query(8, description="Batch size for inference"),
            seq_length: int = Query(128, description="Sequence length"),
            iterations: int = Query(50, description="Number of iterations")
        ):
            """Run BERT inference benchmark."""
            try:
                if not self.gpu_benchmark.torch_available:
                    raise HTTPException(
                        status_code=400,
                        detail="PyTorch with CUDA not available"
                    )

                result = self.gpu_benchmark.benchmark_bert_inference(
                    device_id=device_id,
                    batch_size=batch_size,
                    seq_length=seq_length,
                    iterations=iterations
                )

                if 'error' in result:
                    raise HTTPException(status_code=500, detail=result.get('error'))

                return result
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/gpu/benchmark/info")
        async def get_gpu_benchmark_info(device_id: int = Query(0, description="GPU device ID")):
            """Get GPU information for benchmarking."""
            try:
                if not self.gpu_benchmark.is_available():
                    return {
                        "available": False,
                        "message": "No GPU or GPU libraries available"
                    }
                return self.gpu_benchmark.get_gpu_info(device_id)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/gpu/stress/mixed-precision")
        async def run_mixed_precision_stress(
            device_id: int = Query(0, description="GPU device ID"),
            size: int = Query(4096, description="Matrix size for operations"),
            iterations: int = Query(100, description="Number of iterations")
        ):
            """Run mixed precision stress test (FP32, FP16, BF16)."""
            try:
                if not self.gpu_stress_benchmark.is_available():
                    raise HTTPException(
                        status_code=400,
                        detail="GPU stress testing not available. Requires PyTorch with CUDA."
                    )

                result = self.gpu_stress_benchmark.benchmark_mixed_precision(
                    device_id=device_id,
                    size=size,
                    iterations=iterations
                )

                if 'error' in result:
                    raise HTTPException(status_code=500, detail=result.get('error'))

                return result
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/gpu/stress/memory-stress")
        async def run_memory_stress(
            device_id: int = Query(0, description="GPU device ID"),
            fill_percentage: float = Query(0.9, description="Percentage of GPU memory to fill (0.0-0.95)"),
            duration_seconds: int = Query(60, description="Test duration in seconds")
        ):
            """Run GPU memory stress test."""
            try:
                if not self.gpu_stress_benchmark.is_available():
                    raise HTTPException(
                        status_code=400,
                        detail="GPU stress testing not available. Requires PyTorch with CUDA."
                    )

                if fill_percentage < 0.0 or fill_percentage > 0.95:
                    raise HTTPException(
                        status_code=400,
                        detail="fill_percentage must be between 0.0 and 0.95"
                    )

                result = self.gpu_stress_benchmark.benchmark_memory_stress(
                    device_id=device_id,
                    fill_percentage=fill_percentage,
                    duration_seconds=duration_seconds
                )

                if 'error' in result:
                    raise HTTPException(status_code=500, detail=result.get('error'))

                return result
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/gpu/stress/sustained-load")
        async def run_sustained_load_stress(
            device_id: int = Query(0, description="GPU device ID"),
            duration_minutes: int = Query(10, description="Test duration in minutes"),
            workload_intensity: str = Query("high", description="Workload intensity: low, medium, high, extreme")
        ):
            """Run sustained GPU load stress test."""
            try:
                if not self.gpu_stress_benchmark.is_available():
                    raise HTTPException(
                        status_code=400,
                        detail="GPU stress testing not available. Requires PyTorch with CUDA."
                    )

                valid_intensities = ["low", "medium", "high", "extreme"]
                if workload_intensity not in valid_intensities:
                    raise HTTPException(
                        status_code=400,
                        detail=f"workload_intensity must be one of: {', '.join(valid_intensities)}"
                    )

                result = self.gpu_stress_benchmark.benchmark_sustained_load(
                    device_id=device_id,
                    duration_minutes=duration_minutes,
                    workload_intensity=workload_intensity
                )

                if 'error' in result:
                    raise HTTPException(status_code=500, detail=result.get('error'))

                return result
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/gpu/stress/multi-gpu")
        async def run_multi_gpu_stress(
            duration_seconds: int = Query(60, description="Test duration in seconds")
        ):
            """Run stress test on all available GPUs simultaneously."""
            try:
                if not self.gpu_stress_benchmark.is_available():
                    raise HTTPException(
                        status_code=400,
                        detail="GPU stress testing not available. Requires PyTorch with CUDA."
                    )

                result = self.gpu_stress_benchmark.benchmark_multi_gpu(
                    duration_seconds=duration_seconds
                )

                if 'error' in result:
                    raise HTTPException(status_code=500, detail=result.get('error'))

                return result
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/gpu/stress/suite")
        async def run_stress_benchmark_suite(
            device_id: int = Query(0, description="GPU device ID"),
            suite_type: str = Query("standard", description="Suite type: quick, standard, comprehensive"),
            export_results: bool = Query(False, description="Export results to JSON/CSV"),
            output_dir: str = Query("./benchmark_results", description="Output directory for exports")
        ):
            """Run complete GPU stress benchmark suite."""
            try:
                if not self.gpu_stress_benchmark.is_available():
                    raise HTTPException(
                        status_code=400,
                        detail="GPU stress testing not available. Requires PyTorch with CUDA."
                    )

                valid_suites = ["quick", "standard", "comprehensive"]
                if suite_type not in valid_suites:
                    raise HTTPException(
                        status_code=400,
                        detail=f"suite_type must be one of: {', '.join(valid_suites)}"
                    )

                result = self.gpu_stress_benchmark.run_benchmark_suite(
                    device_id=device_id,
                    suite_type=suite_type
                )

                if 'error' in result:
                    raise HTTPException(status_code=500, detail=result.get('error'))

                # Export results if requested
                if export_results and 'error' not in result:
                    export_paths = self.gpu_stress_benchmark.export_results(
                        results=result,
                        output_dir=output_dir,
                        formats=['json', 'csv']
                    )
                    result['exported_files'] = export_paths

                return result
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/gpu/stress/info")
        async def get_gpu_stress_info():
            """Get GPU stress testing availability and capabilities."""
            try:
                return {
                    "available": self.gpu_stress_benchmark.is_available(),
                    "torch_available": self.gpu_stress_benchmark.torch_available,
                    "cuda_available": self.gpu_stress_benchmark.cuda_available,
                    "gpu_count": self.gpu_stress_benchmark.gpu_count if self.gpu_stress_benchmark.is_available() else 0,
                    "suite_types": ["quick", "standard", "comprehensive"],
                    "workload_intensities": ["low", "medium", "high", "extreme"],
                    "test_types": [
                        "mixed-precision",
                        "memory-stress",
                        "sustained-load",
                        "multi-gpu",
                        "suite"
                    ]
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/history/{metric}")
        async def get_history(
            metric: str,
            hours: int = Query(24, description="Hours of history to retrieve"),
            limit: Optional[int] = Query(None, description="Maximum number of records")
        ):
            """Get historical data for a metric."""
            try:
                valid_metrics = ["cpu", "memory", "disk", "network", "gpu"]
                if metric not in valid_metrics:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid metric. Must be one of: {', '.join(valid_metrics)}"
                    )

                table_name = f"{metric}_history"
                history = self.db.get_history(table_name, hours=hours, limit=limit)

                return {
                    "metric": metric,
                    "hours": hours,
                    "count": len(history),
                    "data": history
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/history/{metric}/stats")
        async def get_history_stats(
            metric: str,
            hours: int = Query(1, description="Hours to analyze")
        ):
            """Get statistical summary of historical data."""
            try:
                valid_metrics = ["cpu", "memory", "disk", "gpu"]
                if metric not in valid_metrics:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid metric. Must be one of: {', '.join(valid_metrics)}"
                    )

                table_name = f"{metric}_history"
                stats = self.db.get_statistics(table_name, hours=hours)

                return {
                    "metric": metric,
                    "statistics": stats
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/alerts")
        async def get_alerts(
            active_only: bool = Query(True, description="Return only active alerts"),
            limit: Optional[int] = Query(None, description="Maximum number of alerts")
        ):
            """Get system alerts."""
            try:
                if active_only:
                    alerts = self.alert_manager.get_active_alerts()
                else:
                    alerts = self.alert_manager.get_alert_history(limit=limit)

                return {
                    "count": len(alerts),
                    "alerts": [alert.to_dict() for alert in alerts]
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/alerts/clear")
        async def clear_alerts():
            """Clear active alerts."""
            try:
                self.alert_manager.clear_alerts()
                return {"message": "Alerts cleared successfully"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/export")
        async def export_data(
            format: str = Query("json", description="Export format (json or csv)"),
            background_tasks: BackgroundTasks = None
        ):
            """Export current system snapshot."""
            try:
                snapshot = {
                    "timestamp": datetime.now().isoformat(),
                    "cpu": self.cpu_monitor.get_usage(interval=0.1),
                    "memory": self.memory_monitor.get_memory(),
                    "disk": self.disk_monitor.get_complete_stats(),
                    "network": self.network_monitor.get_io_counters(per_nic=True),
                    "gpu": self.gpu_monitor.get_all_gpus()
                }

                filepath = self.exporter.export_snapshot(snapshot, format=format)

                return {
                    "message": "Export successful",
                    "filepath": filepath,
                    "format": format
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/config")
        async def get_config():
            """Get current configuration."""
            return self.config.config

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "monitors": {
                    "cpu": True,
                    "memory": True,
                    "disk": True,
                    "network": True,
                    "gpu": self.gpu_monitor.is_available()
                }
            }

        @self.app.get("/metrics")
        async def prometheus_metrics():
            """
            Prometheus metrics endpoint.

            Returns system metrics in Prometheus text format for scraping.
            """
            try:
                metrics = self.prometheus_exporter.generate_metrics()
                return Response(
                    content=metrics,
                    media_type=self.prometheus_exporter.get_content_type()
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

    def run(self, host: Optional[str] = None, port: Optional[int] = None):
        """
        Run the API server.

        Args:
            host: Host address (defaults to config)
            port: Port number (defaults to config)
        """
        host = host or self.config.get("api.host", "0.0.0.0")
        port = port or self.config.get("api.port", 8000)

        uvicorn.run(self.app, host=host, port=port)


def create_app(config: Config = None) -> FastAPI:
    """
    Create FastAPI application instance.

    Args:
        config: Configuration instance

    Returns:
        FastAPI application
    """
    api = MonitoringAPI(config)
    return api.app
