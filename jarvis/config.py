import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_config(path=None, profile=None):
    profile = profile or os.environ.get("JARVIS_PROFILE") or ("laptop" if os.name == "nt" else "pi")
    if profile not in {"pi", "laptop"}:
        raise ValueError("JARVIS_PROFILE must be pi or laptop")
    name = "config.laptop.example.json" if profile == "laptop" else "config.example.json"
    defaults = json.loads((ROOT / name).read_text(encoding="utf-8"))
    defaults.setdefault("oled_enabled", False)
    defaults.setdefault("oled_port", "auto")
    defaults.setdefault("oled_baud", 115200)
    defaults.setdefault("retain_voice", False)
    path = Path(path or ROOT / ("config.laptop.json" if profile == "laptop" else "config.json"))
    if path.exists():
        custom = json.loads(path.read_text(encoding="utf-8-sig"))
        unknown = custom.keys() - defaults.keys()
        if unknown:
            raise ValueError(f"Unknown settings: {sorted(unknown)}")
        defaults.update(custom)
    if defaults["host"] not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Use a loopback address and an SSH tunnel for the GUI")
    max_threads, max_context, max_ram = (12, 8192, 16000000000) if profile == "laptop" else (3, 2048, 3200000000)
    if not 1 <= defaults["threads"] <= max_threads:
        raise ValueError(f"threads must be 1..{max_threads} for {profile}")
    if not 512 <= defaults["context"] <= max_context:
        raise ValueError(f"context must be 512..{max_context} for {profile}")
    if not 16 <= defaults["max_tokens"] <= 256:
        raise ValueError("max_tokens must be 16..256")
    if defaults["idle_unload_seconds"] < 0:
        raise ValueError("idle_unload_seconds cannot be negative")
    if not 0 < defaults["system_ram_limit_bytes"] <= max_ram:
        raise ValueError(f"system RAM limit must be <= {max_ram} bytes for {profile}")
    if defaults["port"] == defaults["llama_port"]:
        raise ValueError("GUI and llama.cpp ports must differ")
    if not 0.1 <= defaults["kws_threshold"] <= 0.8 or not 0.5 <= defaults["kws_score"] <= 3:
        raise ValueError("kws_threshold must be 0.1..0.8 and kws_score 0.5..3")
    return defaults


def resolve(path):
    p = Path(path)
    return p if p.is_absolute() else ROOT / p
