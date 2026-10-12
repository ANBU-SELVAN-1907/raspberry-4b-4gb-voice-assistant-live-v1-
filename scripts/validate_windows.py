"""Explicit short hardware smoke test; no microphone recordings are saved."""
import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jarvis.app import Assistant
from jarvis.config import load_config
from jarvis.store import Store
from scripts.windows_audio import resolve_devices


async def main():
    import aiohttp
    cfg = resolve_devices(load_config(profile="laptop"))
    cfg["oled_enabled"] = False
    with tempfile.TemporaryDirectory(dir=ROOT / "run") as folder:
        async with aiohttp.ClientSession(trust_env=False) as http:
            assistant = Assistant(cfg, http, Store(Path(folder) / "test.sqlite"))
            try:
                await assistant.start()
                async with asyncio.timeout(30):
                    while not assistant.audio_ready:
                        if assistant.fatal:
                            raise RuntimeError(assistant.fatal)
                        await asyncio.sleep(0.1)
                await assistant.submit("What is the capital of France? Answer in one sentence.")
                await asyncio.wait_for(assistant.turn, 90)
                if assistant.state["state"] == "error" or "paris" not in assistant.state["text"].lower():
                    raise AssertionError(assistant.state)
                report = {"speech_worker_ready": assistant.audio_ready, "reply": assistant.state["text"],
                          "metrics": assistant.state["metrics"], "note": "Actual local audio playback path tested. Natural microphone speech and OLED hardware remain separate checks."}
                await assistant.submit("What is two plus two? Answer briefly.")
                await asyncio.wait_for(assistant.turn, 90)
                if assistant.state["state"] == "error":
                    raise AssertionError(assistant.state)
                report["warm_reply"] = assistant.state["text"]
                report["warm_metrics"] = assistant.state["metrics"]
                print(json.dumps(report, indent=2))
                (ROOT / "run/windows-hardware-smoke.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            finally:
                await assistant.close()
            if any(p and p.returncode is None for p in (assistant.engine.process, assistant.speaker.process, assistant.speech)):
                raise AssertionError("A worker survived clean shutdown")


if __name__ == "__main__":
    print("Opening the current microphone and playing one short answer. No mic audio is saved.")
    asyncio.run(main())
