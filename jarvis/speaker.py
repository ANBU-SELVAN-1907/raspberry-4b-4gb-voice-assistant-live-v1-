import asyncio
import base64
import json
import math
import sys

from .config import ROOT
from .engine import terminate


class Speaker:
    def __init__(self, config, publish):
        self.config, self.publish = config, publish
        self.process = None
        self.output = None
        self.log = None
        self.rate = None

    async def start(self):
        if self.process and self.process.returncode is None:
            return
        self.log = (ROOT / "run/tts.log").open("wb")
        self.process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "jarvis.tts_worker", cwd=ROOT,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=self.log)
        line = await asyncio.wait_for(self.process.stdout.readline(), 30)
        if not line or not json.loads(line).get("ready"):
            raise RuntimeError("Piper failed to start. Inspect run/tts.log")

    async def say(self, text, first_audio=None):
        await self.start()
        self.process.stdin.write((json.dumps({"text": text}) + "\n").encode())
        await self.process.stdin.drain()
        played = False
        while True:
            line = await asyncio.wait_for(self.process.stdout.readline(), 30)
            if not line:
                raise RuntimeError("Piper exited unexpectedly")
            event = json.loads(line)
            if event.get("done"):
                return
            pcm = base64.b64decode(event["pcm"], validate=True)
            import sounddevice as sd
            import numpy as np
            if self.output is None or self.rate != event["rate"]:
                if self.output:
                    self.output.close()
                self.rate = event["rate"]
                self.output = sd.RawOutputStream(samplerate=self.rate, channels=1, dtype="int16",
                                                 device=self.config["output_device"], latency="low")
                self.output.start()
            samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768
            rms = math.sqrt(float(np.mean(samples * samples))) if samples.size else 0
            self.publish({"type": "mouth", "level": min(1, rms * 8)})
            if not played and first_audio:
                first_audio()
            played = True
            # Only ~46-64ms per write; cancellation aborts PortAudio immediately.
            await asyncio.to_thread(self.output.write, pcm)

    async def stop(self):
        if self.output:
            self.output.abort()
            self.output.close()
            self.output = None
        await terminate(self.process)
        self.process = None
        if self.log:
            self.log.close()
            self.log = None
        self.publish({"type": "mouth", "level": 0})

    async def finish(self):
        if self.output:
            await asyncio.to_thread(self.output.stop)
