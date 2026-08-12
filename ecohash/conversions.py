"""Converters between ComfyUI tensor formats and EcoHash API byte formats."""

import base64
import io
import wave

import numpy as np
import torch
from PIL import Image


def b64_to_image_tensor(b64: str) -> torch.Tensor:
    img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
    arr = np.asarray(img).astype(np.float32) / 255.0
    return torch.from_numpy(arr)[None,]


def image_tensor_to_png_bytes(image: torch.Tensor) -> bytes:
    arr = (image[0].cpu().numpy().clip(0.0, 1.0) * 255.0).round().astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def wav_bytes_to_audio(wav_bytes: bytes) -> dict:
    with wave.open(io.BytesIO(wav_bytes), "rb") as w:
        channels, sampwidth, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
        frames = w.readframes(w.getnframes())
    if sampwidth != 2:
        raise ValueError(f"Expected 16-bit WAV from EcoHash, got sample width {sampwidth}")
    arr = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    arr = arr.reshape(-1, channels).T  # [C, T]
    return {"waveform": torch.from_numpy(arr.copy())[None,], "sample_rate": rate}


def audio_to_wav_bytes(audio: dict) -> bytes:
    waveform = audio["waveform"][0]  # [C, T]
    arr = (waveform.cpu().numpy().clip(-1.0, 1.0) * 32767.0).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(arr.shape[0])
        w.setsampwidth(2)
        w.setframerate(int(audio["sample_rate"]))
        w.writeframes(arr.T.tobytes())
    return buf.getvalue()
