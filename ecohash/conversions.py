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
    # ComfyUI IMAGE is [B, H, W, C]. These nodes send exactly one image per API call, so a
    # batch would have been silently narrowed to its first frame and the rest dropped with
    # no output and no warning. Fail loudly instead.
    if image.shape[0] != 1:
        raise ValueError(
            f"Expected a single image, got a batch of {image.shape[0]}. EcoHash image nodes "
            f"process one image per request; split the batch upstream (for example with a "
            f"'Image From Batch' node) and wire one image in."
        )
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
    # ComfyUI AUDIO waveform is [B, C, T]; same reasoning as image_tensor_to_png_bytes.
    if audio["waveform"].shape[0] != 1:
        raise ValueError(
            f"Expected a single audio clip, got a batch of {audio['waveform'].shape[0]}. "
            f"EcoHash audio nodes process one clip per request."
        )
    waveform = audio["waveform"][0]  # [C, T]
    arr = (waveform.cpu().numpy().clip(-1.0, 1.0) * 32767.0).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(arr.shape[0])
        w.setsampwidth(2)
        w.setframerate(int(audio["sample_rate"]))
        w.writeframes(arr.T.tobytes())
    return buf.getvalue()
