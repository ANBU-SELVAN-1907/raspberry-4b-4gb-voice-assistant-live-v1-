import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jarvis.config import load_config


def device_id(selection, kind, devices, apis):
    if selection is None:
        return None
    if isinstance(selection, int):
        return selection
    matches = [i for i, device in enumerate(devices)
               if device[f"max_{kind}_channels"] > 0 and
               selection.casefold() == (device["name"] + " | " + apis[device["hostapi"]]["name"]).casefold()]
    if len(matches) != 1:
        raise ValueError(f"Saved {kind} device unavailable: {selection}. Run configure_audio.bat on this laptop.")
    return matches[0]


def resolve_devices(cfg):
    import sounddevice as sd
    devices, apis = sd.query_devices(), sd.query_hostapis()
    result = dict(cfg)
    for kind in ("input", "output"):
        result[f"{kind}_device"] = device_id(cfg[f"{kind}_device"], kind, devices, apis)
    return result


def main():
    import sounddevice as sd
    os.environ["JARVIS_PROFILE"] = "laptop"
    cfg = load_config()
    devices, apis = sd.query_devices(), sd.query_hostapis()
    for kind in ("input", "output"):
        print(f"\n{kind.upper()} devices (prefer the headset's Windows WASAPI entry):")
        valid = []
        for index, device in enumerate(devices):
            if device[f"max_{kind}_channels"]:
                valid.append(index)
                print(f"{index}: {device['name']} | {apis[device['hostapi']]['name']}")
        answer = input(f"{kind} number, or Enter for Windows default: ").strip()
        if not answer:
            cfg[f"{kind}_device"] = None
        elif answer.isdigit() and int(answer) in valid:
            device = devices[int(answer)]
            cfg[f"{kind}_device"] = device["name"] + " | " + apis[device["hostapi"]]["name"]
        else:
            raise ValueError("Choose one of the listed device numbers")
    resolved = resolve_devices(cfg)
    sd.check_input_settings(device=resolved["input_device"], channels=1, dtype="float32", samplerate=cfg["input_rate"])
    rate = sd.query_devices(resolved["output_device"], "output")["default_samplerate"]
    sd.check_output_settings(device=resolved["output_device"], channels=1, dtype="int16", samplerate=rate)
    (ROOT / "config.laptop.json").write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print("Saved stable device names. Restart Jarvis. Rerun this on your friend's laptop if its devices differ.")


if __name__ == "__main__":
    main()
