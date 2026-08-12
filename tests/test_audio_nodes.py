from unittest.mock import patch

import pytest

from ecohash_nodes import audio_nodes
from tests.test_conversions import _wav_bytes


@pytest.fixture(autouse=True)
def fake_catalog(monkeypatch):
    monkeypatch.setattr(audio_nodes.catalog, "model_ids", lambda *c: ["kokoro-82m"])


def test_tts_requests_wav_and_returns_audio():
    node = audio_nodes.EcoHashTTS()
    with patch.object(audio_nodes.client, "request_bytes") as mock_req:
        mock_req.return_value = _wav_bytes()
        (audio,) = node.speak(model="kokoro-82m", text="hello", voice="af_bella", speed=1.0)
    assert audio["sample_rate"] == 16000 and audio["waveform"].shape[0] == 1
    body = mock_req.call_args.kwargs["json_body"]
    assert body == {"model": "kokoro-82m", "input": "hello", "voice": "af_bella",
                    "response_format": "wav", "speed": 1.0}
    assert mock_req.call_args.args == ("POST", "/audio/speech")


def test_stt_sends_multipart_and_returns_text():
    from ecohash import conversions
    node = audio_nodes.EcoHashSTT()
    audio = conversions.wav_bytes_to_audio(_wav_bytes())
    with patch.object(audio_nodes.client, "request_json") as mock_req:
        mock_req.return_value = {"text": "hello world"}
        (text,) = node.transcribe(audio=audio, model="kokoro-82m", language="")
    assert text == "hello world"
    kwargs = mock_req.call_args.kwargs
    assert kwargs["data"] == {"model": "kokoro-82m"}  # empty language omitted
    assert kwargs["files"]["file"][0] == "audio.wav"


def test_stt_passes_language_when_set():
    from ecohash import conversions
    node = audio_nodes.EcoHashSTT()
    audio = conversions.wav_bytes_to_audio(_wav_bytes())
    with patch.object(audio_nodes.client, "request_json") as mock_req:
        mock_req.return_value = {"text": "x"}
        node.transcribe(audio=audio, model="kokoro-82m", language="zh")
    assert mock_req.call_args.kwargs["data"]["language"] == "zh"


def test_stt_missing_text_in_response_raises_error():
    """Guard: STT response without 'text' field should raise EcoHashError"""
    from ecohash import conversions
    from ecohash.client import EcoHashError

    node = audio_nodes.EcoHashSTT()
    audio = conversions.wav_bytes_to_audio(_wav_bytes())
    with patch.object(audio_nodes.client, "request_json") as mock_req:
        mock_req.return_value = {"ok": 1}  # Missing 'text' field
        with pytest.raises(EcoHashError, match="no transcription"):
            node.transcribe(audio=audio, model="kokoro-82m", language="")
