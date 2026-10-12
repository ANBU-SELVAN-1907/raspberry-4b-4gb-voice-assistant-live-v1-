# Hardware acceptance — fill this in on your Pi

Development machine tests do not establish Pi 4 performance. Record actual results before declaring the3.2 GB system target or low-latency goal achieved.

| Item | Actual result |
|---|---|
| Pi model / RAM / OS / Python | Pending |
| llama.cpp release + commit | Pending |
| Power supply / cooling / SD model | Pending |
| Headset capture and speaker playback | Pending |
| Idle estimated system used RAM | Pending |
| Service MemoryPeak after 20 turns | Pending |
| Estimated system peak used RAM during20turns | Pending |
| Cold model load time | Pending |
| Cold / warm first token | Pending |
| Full voice first-audio median / slowest | Pending |
| Stop application delay / perceived speech stop delay | Pending |
| Wake successes out of 20 natural attempts | Pending |
| STT correctly transcribed questions out of 20 | Pending |
| Peak temperature / throttling flags | Pending |
| Fully offline conversation | Pending |
| Exit stops normally without restart | Pending |

1. Run audio_test with the service stopped. Confirm your own voice is recorded and heard in the headset. Check synthetic model smoke tests.
2. Run benchmark with the service stopped; save its JSON. Start the service and the laptop SSH tunnel.
3. Disconnect the router's internet/upstream connection, keeping the local network link. Ask general questions, memory questions, and questions about local notes.
4. Run 20 turns, mixing short and longer questions. Note GUI first-audio timings. In a second SSH terminal sample system use with `watch -n0.5 free -b`, and record the largest `MemTotal - MemAvailable`. Check `MemoryPeak` for the complete service cgroup. Sampling does not prove that no shorter transient peak occurred.
5. Interrupt ten answers with “okay stop.” Try the Stop button too. Check there is no trailing old answer on a new query and no orphaned llama.cpp process. Keyword acoustic delay and sound-device buffering are separate from application cancellation.
6. Leave idle for two minutes in cold mode. Verify no llama-server/Piper worker remains with `pgrep -af 'llama-server|jarvis.tts_worker'`; the tiny wake/audio worker remains running.
7. Say “exit.” Check `systemctl is-active jarvis` becomes inactive. Start it again and verify reboot startup when desired.

If any result fails, keep the failure visible and tune settings or hardware before using the performance claim. The implementation cannot certify a whole-machine3.2 GB hard ceiling, perfect accents, all expressions, or instant intelligence on a Pi 4.
