"""GPU monitoring module."""
from typing import Dict, List, Optional
from datetime import datetime


class GPUMonitor:
    """Monitor GPU usage and statistics (supports NVIDIA primarily)."""

    def __init__(self):
        self.nvidia_available = False
        self.gputil_available = False
        self.gpus = []

        # Try to initialize NVIDIA monitoring
        try:
            import pynvml
            pynvml.nvmlInit()
            self.nvidia_available = True
            self.pynvml = pynvml
            self.device_count = pynvml.nvmlDeviceGetCount()
        except (ImportError, Exception):
            pass

        # Fallback to GPUtil
        if not self.nvidia_available:
            try:
                import GPUtil
                self.gputil_available = True
                self.GPUtil = GPUtil
            except ImportError:
                pass

    def is_available(self) -> bool:
        """Check if GPU monitoring is available."""
        return self.nvidia_available or self.gputil_available

    def get_gpu_count(self) -> int:
        """Get number of GPUs available."""
        if self.nvidia_available:
            return self.device_count
        elif self.gputil_available:
            return len(self.GPUtil.getGPUs())
        return 0

    def get_gpu_info_nvidia(self, device_index: int = 0) -> Dict:
        """
        Get GPU information using pynvml (NVIDIA).

        Args:
            device_index: GPU device index

        Returns:
            Dictionary containing GPU statistics
        """
        try:
            handle = self.pynvml.nvmlDeviceGetHandleByIndex(device_index)

            # Get basic info
            name = self.pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode('utf-8')

            # Get utilization
            utilization = self.pynvml.nvmlDeviceGetUtilizationRates(handle)

            # Get memory info
            memory = self.pynvml.nvmlDeviceGetMemoryInfo(handle)

            # Get temperature
            try:
                temperature = self.pynvml.nvmlDeviceGetTemperature(
                    handle, self.pynvml.NVML_TEMPERATURE_GPU
                )
            except:
                temperature = None

            # Get power usage
            try:
                power_usage = self.pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Convert to watts
                power_limit = self.pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000.0
            except:
                power_usage = None
                power_limit = None

            # Get fan speed
            try:
                fan_speed = self.pynvml.nvmlDeviceGetFanSpeed(handle)
            except:
                fan_speed = None

            # Get clock speeds
            try:
                graphics_clock = self.pynvml.nvmlDeviceGetClockInfo(
                    handle, self.pynvml.NVML_CLOCK_GRAPHICS
                )
                memory_clock = self.pynvml.nvmlDeviceGetClockInfo(
                    handle, self.pynvml.NVML_CLOCK_MEM
                )
            except:
                graphics_clock = None
                memory_clock = None

            return {
                "index": device_index,
                "name": name,
                "utilization": {
                    "gpu": utilization.gpu,
                    "memory": utilization.memory
                },
                "memory": {
                    "total": memory.total,
                    "used": memory.used,
                    "free": memory.free,
                    "percent": (memory.used / memory.total * 100) if memory.total > 0 else 0
                },
                "temperature": temperature,
                "power": {
                    "usage": power_usage,
                    "limit": power_limit,
                    "percent": (power_usage / power_limit * 100) if power_usage and power_limit else None
                },
                "fan_speed": fan_speed,
                "clocks": {
                    "graphics": graphics_clock,
                    "memory": memory_clock
                }
            }
        except Exception as e:
            return {
                "index": device_index,
                "error": str(e)
            }

    def get_gpu_info_gputil(self, device_index: int = 0) -> Dict:
        """
        Get GPU information using GPUtil (NVIDIA fallback).

        Args:
            device_index: GPU device index

        Returns:
            Dictionary containing GPU statistics
        """
        try:
            gpus = self.GPUtil.getGPUs()
            if device_index >= len(gpus):
                return {"error": f"GPU index {device_index} not found"}

            gpu = gpus[device_index]

            return {
                "index": device_index,
                "name": gpu.name,
                "utilization": {
                    "gpu": gpu.load * 100,
                    "memory": gpu.memoryUtil * 100
                },
                "memory": {
                    "total": gpu.memoryTotal * 1024 * 1024,  # Convert to bytes
                    "used": gpu.memoryUsed * 1024 * 1024,
                    "free": gpu.memoryFree * 1024 * 1024,
                    "percent": gpu.memoryUtil * 100
                },
                "temperature": gpu.temperature,
                "uuid": gpu.uuid
            }
        except Exception as e:
            return {
                "index": device_index,
                "error": str(e)
            }

    def get_all_gpus(self) -> Dict:
        """
        Get information for all available GPUs.

        Returns:
            Dictionary containing all GPU statistics
        """
        if not self.is_available():
            return {
                "timestamp": datetime.now().isoformat(),
                "available": False,
                "message": "No GPU monitoring libraries available. Install pynvml or GPUtil."
            }

        gpu_count = self.get_gpu_count()
        gpus = []

        for i in range(gpu_count):
            if self.nvidia_available:
                gpu_info = self.get_gpu_info_nvidia(i)
            else:
                gpu_info = self.get_gpu_info_gputil(i)
            gpus.append(gpu_info)

        return {
            "timestamp": datetime.now().isoformat(),
            "available": True,
            "count": gpu_count,
            "gpus": gpus,
            "driver": self._get_driver_version()
        }

    def _get_driver_version(self) -> Optional[str]:
        """Get GPU driver version."""
        if self.nvidia_available:
            try:
                version = self.pynvml.nvmlSystemGetDriverVersion()
                if isinstance(version, bytes):
                    version = version.decode('utf-8')
                return version
            except:
                return None
        return None

    def __del__(self):
        """Cleanup NVML resources."""
        if self.nvidia_available:
            try:
                self.pynvml.nvmlShutdown()
            except:
                pass