"""Optional bounded, reconnecting serial display. No serial I/O on the AI loop."""
import json
import logging
import threading
import time
import unicodedata
import uuid

LOG = logging.getLogger("jarvis.oled")
MAX_TEXT = 2400


def display_text(text):
    text = text.translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "—": "-", "–": "-", "…": "..."}))
    text = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    text = text.encode("ascii", "replace").decode()
    return " ".join(text.split())[:MAX_TEXT]


def encode_snapshot(session, sequence, state, text):
    return (json.dumps({"v": 1, "session": session, "seq": sequence,
                        "state": state[:16], "text": display_text(text)}, ensure_ascii=True,
                       separators=(",", ":")) + "\n").encode("ascii")


class OledBridge:
    def __init__(self, cfg):
        self.cfg = cfg
        self.closed = threading.Event()
        self.lock = threading.Lock()
        self.latest = (0, "booting", "Starting Jarvis...")
        self.session = uuid.uuid4().hex[:12]
        self.thread = None
        self.connected = False

    def start(self):
        if self.cfg.get("oled_enabled") and self.thread is None:
            self.thread = threading.Thread(target=self._run, daemon=True, name="oled-serial")
            self.thread.start()

    def update(self, state, text):
        value = display_text(text)
        with self.lock:
            sequence, old_state, old_text = self.latest
            if (old_state, old_text) != (state, value):
                self.latest = (sequence + 1, state, value)

    def close(self):
        self.closed.set()
        if self.thread:
            self.thread.join(timeout=2)

    def _candidates(self):
        from serial.tools import list_ports
        requested = self.cfg["oled_port"]
        if requested != "auto":
            return [requested]
        # Probe only common ESP32 USB IDs; explicit COM port supports other adapters.
        return [port.device for port in list_ports.comports()
                if port.vid in {0x10C4, 0x1A86, 0x303A, 0x0403}]

    def _connect(self):
        import serial
        for port in self._candidates():
            if self.closed.is_set():
                return None
            handle = serial.Serial(port=None, baudrate=self.cfg["oled_baud"], timeout=0.15, write_timeout=0.2)
            handle.dtr = False
            handle.rts = False
            handle.port = port
            try:
                handle.open()
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline and not self.closed.is_set():
                    handle.write(b'{"ping":1}\n')
                    if b"JARVIS_OLED_READY v1" in handle.read_until(b"\n", 128):
                        LOG.info("OLED connected on %s", port)
                        return handle
            except (serial.SerialException, OSError):
                pass
            handle.close()
        return None

    def _run(self):
        import serial
        handle = None
        sent = -1
        last_send = 0
        last_ack = 0
        try:
            while not self.closed.is_set():
                if handle is None:
                    handle = self._connect()
                    if handle is None:
                        self.closed.wait(2)
                        continue
                    self.connected = True
                    sent = -1
                    last_ack = time.monotonic()
                try:
                    with self.lock:
                        sequence, state, text = self.latest
                    now = time.monotonic()
                    if (sequence != sent and now - last_send >= 0.2) or now - last_send >= 2:
                        payload = encode_snapshot(self.session, sequence, state, text)
                        if handle.write(payload) != len(payload):
                            raise serial.SerialException("Incomplete OLED frame")
                        sent, last_send = sequence, now
                    if handle.in_waiting:
                        line = handle.read_until(b"\n", 128)
                        if b"JARVIS_OLED_ACK" in line or b"JARVIS_OLED_READY" in line:
                            last_ack = now
                    if now - last_ack > 6:
                        raise serial.SerialException("OLED stopped acknowledging")
                    self.closed.wait(0.05)
                except (serial.SerialException, OSError):
                    handle.close()
                    handle = None
                    self.connected = False
                    self.closed.wait(1)
        finally:
            if handle:
                handle.close()
            self.connected = False
