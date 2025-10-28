"""Data export functionality."""
import json
import csv
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd


class DataExporter:
    """Export monitoring data to various formats."""

    def __init__(self, export_dir: str = "./exports"):
        """
        Initialize the data exporter.

        Args:
            export_dir: Directory to store exported files
        """
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_to_json(self, data: Dict, filename: Optional[str] = None) -> str:
        """
        Export data to JSON format.

        Args:
            data: Data to export
            filename: Optional filename (auto-generated if not provided)

        Returns:
            Path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"monitor_export_{timestamp}.json"

        filepath = self.export_dir / filename

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        return str(filepath)

    def export_to_csv(self, data: List[Dict], filename: Optional[str] = None) -> str:
        """
        Export data to CSV format.

        Args:
            data: List of dictionaries to export
            filename: Optional filename (auto-generated if not provided)

        Returns:
            Path to exported file
        """
        if not data:
            raise ValueError("No data to export")

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"monitor_export_{timestamp}.csv"

        filepath = self.export_dir / filename

        # Use pandas for easier CSV export
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)

        return str(filepath)

    def export_history_to_csv(self, history_data: Dict, filename_prefix: str = "history") -> Dict[str, str]:
        """
        Export historical data to separate CSV files for each metric.

        Args:
            history_data: Dictionary with keys like 'cpu', 'memory', etc.
            filename_prefix: Prefix for generated filenames

        Returns:
            Dictionary mapping metric names to file paths
        """
        exported_files = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for metric_name, metric_data in history_data.items():
            if isinstance(metric_data, list) and metric_data:
                filename = f"{filename_prefix}_{metric_name}_{timestamp}.csv"
                filepath = self.export_to_csv(metric_data, filename)
                exported_files[metric_name] = filepath

        return exported_files

    def export_snapshot(self, snapshot_data: Dict, format: str = "json") -> str:
        """
        Export a snapshot of current system state.

        Args:
            snapshot_data: Current monitoring data
            format: Export format ('json' or 'csv')

        Returns:
            Path to exported file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == "json":
            return self.export_to_json(snapshot_data, f"snapshot_{timestamp}.json")
        elif format == "csv":
            # Flatten the snapshot data for CSV export
            flattened = self._flatten_snapshot(snapshot_data)
            return self.export_to_csv([flattened], f"snapshot_{timestamp}.csv")
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _flatten_snapshot(self, data: Dict, parent_key: str = "", sep: str = "_") -> Dict:
        """
        Flatten nested dictionary for CSV export.

        Args:
            data: Nested dictionary
            parent_key: Parent key for recursion
            sep: Separator for nested keys

        Returns:
            Flattened dictionary
        """
        items = []
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k

            if isinstance(v, dict):
                items.extend(self._flatten_snapshot(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Convert lists to string representation
                items.append((new_key, str(v)))
            else:
                items.append((new_key, v))

        return dict(items)
