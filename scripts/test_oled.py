import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jarvis.config import load_config
from jarvis.oled import OledBridge

bridge = OledBridge(load_config(profile="laptop"))
bridge.start()
try:
    print("Close Jarvis and Serial Monitor before this test. Waiting up to 20 seconds for the OLED...")
    deadline = time.monotonic() + 20
    while not bridge.connected and time.monotonic() < deadline:
        time.sleep(0.1)
    if not bridge.connected:
        raise SystemExit("No Jarvis OLED found. Flash the firmware, check USB/COM port and wiring.")
    bridge.update("speaking", "Hello from your offline Jarvis assistant. This is a longer response to test readable word wrapping and smooth automatic vertical scrolling. The header should stay fixed while these lines move below it. A verylongwordwithoutspaces1234567890 must wrap safely too. Please check that no letters overlap and that the display pauses before returning to the beginning.")
    print("Long text sent. Observe the OLED for 40 seconds.")
    time.sleep(40)
finally:
    bridge.close()
