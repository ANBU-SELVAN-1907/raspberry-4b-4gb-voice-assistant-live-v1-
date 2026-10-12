import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def select_card(cards, requested=None):
    if requested:
        matches = [card for card in cards if card["id"].lower() == requested.lower() or card["index"] == requested]
    else:
        matches = [card for card in cards if re.search(r"plantronics|blackwire|poly", card["name"], re.I)]
    if len(matches) != 1:
        raise ValueError("Specify the headset's ALSA card ID with --card ID; automatic detection was ambiguous or found no headset")
    return matches[0]


def parse_cards(text):
    return [{"index": m[1], "id": m[2].strip(), "name": m[3]}
            for m in re.finditer(r"^\s*(\d+)\s+\[([^\]]+)\]\s*:\s*(.+)$", text, re.M)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--card", help="ALSA ID or current number (saved as stable ID)")
    args = parser.parse_args()
    text = Path("/proc/asound/cards").read_text(encoding="utf-8")
    cards = parse_cards(text)
    card = select_card(cards, args.card)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", card["id"]):
        raise ValueError("Unexpected ALSA card ID")
    config = f'''# Jarvis USB headset default. ALSA plug converts sample rates automatically.
pcm.!default {{
  type asym
  playback.pcm {{ type plug; slave.pcm "hw:CARD={card['id']},DEV=0"; }}
  capture.pcm {{ type plug; slave.pcm "hw:CARD={card['id']},DEV=0"; }}
}}
ctl.!default {{ type hw; card "{card['id']}"; }}
'''
    target = Path.home() / ".asoundrc"
    if target.exists():
        backup = target.with_name(".asoundrc.before-jarvis")
        if not backup.exists():
            backup.write_bytes(target.read_bytes())
    target.write_text(config)
    saved = ROOT / "config.json"
    current = json.loads(saved.read_text(encoding="utf-8") if saved.exists() else (ROOT / "config.example.json").read_text(encoding="utf-8"))
    current.update(input_device="default", output_device="default", input_rate=48000)
    saved.write_text(json.dumps(current, indent=2) + "\n")
    print(f"Selected {card['id']}: {card['name']}\nALSA default saved to {target}")


if __name__ == "__main__":
    main()
