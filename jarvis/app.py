import argparse
import asyncio
import contextlib
import json
import logging
import os
import signal
import sys
import time

import aiohttp
from aiohttp import web

from .config import ROOT, load_config
from .engine import Engine, terminate
from .metrics import system_memory, temperature
from .skills import local_reply, timer_seconds
from .speaker import Speaker
from .store import Store
from .text import SpeechChunks, control, expression

LOG = logging.getLogger("jarvis")


class Assistant:
    def __init__(self, cfg, http, store=None):
        self.cfg = cfg
        self.engine = Engine(cfg, http)
        self.speaker = Speaker(cfg, self.publish)
        self.store = store or Store(ROOT / "data/memory.sqlite3")
        self.history = []
        self.clients = set()
        self.state = {"type": "state", "state": "booting", "expression": "neutral",
                      "text": "", "heard": "", "sources": [], "metrics": {}, "mock": cfg["mock"]}
        self.turn = self.warm = self.speech = self.reader = self.monitor = None
        self.speech_log = None
        self.timers = set()
        self.lock = asyncio.Lock()
        self.exiting = asyncio.Event()
        self.session = 0
        self.idle_since = time.monotonic()
        self.fatal = None
        self.audio_ready = cfg["mock"]

    def publish(self, event):
        if event["type"] == "state":
            self.state.update(event)
            event = dict(self.state)
        elif event["type"] == "reply":
            self.state["text"] = event["text"]
        elif event["type"] == "metrics":
            self.state["metrics"] = {k: v for k, v in event.items() if k != "type"}
        for client in list(self.clients):
            if client.full():
                # Slow browsers cannot hold back audio or inference.
                client.get_nowait()
            client.put_nowait(event)

    def transition(self, state, **kwargs):
        self.publish({"type": "state", "state": state, **kwargs})

    async def audio_command(self, action):
        if self.speech and self.speech.returncode is None:
            self.speech.stdin.write((json.dumps({"action": action, "session": self.session}) + "\n").encode())
            await self.speech.stdin.drain()

    async def start(self):
        (ROOT / "run").mkdir(exist_ok=True)
        if self.cfg["mock"]:
            self.transition("idle", text="Demo mode. Hardware and models are disabled.")
        else:
            self.speech_log = (ROOT / "run/speech.log").open("wb")
            self.speech = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "jarvis.speech_worker", cwd=ROOT,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=self.speech_log)
            self.reader = asyncio.create_task(self.read_audio())
        self.monitor = asyncio.create_task(self.maintenance())

    async def read_audio(self):
        try:
            while line := await self.speech.stdout.readline():
                event = json.loads(line)
                kind = event["type"]
                if kind == "ready":
                    self.audio_ready = True
                    if self.state["state"] == "booting":
                        self.transition("idle", text="Say Hey Jarvis")
                elif kind == "keyword":
                    key = event["keyword"].upper()
                    if key == "WAKE":
                        if self.state["state"] == "idle":
                            await self.wake()
                    elif key == "STOP":
                        await self.stop()
                    elif key == "EXIT":
                        await self.exit()
                elif kind in {"partial", "final"} and event["session"] == self.session and self.state["state"] == "listening":
                    if kind == "partial":
                        self.transition("listening", heard=event["text"])
                    elif event["text"]:
                        await self.submit(event["text"])
                    else:
                        await self.stop()
                elif kind == "warning":
                    self.publish(event)
            if not self.exiting.is_set():
                raise RuntimeError("Microphone/recognizer worker exited; inspect run/speech.log")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            LOG.exception("Audio failed")
            self.fatal = str(exc)
            self.transition("error", text=self.fatal, expression="concerned")
            self.exiting.set()

    async def wake(self):
        if not self.audio_ready:
            self.publish({"type": "warning", "text": "The microphone is still starting. Please wait."})
            return
        async with self.lock:
            was_busy = self.turn is not None and not self.turn.done()
            await self._cancel()
            if was_busy:
                await self.engine.stop()
            memory = system_memory()
            if memory and memory["used_bytes"] >= self.cfg["system_ram_limit_bytes"]:
                self.transition("error", text="Memory budget exceeded. Close other programs on the Pi.")
                return
            self.session += 1
            self.transition("listening", expression="curious", text="", heard="", sources=[])
            await self.audio_command("listen")
            if not self.cfg["mock"]:
                self.warm = asyncio.create_task(self._preload())

    async def _preload(self):
        try:
            await self.engine.ensure()
        except asyncio.CancelledError:
            raise
        except Exception:
            LOG.exception("LLM preload failed; the answer path will report the error")

    async def _cancel(self):
        self.session += 1
        await self.audio_command("idle")
        for task in (self.turn, self.warm):
            if task and not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        self.turn = self.warm = None
        await self.speaker.stop()

    async def stop(self):
        started = time.monotonic()
        async with self.lock:
            await self._cancel()
            # Force-kill on interruption: closing HTTP alone may leave inference busy.
            await self.engine.stop()
            self.idle_since = time.monotonic()
            self.transition("idle", expression="calm", text="Stopped. Say Hey Jarvis when ready.",
                            metrics={"stop_ms": round((time.monotonic() - started) * 1000)})

    async def exit(self):
        await self.stop()
        self.transition("offline", text="Goodbye.", expression="calm")
        await asyncio.sleep(0.05)
        self.exiting.set()

    async def submit(self, text):
        text = text.strip()[:600]
        action = control(text)
        if action == "stop":
            await self.stop()
            return
        if action == "exit":
            await self.exit()
            return
        if action == "wake":
            await self.wake()
            return
        if not text:
            return
        if not self.audio_ready:
            self.publish({"type": "warning", "text": "The microphone is still starting. Please wait."})
            return
        memory = system_memory()
        if memory and memory["used_bytes"] >= self.cfg["system_ram_limit_bytes"]:
            await self.stop()
            self.transition("error", text="Memory budget exceeded. Close other programs on the Pi.")
            return
        async with self.lock:
            # Preserve a completed/in-progress preload until answer.ensure joins it.
            await self.audio_command("idle")
            if self.turn and not self.turn.done():
                await self._cancel()
                await self.engine.stop()
            self.session += 1
            self.turn = asyncio.create_task(self.answer(text))

    async def answer(self, text):
        started = time.monotonic()
        metrics = {}
        notes = self.store.search(text)
        self.transition("thinking", heard=text, text="", expression="curious", sources=[n["source"] for n in notes], metrics=metrics)
        chunks = SpeechChunks()
        sentences = asyncio.Queue(maxsize=2)
        full = []

        def first_audio():
            if "first_audio_ms" not in metrics:
                metrics["first_audio_ms"] = round((time.monotonic() - started) * 1000)
                self.publish({"type": "metrics", **metrics})

        async def speak():
            while (sentence := await sentences.get()) is not None:
                self.transition("speaking", expression=expression(sentence))
                if self.cfg["mock"]:
                    first_audio()
                    self.publish({"type": "mouth", "level": 0.6})
                    await asyncio.sleep(0.08)
                else:
                    await self.speaker.say(sentence, first_audio)

        async def generate():
            direct = local_reply(text, self.store)
            seconds = timer_seconds(text)
            if seconds is not None:
                if len(self.timers) >= 8:
                    direct = "You already have eight timers. Please wait for one to finish."
                else:
                    task = asyncio.create_task(self.timer(seconds))
                    self.timers.add(task)
                    task.add_done_callback(self.timers.discard)
                    direct = f"Timer set for {seconds} seconds."
            if direct is not None:
                if self.warm and not self.warm.done():
                    self.warm.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await self.warm
                async def tokens():
                    yield direct
            elif self.cfg["mock"]:
                async def tokens():
                    for word in "I'm your offline companion. This demo shows the interface without loading Pi models.".split():
                        await asyncio.sleep(0.015)
                        yield word + " "
            else:
                def tokens():
                    return self.engine.tokens(text, self.history, self.store.facts(), notes)
            async for token in tokens():
                if "first_token_ms" not in metrics:
                    metrics["first_token_ms"] = round((time.monotonic() - started) * 1000)
                full.append(token)
                self.publish({"type": "reply", "text": "".join(full)[:2400]})
                for part in chunks.feed(token):
                    await sentences.put(part)
            for part in chunks.feed("", final=True):
                await sentences.put(part)
            if not full:
                raise RuntimeError("The model returned an empty answer")
            await sentences.put(None)

        try:
            # A failure in either side cancels the other, including a blocked queue.
            async with asyncio.TaskGroup() as group:
                group.create_task(generate())
                group.create_task(speak())
            await self.speaker.finish()
            reply = "".join(full).strip()[:1200]
            self.history.extend([{"role": "user", "content": text[:400]}, {"role": "assistant", "content": reply[:400]}])
            self.history = self.history[-4:]
            metrics["turn_ms"] = round((time.monotonic() - started) * 1000)
            self.publish({"type": "metrics", **metrics})
            self.transition("idle", text=reply, metrics=metrics, expression=expression(reply))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            LOG.exception("Turn failed")
            await self.engine.stop()
            self.transition("error", text=f"Reply failed: {exc}. Check run logs.", expression="concerned")
        finally:
            await self.speaker.stop()
            self.idle_since = time.monotonic()
            if self.cfg["idle_unload_seconds"] == 0:
                await self.engine.stop()

    async def timer(self, seconds):
        await asyncio.sleep(seconds)
        self.publish({"type": "timer", "text": "Your timer is finished."})
        # Timers never interrupt a current answer or activate listening.
        if self.state["state"] == "idle":
            await self.submit("timer alert")

    async def maintenance(self):
        startup_deadline = time.monotonic() + 30
        while True:
            await asyncio.sleep(1)
            if self.state["state"] == "booting" and time.monotonic() > startup_deadline:
                self.fatal = "Speech worker startup timed out; inspect run/speech.log"
                self.transition("error", text=self.fatal)
                self.exiting.set()
                return
            memory = system_memory()
            self.publish({"type": "system", "memory": memory, "temperature_c": temperature()})
            if memory and memory["used_bytes"] >= self.cfg["system_ram_limit_bytes"]:
                if self.state["state"] not in {"error", "offline"}:
                    await self.stop()
                    self.transition("error", text="Pi memory pressure: heavy workers stopped.", expression="concerned")
            elif self.state["state"] in {"idle", "error"} and self.engine.process and time.monotonic() - self.idle_since >= self.cfg["idle_unload_seconds"]:
                await self.engine.stop()

    async def close(self):
        self.exiting.set()
        for task in list(self.timers):
            task.cancel()
        if self.timers:
            await asyncio.gather(*self.timers, return_exceptions=True)
        if self.monitor:
            self.monitor.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.monitor
        await self.stop()
        if self.reader:
            self.reader.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.reader
        await terminate(self.speech)
        if self.speech_log:
            self.speech_log.close()
        self.store.close()


