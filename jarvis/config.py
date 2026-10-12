import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_config(path=None):
    defaults = json.loads((ROOT / "config.example.json").read_text(encoding="utf-8"))
    path = Path(path or ROOT / "config.json")
    if path.exists():
        custom = json.loads(path.read_text(encoding="utf-8"))
        unknown = custom.keys() - defaults.keys()
        if unknown:
            raise ValueError(f"Unknown settings: {sorted(unknown)}")
        defaults.update(custom)
    if defaults["host"] not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Use a loopback address and an SSH tunnel for the GUI")
    if not 1 <= defaults["threads"] <= 3:
        raise ValueError("threads must be between 1 and 3 on Pi 4")
    if not 512 <= defaults["context"] <= 2048:
        raise ValueError("context must be 512..2048 for the memory budget")
    if not 16 <= defaults["max_tokens"] <= 128:
        raise ValueError("max_tokens must be 16..128")
    if defaults["idle_unload_seconds"] < 0:
        raise ValueError("idle_unload_seconds cannot be negative")
    if not 0 < defaults["system_ram_limit_bytes"] <= 3200000000:
        raise ValueError("system RAM limit must be <= 3.2 billion bytes")
    if defaults["port"] == defaults["llama_port"]:
        raise ValueError("GUI and llama.cpp ports must differ")
    if not 0.1 <= defaults["kws_threshold"] <= 0.8 or not 0.5 <= defaults["kws_score"] <= 3:
        raise ValueError("kws_threshold must be 0.1..0.8 and kws_score 0.5..3")
    return defaults


def resolve(path):
    p = Path(path)
    return p if p.is_absolute() else ROOT / p
