"""
System scanning utilities
"""

import datetime
import socket
import subprocess
import re
from typing import Dict, Any


def check_internet_connection(timeout=3):
    """Check internet connection with timeout (non-blocking)"""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except OSError:
        return False
    finally:
        socket.setdefaulttimeout(None)


def system_scanner(interval: float = None) -> Dict[str, Any]:
    snapshot = {
        "timestamp": datetime.datetime.now().isoformat(),
        "error": None,
        "system": {},
        "cpu": {},
        "memory": {},
        "storage": [],
        "processes": [],
        "power_plan": {}
    }
    
    try:
        import psutil
        import platform
        
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.datetime.now() - boot_time
        
        snapshot["system"] = {
            "os": f"{platform.system()} {platform.release()}",
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S"),
            "uptime_days": round(uptime.total_seconds() / 86400, 1)
        }
        
        cpu_freq = psutil.cpu_freq()
        snapshot["cpu"] = {
            "name": platform.processor(),
            "cores_physical": psutil.cpu_count(logical=False) or 0,
            "cores_logical": psutil.cpu_count(logical=True) or 0,
            "usage_percent": round(psutil.cpu_percent(interval=interval), 1),
            "frequency_mhz": round(cpu_freq.current, 0) if cpu_freq else 0,
            "max_frequency_mhz": round(cpu_freq.max, 0) if cpu_freq else 0
        }
        
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        snapshot["memory"] = {
            "total_gb": round(mem.total / (1024**3), 1),
            "available_gb": round(mem.available / (1024**3), 1),
            "used_gb": round(mem.used / (1024**3), 1),
            "usage_percent": mem.percent,
            "swap_total_gb": round(swap.total / (1024**3), 1) if swap.total else 0,
            "swap_used_gb": round(swap.used / (1024**3), 1) if swap.used else 0,
            "swap_percent": swap.percent if swap.total else 0
        }
        
        for part in psutil.disk_partitions():
            if 'cdrom' in part.opts or part.fstype == '':
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                snapshot["storage"].append({
                    "drive": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total": round(usage.total / (1024**3), 1),
                    "used": round(usage.used / (1024**3), 1),
                    "free": round(usage.free / (1024**3), 1),
                    "percent": usage.percent
                })
            except:
                continue
        
        processes = []
        for proc in sorted(psutil.process_iter(['name', 'memory_percent']), 
                          key=lambda x: x.info.get('memory_percent', 0), reverse=True)[:10]:
            try:
                processes.append({
                    "name": proc.info.get('name', 'Unknown'),
                    "mem": round(proc.info.get('memory_percent', 0), 1)
                })
            except:
                pass
        snapshot["processes"] = processes
        
        try:
            disk_io = psutil.disk_io_counters()
            snapshot["storage_io"] = {
                "read_bytes": disk_io.read_bytes if disk_io else 0,
                "write_bytes": disk_io.write_bytes if disk_io else 0,
                "read_count": disk_io.read_count if disk_io else 0,
                "write_count": disk_io.write_count if disk_io else 0
            }
        except:
            snapshot["storage_io"] = {}

        try:
            net_io = psutil.net_io_counters()
            snapshot["network_io"] = {
                "bytes_sent": net_io.bytes_sent if net_io else 0,
                "bytes_recv": net_io.bytes_recv if net_io else 0,
                "packets_sent": net_io.packets_sent if net_io else 0,
                "packets_recv": net_io.packets_recv if net_io else 0
            }
        except:
            snapshot["network_io"] = {}
            
    except Exception as e:
        snapshot["error"] = str(e)
    
    return snapshot
