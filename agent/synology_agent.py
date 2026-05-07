#!/usr/bin/env python3
import os, json, subprocess, urllib.request

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
    except:
        return 0.0

def get_memory():
    try:
        out = subprocess.check_output(["free", "-m"], text=True)
        parts = out.strip().split("\n")[1].split()
        return round(int(parts[2]) / int(parts[1]) * 100, 1)
    except:
        return 0.0

def get_disk():
    try:
        out = subprocess.check_output(["df", "/volume1"], text=True)
        parts = out.strip().split("\n")[1].split()
        return float(parts[4].replace("%", ""))
    except:
        return 0.0

def get_backup():
    try:
        r = subprocess.check_output(["synopkg", "status", "HyperBackup"], text=True, stderr=subprocess.DEVNULL)
        if "running" in r.lower():
            return "ok", "HyperBackup running"
        return "warning", "HyperBackup not running"
    except:
        return "unknown", "cannot get backup status"

def main():
    cfg = load_config()
    cpu, mem, disk = get_cpu(), get_memory(), get_disk()
    backup_status, backup_details = get_backup()
    payload = json.dumps({
        "cpu_usage": cpu, "memory_usage": mem, "disk_usage": disk,
        "backup_status": backup_status, "backup_details": backup_details
    }).encode()
    req = urllib.request.Request(
        cfg["server_url"].rstrip("/") + "/report",
        data=payload,
        headers={"Content-Type": "application/json", "X-Api-Key": cfg["api_key"]}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        print(f"[OK] {resp.status} CPU:{cpu}% MEM:{mem}% DISK:{disk}% Backup:{backup_status}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
