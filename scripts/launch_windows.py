"""Offline laptop launcher with relative assets and clean child teardown."""
import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["JARVIS_PROFILE"] = "laptop"
from jarvis.config import load_config, resolve
from jarvis.app import run


def existing_app(url):
    try:
        with urllib.request.urlopen(url + "/api/status", timeout=1) as response:
            state = json.load(response)
        return state.get("type") == "state" and "heard" in state
    except (urllib.error.URLError, ValueError, TimeoutError):
        return False


async def launch(cfg):
    url = f"http://127.0.0.1:{cfg['port']}"
    app_task = asyncio.create_task(run(cfg))
    try:
        for _ in range(100):
            if app_task.done():
                await app_task
                return
            if await asyncio.to_thread(existing_app, url):
                webbrowser.open(url)
                break
            await asyncio.sleep(0.1)
        print("Jarvis is running. Say Hey Jarvis, pause, then ask. Say exit to close.")
        print("Keep this window open. The USB OLED is optional.")
        await app_task
    finally:
        if not app_task.done():
            app_task.cancel()
        try:
            await app_task
        except asyncio.CancelledError:
            pass


def main():
    os.chdir(ROOT)
    cfg = load_config()
    url = f"http://127.0.0.1:{cfg['port']}"
    if existing_app(url):
        webbrowser.open(url)
        print("Jarvis is already running. Opened its existing GUI.")
        return
    for asset in (cfg["llama_binary"], cfg["llm_model"], cfg["voice_model"], "models/manifest.json"):
        if not resolve(asset).is_file():
            raise SystemExit(f"Missing {asset}. Run setup.bat before starting.")
    from scripts.windows_audio import resolve_devices
    cfg = resolve_devices(cfg)
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        asyncio.run(launch(cfg))
    except KeyboardInterrupt:
        print("Jarvis closed.")


if __name__ == "__main__":
    main()
