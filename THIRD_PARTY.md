# Model and dependency licenses

The repository's original code is MIT licensed. Model assets and dependencies are downloaded separately and retain their own terms; they are not covered by this repository's MIT license.

| Asset | Upstream / license reference |
|---|---|
| LFM2.5-1.2B-Instruct | [LiquidAI model card and LFM license](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF); `lfm1.0`, including its stated commercial conditions |
| sherpa-onnx | [Apache2.0 code](https://github.com/k2-fsa/sherpa-onnx/blob/master/LICENSE); model provenance and terms are documented in official model documentation |
| Piper runtime | [GPL3.0 code](https://github.com/OHF-Voice/piper1-gpl/blob/main/LICENSE.md); installed separately, called through a process interface |
| Lessac voice | [Voice model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/lessac/low/MODEL_CARD), also downloaded to `models/tts/MODEL_CARD` |
| llama.cpp | [MIT code](https://github.com/ggml-org/llama.cpp/blob/master/LICENSE) |

Read upstream terms before redistribution or commercial deployment. Assets are pinned by source revision/checksum in `models.lock.json`; runtime installation records exact Python package versions. No proprietary character, external font, or remotely hosted animation asset is included.
