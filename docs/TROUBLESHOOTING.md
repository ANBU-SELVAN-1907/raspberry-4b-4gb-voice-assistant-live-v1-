# Troubleshooting

| Symptom | Check and resolution |
|---|---|
| Installer says ARM32 | Reflash Pi OS Lite64-bit; ARM32 cannot use this model/runtime configuration. |
| Installer fails downloading | Rerun it; completed assets are verified and partial downloads resume. Check the reported URL/connectivity and free disk space. |
| Missing ARM wheel | Use supported Python3.11–3.13 on Debian-based Pi OS64-bit. Never force a large source build as a workaround. Inspect the package named in the error. |
| Compilation killed | Stop unrelated services, check free RAM, cooling/power. Installer already uses one build job. Runtime memory limits do not apply during install. |
| llama.cpp exits | Inspect `run/llama.log`, model hash, free RAM, and recorded release. Try the verified `LLAMA_REF=v0.6.0` release. |
| Cannot find headset | Run `arecord -l`, `aplay -l`, `cat /proc/asound/cards`; pass the stable ID with `bash scripts/configure_audio.sh --card ID`. |
| Device busy | Stop the service before `audio_test.sh`, `doctor.py --audio`, or a second foreground run. Close other processes using ALSA. |
| No microphone input | Check physical mute and `alsamixer` capture; test with `audio_test.sh`. Inspect `run/speech.log`. |
| No spoken output | Check headset playback volume, ALSA default, `run/tts.log`; replay the audio-test recording. |
| GUI disconnected | Keep the laptop SSH tunnel open. Confirm service is active and port 8765 is free on the laptop. Visit127.0.0.1, not the Pi address. |
| Wake word unreliable | Use the close-talk microphone and a short pause after “Hey Jarvis.” Test quiet-room speech first. The browser Wake button bypasses keyword detection. |
| Own speech triggers Stop/Exit | Lower earpiece volume and mic gain, use the headset instead of a room speaker. This project has no full acoustic echo cancellation. |
| Speech clipped / words wrong | Increase endpoint silence to0.8seconds, speak near the mic, check capture gain. This small English model has accuracy limits. |
| Audio overflow warnings | Try two LLM threads, verify USB cable/power and CPU temperature; keep the OS headless and stop unrelated jobs. |
| Answers take a while | Cold SD-card loading and a Pi 4CPU are the bottlenecks. Try45second LLM warm residency, shorter replies, and measure actual first-audio latency. |
| Service OOM / memory warning | Check service peak and whole-system use. Reduce context/tokens, close other jobs, keep default model. Do not simply increase memory limits. |
| Incorrect time/date | Set the Pi timezone/clock; an offline Pi 4 lacks a built-in battery-backed RTC. |
| Exit leaves GUI disconnected | Expected. Exit closes Jarvis normally without powering off the Pi. Use `bash scripts/service.sh start`. |
| Local notes not used | Run the indexer; use words that occur in notes. Retrieval is keyword-based, not semantic. |

Useful checks:

```bash
journalctl -u jarvis -n80 --no-pager
systemctl show jarvis -p MemoryCurrent -p MemoryPeak -p MemoryMax -p MemorySwapMax
free -h
vcgencmd get_throttled
cat /sys/class/thermal/thermal_zone0/temp
```

`vcgencmd` is optional and may not exist on other distributions. Model, microphone, and audio failures are explicit; the application does not silently switch to a cloud service.
