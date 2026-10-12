from pathlib import Path


def system_memory():
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
