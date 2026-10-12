import asyncio
import json
import tempfile
import unittest
from pathlib import Path

import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestServer

from jarvis.app import Assistant, make_web
from jarvis.config import load_config
from jarvis.engine import Engine
from jarvis.store import Store


class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from unittest.mock import patch
        self.memory_patch = patch("jarvis.app.system_memory", return_value={})
        self.memory_patch.start()
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = load_config(Path(self.tmp.name) / "absent.json", profile="pi")
        self.cfg["mock"] = True
        self.http = aiohttp.ClientSession()
        self.assistant = Assistant(self.cfg, self.http, Store(Path(self.tmp.name) / "test.db"))
        await self.assistant.start()

    async def asyncTearDown(self):
        await self.assistant.close()
        await self.http.close()
        self.tmp.cleanup()
        self.memory_patch.stop()

    async def test_interrupt_cancels_generation_and_returns_idle(self):
        await self.assistant.submit("Tell me a story")
        turn = self.assistant.turn
        await asyncio.sleep(0.06)
        await asyncio.wait_for(self.assistant.stop(), 1)
        self.assertTrue(turn.done())
        self.assertEqual(self.assistant.state["state"], "idle")
        self.assertIsNone(self.assistant.engine.process)

    async def test_reply_failure_cancels_producer_instead_of_hanging(self):
        self.assistant.cfg["mock"] = False
        async def fail(*args, **kwargs):
            raise RuntimeError("test speaker unavailable")
        self.assistant.speaker.say = fail
        await self.assistant.submit("help")
        await asyncio.wait_for(self.assistant.turn, 2)
        self.assertEqual(self.assistant.state["state"], "error")

    async def test_repeated_turns_bound_history_and_saved_memory(self):
        for _ in range(20):
            await self.assistant.submit("what time is it")
            await asyncio.wait_for(self.assistant.turn, 2)
        self.assertEqual(len(self.assistant.history), 4)
        self.assertEqual(self.assistant.state["state"], "idle")

    async def test_websocket_origin_guard_and_command_roundtrip(self):
        server = TestServer(make_web(self.assistant))
        await server.start_server()
        try:
            async with self.http.get(server.make_url("/")) as response:
                self.assertEqual(response.status, 200)
                self.assertIn("Animated companion", await response.text())
            with self.assertRaises(aiohttp.WSServerHandshakeError):
                await self.http.ws_connect(server.make_url("/ws"), origin="https://foreign.example")
            origin = str(server.make_url("/")).rstrip("/")
            async with self.http.ws_connect(server.make_url("/ws"), origin=origin) as ws:
                self.assertEqual((await ws.receive_json())["state"], "idle")
                await ws.send_json({"action": "ask", "text": "remember that my name is Anbu"})
                async with asyncio.timeout(3):
                    while True:
                        event = await ws.receive_json()
                        if event.get("state") == "idle" and event.get("text") == "I'll remember that.":
                            break
                self.assertEqual(self.assistant.store.facts(), ["my name is Anbu"])
                await ws.send_str("broken json")
                async with asyncio.timeout(2):
                    while (await ws.receive_json())["type"] != "warning":
                        pass
        finally:
            await server.close()

    async def test_exit_sets_shutdown_event_and_stops_workers(self):
        await self.assistant.submit("exit")
        self.assertTrue(self.assistant.exiting.is_set())
        self.assertEqual(self.assistant.state["state"], "offline")

    async def test_slow_browser_queue_remains_bounded(self):
        queue = asyncio.Queue(maxsize=2)
        self.assistant.clients.add(queue)
        for i in range(100):
            self.assistant.publish({"type": "reply", "text": str(i)})
        self.assertEqual(queue.qsize(), 2)
        self.assertEqual((await queue.get())["text"], "98")
        self.assistant.clients.remove(queue)

    async def test_memory_pressure_blocks_wake_and_stops_heavy_work(self):
        from unittest.mock import patch
        with patch("jarvis.app.system_memory", return_value={"used_bytes": 3300000000}):
            await self.assistant.wake()
        self.assertEqual(self.assistant.state["state"], "error")
        self.assertIsNone(self.assistant.engine.process)
        with patch("jarvis.app.system_memory", return_value={"used_bytes": 3300000000}):
            await self.assistant.submit("tell me something")
        self.assertEqual(self.assistant.state["state"], "error")
        self.assertIsNone(self.assistant.turn)

    async def test_speaking_state_preserves_streamed_reply_for_reconnect(self):
        self.assistant.publish({"type": "reply", "text": "Hello friend."})
        self.assistant.transition("speaking")
        self.assertEqual(self.assistant.state["text"], "Hello friend.")

    async def test_llama_sse_handles_fragmented_transport_and_request_bounds(self):
        received = {}
        async def completion(request):
            received.update(await request.json())
            response = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
            await response.prepare(request)
            body = 'data: {"choices":[{"delta":{"content":"Hello "}}]}\n\ndata: {"choices":[{"delta":{"content":"friend."}}]}\n\ndata: [DONE]\n\n'.encode()
            for start in range(0, len(body), 7):
                await response.write(body[start:start+7])
            await response.write_eof()
            return response
        app = web.Application()
        app.router.add_post("/v1/chat/completions", completion)
        server = TestServer(app)
        await server.start_server()
        engine = Engine({**self.cfg, "llama_port": server.port}, self.http)
        async def ready():
            pass
        engine.ensure = ready
        try:
            result = [token async for token in engine.tokens("x" * 1000, [], [], [])]
            self.assertEqual("".join(result), "Hello friend.")
            self.assertEqual(len(received["messages"][-1]["content"]), 600)
            self.assertLessEqual(received["max_tokens"], 128)
        finally:
            await server.close()
