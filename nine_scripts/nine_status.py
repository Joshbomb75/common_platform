# DEPLOY TO: ~/nine_scripts/nine_status.py
#!/usr/bin/env python3
"""
Nine's robot health check.
Prints: STATUS_OK {"camera_devices": [...], "teensy_ok": bool, ...}
"""

import json
import glob
import subprocess
import sys
import os

def get_camera_devices():
    return sorted(glob.glob("/dev/video*"))

def device_exists(pattern):
    return len(glob.glob(pattern)) > 0

def get_disk_free_gb():
    try:
        st = os.statvfs("/")
        free_bytes = st.f_bavail * st.f_frsize
        return round(free_bytes / (1024**3), 2)
    except Exception:
        return None

def get_uptime():
    try:
        with open("/proc/uptime") as f:
            seconds = float(f.read().split()[0])
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
    except Exception:
        return "unknown"

def get_ros_nodes():
    try:
        result = subprocess.run(
            ["bash", "-c", "ros2 node list 2>/dev/null"],
            capture_output=True, text=True, timeout=5
        )
        nodes = [n.strip() for n in result.stdout.strip().splitlines() if n.strip()]
        return nodes
    except Exception:
        return []

def main():
    status = {
        "camera_devices": get_camera_devices(),
        "teensy_ok": device_exists("/dev/serial/by-id/usb-Teensyduino_Dual_Serial_*"),
        "lidar_ok": device_exists("/dev/serial/by-id/usb-Silicon_Labs_CP2102*"),
        "disk_free_gb": get_disk_free_gb(),
        "uptime": get_uptime(),
        "ros_nodes": get_ros_nodes(),
    }
    print(f"STATUS_OK {json.dumps(status)}")
    sys.exit(0)

if __name__ == "__main__":
    main()

# Dependencies: standard library only (json, glob, subprocess, os)
# ros2 CLI must be in PATH (sourced via ~/.profile on login shell)
