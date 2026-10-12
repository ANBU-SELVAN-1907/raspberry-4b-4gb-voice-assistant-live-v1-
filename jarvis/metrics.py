from pathlib import Path
import os


def system_memory():
    if os.name == "nt":
        import ctypes
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                (name, ctypes.c_ulonglong) for name in
                ("total", "available", "page_total", "page_available", "virtual_total", "virtual_available", "extended")]
        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return {}
        return {"total_bytes": status.total, "available_bytes": status.available, "used_bytes": status.total - status.available}
    path = Path("/proc/meminfo")
    if not path.exists():
        return {}
    values = {line.split(":")[0]: int(line.split()[1]) * 1024 for line in path.read_text(encoding="utf-8").splitlines()}
    used = values["MemTotal"] - values["MemAvailable"]
    return {"total_bytes": values["MemTotal"], "available_bytes": values["MemAvailable"], "used_bytes": used}


def temperature():
    try:
        return int(Path("/sys/class/thermal/thermal_zone0/temp").read_text(encoding="utf-8")) / 1000
    except (OSError, ValueError):
        return None
