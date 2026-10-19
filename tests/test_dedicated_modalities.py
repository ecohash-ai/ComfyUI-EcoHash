from unittest.mock import patch

import pytest

from ecohash import client, connections
from ecohash_nodes import audio_nodes, image_nodes, llm_nodes
from tests.test_client import _mock_response
from tests.test_conversions import _wav_bytes

NODES = [image_nodes.EcoHashDedicatedImageGenerate, image_nodes.EcoHashDedicatedImageEdit,
         llm_nodes.EcoHashDedicatedLLM, llm_nodes.EcoHashDedicatedVLMDescribe,
         audio_nodes.EcoHashDedicatedTTS, audio_nodes.EcoHashDedicatedSTT]


@pytest.mark.parametrize("node", NODES)
def test_dedicated_schema_is_manual_and_connection_changes_invalidate_cache(node, monkeypatch):
    monkeypatch.setattr(llm_nodes.catalog, "model_ids", lambda *args: pytest.fail("Public catalog accessed"))
    schema = node.INPUT_TYPES()
    assert schema["required"]["model"][0] == "STRING"
    assert not ({"api_key", "base_url"} & schema["required"].keys())
    assert schema["optional"]["connection"][1]["default"] == "dedicated"
    connections.save_connection("studio", {"base_url": "https://private.example/v1", "api_key": "private-key"})
    original = node.IS_CHANGED(connection="studio")
    connections.save_connection("studio", {"api_key": "rotated-key"})
    assert node.IS_CHANGED(connection="studio") != original
    assert "not configured" in node.VALIDATE_INPUTS(connection="missing")


@pytest.mark.parametrize("mode", list(llm_nodes.MODE_PRESETS))
def test_dedicated_llm_modes_use_selected_endpoint(mode):
    connections.save_connection("studio", {"base_url": "https://private.example/custom/v1", "api_key": "private-key", "timeout": 456})
    with patch.object(client.requests, "request", return_value=_mock_response(payload={"choices": [{"message": {"content": "Answer"}}]})) as request:
        assert llm_nodes.EcoHashDedicatedLLM().run("private/model", mode, "hello", "Custom system", 0.5, 128, connection="studio") == ("Answer",)
    assert request.call_args.args == ("POST", "https://private.example/custom/v1/chat/completions")
    assert request.call_args.kwargs["timeout"] == 456
    assert request.call_args.kwargs["headers"] == {"Authorization": "Bearer private-key"}
    messages = request.call_args.kwargs["json"]["messages"]
    expected = "Custom system" if mode == "custom" else llm_nodes.MODE_PRESETS[mode]
    assert messages == ([{"role": "system", "content": expected}] if expected else []) + [{"role": "user", "content": "hello"}]


def test_missing_private_key_never_uses_public_credential(monkeypatch):
    monkeypatch.setenv("ECOHASH_API_KEY", "public-only")
    connections.save_connection("studio", {"base_url": "https://private.example/v1"})
    with patch.object(client.requests, "request") as request:
        with pytest.raises(client.EcoHashAuthError):
            llm_nodes.EcoHashDedicatedLLM().run("private", "chat", "hi", "", 0.7, 128, connection="studio")
        with pytest.raises(client.EcoHashAuthError):
            audio_nodes.EcoHashDedicatedTTS().speak("private", "hi", "speaker", 1, connection="studio")
    request.assert_not_called()


@pytest.mark.parametrize("payload", [
    {"choices": "invalid"}, {"choices": [{"message": "invalid"}]},
    {"choices": [{"message": {"content": {"unexpected": "value"}}}]},
    {"choices": [{"message": {"content": ""}, "finish_reason": "length"}]},
])
def test_malformed_completion_has_actionable_error(payload):
    with pytest.raises(client.EcoHashError):
        llm_nodes._first_message_content(payload)


def test_private_tts_uses_configured_timeout_and_requires_model_voice():
    connections.save_connection("studio", {"base_url": "https://private.example/v1", "api_key": "private-key", "timeout": 456})
    assert audio_nodes.EcoHashDedicatedTTS.INPUT_TYPES()["required"]["voice"][1]["default"] == ""
    with patch.object(client.requests, "request", return_value=_mock_response(content=_wav_bytes())) as request:
        audio_nodes.EcoHashDedicatedTTS().speak("private", "hi", "speaker-a", 1, connection="studio")
        assert request.call_args.kwargs["timeout"] == 456
        with pytest.raises(client.EcoHashError, match="voice ID"):
            audio_nodes.EcoHashDedicatedTTS().speak("private", "hi", "", 1, connection="studio")
        assert request.call_count == 1


def test_private_audio_rejects_async_invalid_wav_and_nontext_transcription():
    connections.save_connection("studio", {"base_url": "https://private.example/v1", "api_key": "private-key"})
    node = audio_nodes.EcoHashDedicatedTTS()
    with patch.object(client.requests, "request", return_value=_mock_response(202, content=b"job")):
        with pytest.raises(client.EcoHashError, match="task-polling"):
            node.speak("private", "hi", "speaker", 1, connection="studio")
    with patch.object(client.requests, "request", return_value=_mock_response(content=b"not audio")):
        with pytest.raises(client.EcoHashError, match="PCM WAV"):
            node.speak("private", "hi", "speaker", 1, connection="studio")
    with pytest.raises(client.EcoHashError, match="transcription"):
        audio_nodes._get_text({"text": ["wrong type"]})
