import base64
from unittest.mock import patch

import pytest

from ecohash_nodes import llm_nodes
from tests.test_conversions import _png_b64


@pytest.fixture(autouse=True)
def fake_catalog(monkeypatch):
    monkeypatch.setattr(llm_nodes.catalog, "model_ids", lambda *c: ["glm-5.2"])


def _chat_response(text="OUT"):
    return {"choices": [{"message": {"content": text}}]}


def test_llm_chat_mode_no_system():
    node = llm_nodes.EcoHashLLM()
    with patch.object(llm_nodes.client, "request_json") as mock_req:
        mock_req.return_value = _chat_response("hi")
        (out,) = node.run(model="glm-5.2", mode="chat", text="hello",
                          system_prompt="", temperature=0.7, max_tokens=1024)
    assert out == "hi"
    msgs = mock_req.call_args.kwargs["json_body"]["messages"]
    assert msgs == [{"role": "user", "content": "hello"}]


def test_llm_prompt_enhance_injects_preset_system():
    node = llm_nodes.EcoHashLLM()
    with patch.object(llm_nodes.client, "request_json") as mock_req:
        mock_req.return_value = _chat_response()
        node.run(model="glm-5.2", mode="prompt_enhance", text="a cat",
                 system_prompt="", temperature=0.7, max_tokens=1024)
    msgs = mock_req.call_args.kwargs["json_body"]["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == llm_nodes.MODE_PRESETS["prompt_enhance"]


def test_llm_custom_mode_uses_user_system_prompt():
    node = llm_nodes.EcoHashLLM()
    with patch.object(llm_nodes.client, "request_json") as mock_req:
        mock_req.return_value = _chat_response()
        node.run(model="glm-5.2", mode="custom", text="x",
                 system_prompt="You are a pirate.", temperature=0.2, max_tokens=64)
    body = mock_req.call_args.kwargs["json_body"]
    assert body["messages"][0] == {"role": "system", "content": "You are a pirate."}
    assert body["temperature"] == 0.2 and body["max_tokens"] == 64


def test_vlm_describe_sends_data_url():
    from ecohash import conversions
    node = llm_nodes.EcoHashVLMDescribe()
    img = conversions.b64_to_image_tensor(_png_b64())
    with patch.object(llm_nodes.client, "request_json") as mock_req:
        mock_req.return_value = _chat_response("a red image")
        (out,) = node.describe(image=img, model="glm-5.2",
                               prompt="Describe this image.", max_tokens=512)
    assert out == "a red image"
    content = mock_req.call_args.kwargs["json_body"]["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "Describe this image."}
    url = content[1]["image_url"]["url"]
    assert url.startswith("data:image/png;base64,")
    base64.b64decode(url.split(",", 1)[1])  # must be valid base64


def test_llm_raises_on_empty_choices():
    from ecohash.client import EcoHashError
    node = llm_nodes.EcoHashLLM()
    with patch.object(llm_nodes.client, "request_json") as mock_req:
        mock_req.return_value = {"choices": []}
        with pytest.raises(EcoHashError, match="no completion"):
            node.run(model="glm-5.2", mode="chat", text="hello",
                     system_prompt="", temperature=0.7, max_tokens=1024)


def test_vlm_describe_raises_on_empty_choices():
    from ecohash import conversions
    from ecohash.client import EcoHashError
    node = llm_nodes.EcoHashVLMDescribe()
    img = conversions.b64_to_image_tensor(_png_b64())
    with patch.object(llm_nodes.client, "request_json") as mock_req:
        mock_req.return_value = {"choices": []}
        with pytest.raises(EcoHashError, match="no completion"):
            node.describe(image=img, model="glm-5.2",
                          prompt="Describe this image.", max_tokens=512)
