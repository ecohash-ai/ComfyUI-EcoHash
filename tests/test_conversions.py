import base64
import io
import struct
import wave

import numpy as np
import pytest
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


def test_wav_non_16bit_raises_error():
    # Build 8-bit WAV (sampwidth=1) - should raise ValueError
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)  # 8-bit, not 16-bit
        w.setframerate(16000)
        w.writeframes(struct.pack("<" + "B" * 8, *([128] * 8)))
    wav_8bit = buf.getvalue()

    with pytest.raises(ValueError, match="16-bit"):
        conversions.wav_bytes_to_audio(wav_8bit)


def test_wav_stereo_deinterleave_and_roundtrip():
    # Build stereo WAV with L=1000, R=-2000, interleaved
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(16000)
        # 4 frames: (L,R) = (1000,-2000), (1000,-2000), (1000,-2000), (1000,-2000)
        w.writeframes(struct.pack("<8h", 1000, -2000, 1000, -2000, 1000, -2000, 1000, -2000))
    wav_stereo = buf.getvalue()

    audio = conversions.wav_bytes_to_audio(wav_stereo)
    assert audio["waveform"].shape == (1, 2, 4)
    assert audio["sample_rate"] == 16000
    assert abs(float(audio["waveform"][0, 0, 0]) - 1000 / 32768) < 1e-4
    assert abs(float(audio["waveform"][0, 1, 0]) - (-2000 / 32768)) < 1e-4

    # Roundtrip
    wav2 = conversions.audio_to_wav_bytes(audio)
    audio2 = conversions.wav_bytes_to_audio(wav2)
    assert torch.allclose(audio["waveform"], audio2["waveform"], atol=1e-3)
