import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from jarvis.config import load_config
from jarvis.skills import local_reply, timer_seconds
from jarvis.store import Store
from jarvis.text import SpeechChunks, control


class CoreTests(unittest.TestCase):
    def test_control_is_exact_and_does_not_stop_normal_questions(self):
        self.assertEqual(control("Okay, stop!"), "stop")
        self.assertEqual(control("EXIT"), "exit")
        self.assertIsNone(control("Why do trains stop at stations?"))
        self.assertIsNone(control("What is an exit poll?"))

    def test_chunking_sentence_boundaries_and_long_unpunctuated_text(self):
        chunks = SpeechChunks()
        self.assertEqual(chunks.feed("Hello there. Next"), ["Hello there."])
        self.assertEqual(chunks.feed(" sentence!"), ["Next sentence!"])
        parts = chunks.feed("x " * 210, final=True)
        self.assertTrue(all(len(p) <= 160 for p in parts))
        self.assertEqual(" ".join(parts), ("x " * 210).strip())

    def test_memory_is_bounded_and_forget_does_not_remove_knowledge(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "memory.sqlite3")
            for i in range(30):
                store.remember(str(i))
            self.assertEqual(len(store.facts()), 10)
            self.assertEqual(store.facts()[0], "29")
            notes = Path(tmp) / "notes"
            notes.mkdir()
            (notes / "pi.md").write_text("Raspberry hardware has a processor.")
            self.assertEqual(store.index(notes), 1)
            self.assertEqual(len(store.search('raspberry " OR syntax:')), 1)
            store.forget()
            self.assertEqual(store.facts(), [])
            self.assertEqual(len(store.search("raspberry")), 1)
            self.assertEqual(store.search("!!!"), [])
            store.close()

    def test_timer_has_positive_bounded_duration(self):
        self.assertEqual(timer_seconds("Set a timer for 2 minutes"), 120)
        self.assertEqual(timer_seconds("set a timer for two minutes"), 120)
        self.assertEqual(timer_seconds("timer twenty five seconds"), 25)
        self.assertEqual(timer_seconds("timer 99999 hours"), 86400)
        self.assertIsNone(timer_seconds("timer 0 seconds"))
        self.assertIsNone(timer_seconds("tell me about timers"))

    def test_config_rejects_oversized_context_and_public_bind(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.json"
            for custom in ({"context": 8192}, {"threads": 4}, {"host": "0.0.0.0"}, {"system_ram_limit_bytes": 4000000000}):
                path.write_text(json.dumps(custom))
                with self.assertRaises(ValueError):
                    load_config(path)

    def test_audio_card_selection_handles_number_changes_and_ambiguity(self):
        spec = importlib.util.spec_from_file_location("audio_setup", Path(__file__).resolve().parent.parent / "scripts/configure_audio.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cards = module.parse_cards(" 0 [Headphones     ]: bcm2835 - Internal\n 2 [P3210          ]: USB-Audio - Plantronics Blackwire 3210\n")
        self.assertEqual(module.select_card(cards)["id"], "P3210")
        self.assertEqual(module.select_card(cards, "2")["id"], "P3210")
        with self.assertRaises(ValueError):
            module.select_card(cards + cards)

    def test_explicit_saved_facts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "facts.db")
            self.assertEqual(local_reply("remember that I like tea", store), "I'll remember that.")
            self.assertEqual(store.facts(), ["I like tea"])
            self.assertEqual(local_reply("forget my memory", store), "I've cleared your saved facts.")
            store.close()
