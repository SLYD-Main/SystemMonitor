#!/usr/bin/env python3
"""Test the SpeedTestMonitor module."""

from src.monitors.speedtest import SpeedTestMonitor
import json

print("Testing SpeedTestMonitor module...")
print("=" * 60)

try:
    monitor = SpeedTestMonitor()

    print("\nRunning speedtest via monitor...")
    result = monitor.run_speedtest()

    print("\nResult:")
    print(json.dumps(result, indent=2, default=str))

    if 'error' in result:
        print(f"\n❌ ERROR: {result['error']}")
        if 'details' in result:
            print(f"Details: {result['details']}")
    else:
        print("\n✓ SUCCESS! Monitor works correctly.")
        print(f"\nDownload: {result['download']['formatted']}")
        print(f"Upload: {result['upload']['formatted']}")
        print(f"Ping: {result['ping']['formatted']}")

except Exception as e:
    print(f"\n❌ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()
