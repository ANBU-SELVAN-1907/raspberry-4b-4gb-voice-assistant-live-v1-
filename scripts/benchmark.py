#!/usr/bin/env python3
"""Measured Pi evidence; never substitute desktop timings for Pi timings."""
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jarvis.config import load_config
from jarvis.engine import Engine
from jarvis.metrics import system_memory, temperature


async def benchmark():
    import aiohttp
    cfg = load_config()
    report = {"hardware": "Run this report on the actual Pi 4", "model": cfg["llm_model"], "threads": cfg["threads"], "context": cfg["context"], "temperature_c_start": temperature()}
    async with aiohttp.ClientSession(trust_env=False) as http:
        engine = Engine(cfg, http)
        maximum_used = 0
        async def sample():
            nonlocal maximum_used
            while True:
                memory = system_memory()
                if memory:
                    maximum_used = max(maximum_used, memory["used_bytes"])
                    if memory["used_bytes"] > cfg["system_ram_limit_bytes"]:
                        await engine.stop()
                        raise RuntimeError("RAM ceiling exceeded during benchmark")
                await asyncio.sleep(0.1)
        try:
            async with asyncio.TaskGroup() as group:
                monitor = group.create_task(sample())
                start = time.perf_counter()
                await engine.ensure()
                report["cold_load_seconds"] = round(time.perf_counter() - start, 3)
                for phase in ("first", "warm"):
                    start = time.perf_counter()
                    first = None
                    parts = []
                    async for token in engine.tokens("Explain why the sky is blue in one short sentence.", [], [], []):
                        first = first or time.perf_counter()
                        parts.append(token)
                    report[f"{phase}_first_token_seconds"] = round((first or time.perf_counter()) - start, 3)
                    report[f"{phase}_total_seconds"] = round(time.perf_counter() - start, 3)
                    report[f"{phase}_reply"] = "".join(parts)
                report["llm_only_peak_system_used_bytes"] = maximum_used
                monitor.cancel()
        finally:
            await engine.stop()
    report["temperature_c_end"] = temperature()
    report["note"] = "This benchmark covers LLM only. GUI first-audio timing covers full turns; use acceptance.sh for full service memory."
    (ROOT / "run").mkdir(exist_ok=True)
    output = ROOT / "run/benchmark.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"Saved {output}")


if __name__ == "__main__":
    asyncio.run(benchmark())
