#!/usr/bin/env python3
"""Test script to debug speedtest functionality."""

import speedtest

print("Testing speedtest library...")
print("=" * 60)

try:
    st = speedtest.Speedtest()

    print("\n1. Getting best server...")
    best = st.get_best_server()
    print(f"   Server: {best['sponsor']} - {best['name']}, {best['country']}")
    print(f"   Distance: {best['d']:.2f} km")
    print(f"   Latency: {best['latency']:.2f} ms")

    print("\n2. Running download test...")
    download = st.download()
    print(f"   Download: {download / 1_000_000:.2f} Mbps")

    print("\n3. Running upload test...")
    upload = st.upload()
    print(f"   Upload: {upload / 1_000_000:.2f} Mbps")

    print("\n" + "=" * 60)
    print("SUCCESS! Speedtest library works correctly.")
    print("=" * 60)

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()