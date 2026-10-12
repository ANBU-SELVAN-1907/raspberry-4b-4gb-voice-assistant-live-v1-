"""Small continuous linear PCM resampler for device-rate compatibility."""
class LinearResampler:
    def __init__(self, input_rate, output_rate):
        self.step = input_rate / output_rate
        self.position = 0.0
        self.received = 0
        self.previous = None

    def convert(self, pcm):
        import numpy as np
        samples = np.frombuffer(pcm, dtype=np.int16)
        if not len(samples):
            return b""
        start = self.received
        if self.previous is not None:
            samples = np.concatenate(([self.previous], samples))
            start -= 1
        end = start + len(samples) - 1
        count = max(0, int((end - self.position) / self.step + 1e-9) + 1)
        positions = self.position + np.arange(count) * self.step
        values = np.interp(positions - start, np.arange(len(samples)), samples)
        self.position += count * self.step
        self.received = end + 1
        self.previous = int(samples[-1])
        return np.clip(values, -32768, 32767).astype(np.int16).tobytes()
