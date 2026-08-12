import base64
import io
import struct
import wave

import numpy as np
import torch
from PIL import Image

from ecohash import conversions


def _png_b64(w=4, h=2):
    img = Image.new("RGB", (w, h), (255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _wav_bytes(n=8, rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack("<" + "h" * n, *([1000] * n)))
    return buf.getvalue()


def test_b64_roundtrip_shape_and_range():
    t = conversions.b64_to_image_tensor(_png_b64())
    assert t.shape == (1, 2, 4, 3) and t.dtype == torch.float32
    assert float(t.max()) <= 1.0 and float(t[0, 0, 0, 0]) > 0.99  # red channel

def test_tensor_to_png_roundtrip():
    t = conversions.b64_to_image_tensor(_png_b64())
    png = conversions.image_tensor_to_png_bytes(t)
    img = Image.open(io.BytesIO(png))
    assert img.size == (4, 2)


def test_wav_to_audio_and_back():
    audio = conversions.wav_bytes_to_audio(_wav_bytes())
    assert audio["sample_rate"] == 16000
    assert audio["waveform"].shape == (1, 1, 8)
    assert abs(float(audio["waveform"][0, 0, 0]) - 1000 / 32768) < 1e-4
    wav2 = conversions.audio_to_wav_bytes(audio)
    audio2 = conversions.wav_bytes_to_audio(wav2)
    assert torch.allclose(audio["waveform"], audio2["waveform"], atol=1e-3)
