# Validation evidence

Verified on 12 October 2026 using an isolated Windows Python 3.12 environment. These results establish source/API compatibility and synthetic behavior, **not Pi 4 hardware performance**.

| Check | Result |
|---|---|
| Python unit + asynchronous integration suite | 16 tests passed, including 20 sequential turns |
| Python source compilation | Passed |
| JavaScript syntax | Passed |
| Bash syntax | Passed |
| ShellCheck 0.11.0 | Passed |
| ARM64 Python 3.11 and 3.13 binary dependency resolution | Passed for all dependencies, including ONNX Runtime |
| Download asset SHA256 checks | Passed for every pinned file/archive |
| Actual Piper 1.8.0 one-thread ONNX voice | Loaded, generated 16 kHz PCM, subprocess protocol verified |
| Actual sherpa-onnx 1.13.8 keyword detector | Deterministic synthetic Hey Jarvis / Okay stop / Exit detected |
| Actual streaming STT | Synthetic “What is the capital of France?” transcribed correctly |
| Actual llama.cpp API + official LFM2.5 GGUF | Reply: “The capital of France is Paris.” |
| Native Windows llama.cpp CPU binary | Official b11429 referenced by v0.6.0 release; API smoke only |
| Laptop browser controls | Ask/response flow checked; no browser errors observed |
| Layout | Checked at 1280 × 900 and 3840 × 2160; no horizontal document overflow |
| Plantronics Blackwire 3210 on Pi | Pending hardware |
| Native ARM64 build/run | Pending hardware |
| Whole-system 3.2 GB peak / cgroup enforcement | Pending hardware |
| Natural speech wake/STT accuracy / perceived latency | Pending hardware |

The speech test uses deterministic synthesis settings to avoid random Piper noise variation. It does not establish recognition reliability for a real person's accent or noisy microphone. The original tiny 20M STT candidate was rejected after dropping words in a short synthetic question; the shipped model is the stronger 73 MB English Zipformer from 2023-06-26. Wake pronunciations include dictionary-based Jarvis and Okay variants; natural speech still requires calibration.

Tests cover exact control matching, bounded text chunks, timer parsing including spoken numbers, explicit memory/forget behavior, knowledge indexing, stable audio card selection, config limits, streamed SSE transport fragmentation, generation cancellation, failure recovery, memory-pressure gating, browser backpressure, reconnect state, same-origin access, and normal Exit cleanup. A simulated audio failure is deliberately injected in one test; its expected error log is evidence of recovery, not a deployment error.

Follow [ACCEPTANCE.md](ACCEPTANCE.md) on your Pi before claiming that hardware-specific targets are met. The installers include doctor and real-model smoke commands to repeat these checks on ARM64.
