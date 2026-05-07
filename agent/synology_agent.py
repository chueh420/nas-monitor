#!/usr/bin/env python3
import os
import json
import subprocess
import requests

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def get_cpu():
    try:
        with open("/proc/loadavg") as f:
            load = float(f.read().split()[0])
        cpu_count = os.cpu_count() or 1
        return min(round(load / cpu_count * 100, 1), 100.0)
    except Exception:
        return 0.0

def get_memory():
    try:
        out = subprocess.check_output(["free", "-m"], text=True)
        lines = out.strip().split("\n")
        parts = lines[1].split()
        total, used = int(parts[1]), int(parts[2])
        return round(used / total * 100, 1)
    except Exception:
        return 0.0

def get_disk():
    try:
        out = subprocess.check_output(["df", "-h", "/volume1"], text=True)
        lines = out.strip().split("\n")
        parts = lines[1].split()
        pct = int(parts[4].replace("%", ""))
        return float(pct)
    except Exception:
        return 0.0

def get_backup_status():
    try:
        result = subprocess.check_output(
            ["synopkg", "status", "HyperBackup"], text=True, stderr=subprocess.DEVNULL
        )
        if "running" in result.lower():
            return "ok", "HyperBackup 運行中"
        return "warning", "HyperBackup 未運行"
    except Exception:
        return "unknown", "無法取得備份狀態"

def main():
    config = load_config()
    server_url = config["server_url"].rstrip("/")
    api_key = config["api_key"]

    cpu = get_cpu()
    memory = get_memory()
    disk = get_disk()
    backup_status, backup_details = get_backup_status()

    payload = {
        "cpu_usage": cpu,
        "memory_usage": memory,
        "disk_usage": disk,
        "backup_status": backup_status,
        "backup_details": backup_details,
    }

    try:
        resp = requests.post(
            f"{server_url}/report",
            json=payload,
            headers={"X-Api-Key": api_key},
            timeout=15,
        )
        print(f"[OK] {resp.status_code} - CPU:{cpu}% MEM:{memory}% DISK:{disk}% Backup:{backup_status}")
    except Exception as e:
        print(f"[ERROR] 無法連線到伺服器: {e}")

if __name__ == "__main__":
    main()