def make_web(assistant):
    app = web.Application(client_max_size=2048)

    async def index(request):
        return web.FileResponse(ROOT / "web/index.html")

    async def status(request):
        return web.json_response(assistant.state)

    async def websocket(request):
        if request.headers.get("Origin") != f"http://{request.host}":
            raise web.HTTPForbidden(text="Open the GUI through your SSH tunnel")
        if len(assistant.clients) >= 4:
            raise web.HTTPServiceUnavailable(text="Maximum four GUI clients")
        ws = web.WebSocketResponse(heartbeat=20, max_msg_size=2048)
        await ws.prepare(request)
        events = asyncio.Queue(maxsize=16)
        assistant.clients.add(events)
        await ws.send_json(assistant.state)

        async def send():
            while True:
                await ws.send_json(await events.get())

        sender = asyncio.create_task(send())
        try:
            async for message in ws:
                if message.type == aiohttp.WSMsgType.TEXT:
                    try:
                        event = json.loads(message.data)
                        action = event.get("action")
                        if action == "wake":
                            await assistant.wake()
                        elif action == "stop":
                            await assistant.stop()
                        elif action == "exit":
                            await assistant.exit()
                        elif action == "ask" and isinstance(event.get("text"), str):
                            await assistant.submit(event["text"])
                        else:
                            await ws.send_json({"type": "warning", "text": "Unknown command"})
                    except (ValueError, AttributeError):
                        await ws.send_json({"type": "warning", "text": "Invalid message"})
        finally:
            assistant.clients.discard(events)
            sender.cancel()
            with contextlib.suppress(asyncio.CancelledError, ConnectionError):
                await sender
        return ws

    app.router.add_get("/", index)
    app.router.add_get("/api/status", status)
    app.router.add_get("/ws", websocket)
    app.router.add_static("/static/", ROOT / "web")
    return app


async def run(cfg):
    async with aiohttp.ClientSession(trust_env=False) as http:
        assistant = Assistant(cfg, http)
        runner = web.AppRunner(make_web(assistant))
        try:
            await runner.setup()
            await web.TCPSite(runner, cfg["host"], cfg["port"]).start()
            await assistant.start()
            loop = asyncio.get_running_loop()
            if os.name != "nt":
                for sig in (signal.SIGTERM, signal.SIGINT):
                    loop.add_signal_handler(sig, assistant.exiting.set)
            LOG.info("GUI: http://127.0.0.1:%s; mock=%s", cfg["port"], cfg["mock"])
            await assistant.exiting.wait()
        finally:
            await assistant.close()
            await runner.cleanup()
        if assistant.fatal:
            raise RuntimeError(assistant.fatal)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="GUI demo without models or audio")
    args = parser.parse_args()
    cfg = load_config()
    cfg["mock"] = cfg["mock"] or args.mock
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        asyncio.run(run(cfg))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
