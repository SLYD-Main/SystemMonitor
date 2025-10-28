"""Configuration management."""
import yaml
from pathlib import Path
from typing import Dict, Optional


class Config:
    """Application configuration manager."""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load configuration from file."""
        if not self.config_path.exists():
            return self._default_config()

        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config if config else self._default_config()
        except Exception as e:
            print(f"Error loading config: {e}. Using defaults.")
            return self._default_config()

    @staticmethod
    def _default_config() -> Dict:
        """Get default configuration."""
        return {
            "thresholds": {
                "cpu": {"warning": 70, "critical": 90},
                "memory": {"warning": 75, "critical": 90},
                "disk": {"warning": 80, "critical": 95},
                "gpu": {"warning": 80, "critical": 95},
                "network": {"warning": 100, "critical": 500}
            },
            "history": {
                "enabled": True,
                "retention_hours": 24,
                "interval_seconds": 5
            },
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "enable_cors": True
            },
            "cli": {
                "refresh_rate": 1,
                "show_graphs": True
            },
            "export": {
                "directory": "./exports",
                "formats": ["json", "csv"]
            }
        }

    def get(self, key: str, default: Optional[any] = None) -> any:
        """
        Get configuration value by key (supports dot notation).

        Args:
            key: Configuration key (e.g., 'api.host')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_thresholds(self) -> Dict:
        """Get alert thresholds configuration."""
        return self.config.get("thresholds", {})

    def get_history_config(self) -> Dict:
        """Get history configuration."""
        return self.config.get("history", {})

    def get_api_config(self) -> Dict:
        """Get API configuration."""
        return self.config.get("api", {})

    def get_cli_config(self) -> Dict:
        """Get CLI configuration."""
        return self.config.get("cli", {})

    def get_export_config(self) -> Dict:
        """Get export configuration."""
        return self.config.get("export", {})

    def save_config(self):
        """Save current configuration to file."""
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)

    def update(self, key: str, value: any):
        """
        Update configuration value.

        Args:
            key: Configuration key (supports dot notation)
            value: New value
        """
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value
