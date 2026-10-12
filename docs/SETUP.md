# Pi and headset setup

1. Flash **Raspberry Pi OS Lite 64-bit**, Bookworm or Trixie, to the32 GB SD with Raspberry Pi Imager. Set your username, SSH credentials, and local Wi-Fi. Use normal SSH authentication; no default username/password is assumed.
2. Boot the Pi, plug the Blackwire3210 into a Pi USB port, and SSH in. Check `uname -m` gives `aarch64` and `free -h` shows the expected memory.
3. Follow the five commands in the README. Keep the headset plugged in during configuration and service install. The installer downloads approximately 900 MB of model/archive assets plus dependencies/source. It validates checksums, retries/resumes downloads, builds with a single compilation job, and preserves existing `config.json`.
4. The audio step backs up an existing `~/.asoundrc` as `~/.asoundrc.before-jarvis` before selecting the headset as your user's ALSA default input/output. ALSA's plug device resamples for 16 kHz Piper output and 48 kHz capture. It does not alter the system-wide `/etc/asound.conf`.
5. Test recording/playback with the service stopped, then restart it. Use `alsamixer -c CARD_ID` for capture gain, speaker volume, and unmute. Ensure the headset's physical microphone mute is off.
6. Open an SSH tunnel from the laptop and view the local browser page. The laptop microphone is not used. The browser needs no camera, microphone permission, npm build, or online fonts.

The service runs under your existing user with the audio supplementary group. Its memory limit requires working systemd cgroup memory accounting; verify with `systemctl show jarvis -p MemoryMax -p MemoryCurrent -p MemorySwapMax`. A cgroup-v2 Pi OS installation is the supported deployment.

For local clock answers, ensure the Pi timezone/date are correct. If you want India time, configure `sudo timedatectl set-timezone Asia/Kolkata`. A Pi 4 has no built-in battery-backed RTC; after a long offline power loss the clock may be wrong until you set it or synchronize it. Timers use a monotonic clock and are independent of timezone.

## Profiles

Copy defaults only once; later edit your untracked `config.json`:

| Setting | Suggested value | Meaning |
|---|---:|---|
| `idle_unload_seconds` | 0 | Minimum heavy-model idle residency; cold start every turn |
| `idle_unload_seconds` |45 | Reuse LLM for fast repeated questions; release after45seconds idle |
| `threads` |3 | Default LLM CPU threads |
| `threads` |2 | Try if audio overflows or the Pi gets hot |
| `context` |2048 | Bounded chat context; reduce to1024 for a stricter memory profile |
| `max_tokens` |96 | Crisp replies; reduce to64 for shorter speech |
| `endpoint_silence_seconds` |0.55 | Pause to end a question; increase to0.8 if speech is cut off |
| `input_rate` |48000 | Headset capture rate; sherpa internally resamples |
| `kws_threshold` |0.2 | Keyword probability threshold; increase toward 0.3 if false triggers occur |
| `kws_score` |2.0 | Keyword boost; reduce toward 1.5 if false triggers occur |

Restart after changing settings: `bash scripts/service.sh restart`. Do not expose the GUI or llama.cpp to a public interface. The config validator intentionally restricts the GUI to loopback.

## Updating / offline reinstall

Stop the service, `git pull --ff-only`, and rerun `bash scripts/install.sh`; then restart. Record the release and run acceptance again. A newer release can change behavior. `LLAMA_REF=v0.6.0 bash scripts/install.sh` requests the verified source release explicitly.

The installer requires internet. After successful installation, restarting and all normal voice use require no internet. A new offline machine still needs the installed virtualenv, compiled ARM64 runtime, and local model files; the Git repository deliberately excludes model binaries and downloaded dependencies. A Windows virtualenv/binary cannot be copied to ARM64 Linux.

You can transfer the complete folder to the Pi instead of cloning from GitHub. Use `~/jarvis` as its destination and run the installer on the Pi. It clears/rebuilds its managed `.venv`, compiles Linux ARM64 binaries, and reuses verified model downloads. The laptop project folder is unnecessary afterward; its browser displays files served by the Pi through the SSH tunnel. Your Blackwire microphone and speaker both remain connected to the Pi.

To remove the service: `bash scripts/service.sh uninstall`. The repository, downloaded models, local facts, and audio backup remain. Restore your previous `~/.asoundrc` from its backup if you want the old audio defaults.
