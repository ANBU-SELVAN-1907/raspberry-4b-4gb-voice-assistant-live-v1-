"""Explicit one-thread ONNX session; Piper defaults may consume all cores."""
import json
from pathlib import Path


def load_voice(path):
    import onnxruntime as ort
    from piper import PiperVoice
    from piper.config import PiperConfig
    path = Path(path)
    config = PiperConfig.from_dict(json.loads(Path(str(path) + ".json").read_text(encoding="utf-8")))
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    session = ort.InferenceSession(str(path), sess_options=options, providers=["CPUExecutionProvider"])
    return PiperVoice(session=session, config=config)
