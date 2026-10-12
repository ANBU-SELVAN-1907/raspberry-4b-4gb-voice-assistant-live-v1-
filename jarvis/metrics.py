from pathlib import Path
import os


def memory_pressure(memory, cfg, *, recovering=False):
    """Return an actionable reason, retaining the Pi's absolute system budget."""
    if not memory:
        return None
    margin = 256000000 if recovering else 0
    limit = cfg["system_ram_limit_bytes"]
    reserve = cfg.get("minimum_available_memory_bytes", 0)
    used = memory["used_bytes"]
    available = memory.get("available_bytes")
    over_budget = used >= limit - margin
    low_headroom = reserve > 0 and available is not None and available < reserve + margin
    if not over_budget and not low_headroom:
        return None
    readings = f"{used / 1e9:.2f} GB used"
    if available is not None:
        readings += f", {available / 1e9:.2f} GB available"
    return (f"Memory pressure ({readings}; use limit {limit / 1e9:.2f} GB, "
            f"free reserve {reserve / 1e9:.2f} GB). Close other apps. "
            "On Windows, run repair_memory.bat if the settings came from another computer.")


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
