"""Report Windows physical RAM and repair laptop settings without touching audio."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jarvis.metrics import memory_pressure, system_memory
from jarvis.config import load_config


def repair_config(path):
    path = Path(path)
    settings = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    # Laptop policy: retain free RAM as well as an absolute safety threshold.
    settings["system_ram_limit_bytes"] = 16000000000
    settings["minimum_available_memory_bytes"] = 1500000000
    if path.exists():
        backup = path.with_name(path.name + ".before-memory-repair")
        if not backup.exists():
            backup.write_bytes(path.read_bytes())
    path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repair", action="store_true")
    args = parser.parse_args()
    memory = system_memory()
    if not memory:
        raise SystemExit("Cannot read system RAM on this computer.")
    for name in ("total_bytes", "used_bytes", "available_bytes"):
        value = memory[name]
        print(f"{name}: {value / 1e9:.2f} GB ({value / 1073741824:.2f} GiB)")
    path = ROOT / "config.laptop.json"
    if args.repair:
        repair_config(path)
        print("Updated config.laptop.json. Other settings preserved; first original saved beside it.")
    cfg = load_config(path, profile="laptop")
    print(f"System-use limit: {cfg['system_ram_limit_bytes'] / 1e9:.2f} GB")
    print(f"Available-RAM reserve: {cfg['minimum_available_memory_bytes'] / 1e9:.2f} GB")
    reason = memory_pressure(memory, cfg)
    print(reason or "RAM guard allows startup. Restart Jarvis to load changed settings.")


if __name__ == "__main__":
    main()
