import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis.config import load_config
from jarvis.oled import OledBridge, encode_snapshot, display_text
from scripts.windows_audio import device_id
from jarvis.metrics import memory_pressure
from scripts.windows_memory import repair_config


class LaptopTests(unittest.TestCase):
    def test_laptop_memory_guard_checks_available_ram_and_recovers_with_margin(self):
        cfg = load_config(Path("unused-config"), profile="laptop")
        memory = {"used_bytes": 14200000000, "available_bytes": 2500000000}
        self.assertIsNone(memory_pressure(memory, cfg))
        low = {"used_bytes": 14200000000, "available_bytes": 1200000000}
        self.assertIn("1.20 GB available", memory_pressure(low, cfg))
        edge = {"used_bytes": 14200000000, "available_bytes": 1600000000}
        self.assertIsNone(memory_pressure(edge, cfg))
        self.assertIsNotNone(memory_pressure(edge, cfg, recovering=True))
        self.assertIsNone(memory_pressure(memory, cfg, recovering=True))

    def test_pi_memory_guard_preserves_strict_system_budget(self):
        cfg = load_config(Path("unused-config"), profile="pi")
        self.assertIsNone(memory_pressure({"used_bytes": 3199999999}, cfg))
        self.assertIsNotNone(memory_pressure({"used_bytes": 3200000000}, cfg))

    def test_memory_repair_preserves_audio_and_backs_up_original(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "config.laptop.json"
            original = '{"system_ram_limit_bytes":3200000000,"input_device":"USB Headset"}'
            path.write_text(original, encoding="utf-8-sig")
            repair_config(path)
            cfg = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(cfg["input_device"], "USB Headset")
            self.assertEqual(cfg["system_ram_limit_bytes"], 16000000000)
            backup = path.with_name(path.name + ".before-memory-repair")
            self.assertEqual(backup.read_text(encoding="utf-8-sig"), original)
            repair_config(path)
            self.assertEqual(backup.read_text(encoding="utf-8-sig"), original)

    def test_laptop_profile_accepts_laptop_threads_and_context(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = load_config(Path(folder) / "missing", profile="laptop")
        self.assertEqual(cfg["threads"], 6)
        self.assertEqual(cfg["context"], 4096)
        self.assertIsNone(cfg["input_device"])
        self.assertEqual(cfg["llama_binary"], "vendor/windows/llama-server.exe")

    def test_oled_wire_frame_is_ascii_bounded_and_atomic(self):
        text = '“Hello”\n' + "many words " * 1000
        frame = encode_snapshot("session", 123, "speaking", text)
        self.assertLess(len(frame), 8192)
        self.assertEqual(frame.count(b"\n"), 1)
        parsed = json.loads(frame)
        self.assertLessEqual(len(parsed["text"]), 2400)
        self.assertTrue(parsed["text"].startswith('"Hello"'))
        self.assertEqual(parsed["seq"], 123)

    def test_oled_updates_coalesce_without_a_growing_queue(self):
        bridge = OledBridge({"oled_enabled": False})
        for i in range(10000):
            bridge.update("speaking", str(i))
        self.assertEqual(bridge.latest, (10000, "speaking", "9999"))
        bridge.update("speaking", "9999")
        self.assertEqual(bridge.latest[0], 10000)
        bridge.close()

    def test_audio_selection_uses_stable_name_and_host_api(self):
        devices = [{"name": "USB Headset", "hostapi": 0, "max_input_channels": 1},
                   {"name": "USB Headset", "hostapi": 1, "max_input_channels": 1}]
        apis = [{"name": "MME"}, {"name": "Windows WASAPI"}]
        self.assertEqual(device_id("USB Headset | Windows WASAPI", "input", devices, apis), 1)
        self.assertIsNone(device_id(None, "input", devices, apis))
        with self.assertRaises(ValueError):
            device_id("Missing | MME", "input", devices, apis)

    def test_resampling_is_continuous_across_pcm_chunks(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest("NumPy not installed in the minimal CI job")
        from jarvis.resample import LinearResampler
        pcm = np.arange(-500, 500, dtype=np.int16).tobytes()
        whole = LinearResampler(16000, 48000).convert(pcm)
        worker = LinearResampler(16000, 48000)
        split = b"".join(worker.convert(pcm[i:i+200]) for i in range(0, len(pcm), 200))
        self.assertTrue(np.allclose(np.frombuffer(whole, dtype=np.int16), np.frombuffer(split, dtype=np.int16), atol=1))

    def test_non_ascii_text_is_display_safe(self):
        self.assertEqual(display_text("café — hello…"), "cafe - hello...")
