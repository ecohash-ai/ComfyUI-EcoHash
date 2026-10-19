from unittest.mock import patch

import pytest
import requests

from ecohash import client
from ecohash_nodes import image_nodes
from tests.test_client import _mock_response
from tests.test_conversions import _png_b64


@pytest.fixture
def dedicated_env(monkeypatch):
    monkeypatch.setenv("ECOHASH_DEDICATED_BASE_URL", "https://dedicated.example/tenant/v1///")
    monkeypatch.setenv("ECOHASH_DEDICATED_API_KEY", "dedicated_secret")


def test_dedicated_env_overrides_file(monkeypatch, dedicated_env):
    client.CONFIG_PATH.write_text(
        "[dedicated]\nbase_url = https://file.example/v1\napi_key = file_key\ntimeout = 450\n"
    )
    monkeypatch.setenv("ECOHASH_DEDICATED_TIMEOUT", "600")
    endpoint = client.load_dedicated_endpoint()
    assert endpoint.base_url == "https://dedicated.example/tenant/v1"
    assert endpoint.api_key == "dedicated_secret"
    assert endpoint.timeout == 600
    assert endpoint.api_key not in repr(endpoint)


def test_dedicated_file_and_blank_env(monkeypatch):
    client.CONFIG_PATH.write_text(
        "[ecohash]\napi_key = public_secret\n"
        "[dedicated]\nbase_url = http://127.0.0.1:9000/custom/api/\napi_key = dedicated%key\n"
    )
    monkeypatch.setenv("ECOHASH_DEDICATED_API_KEY", "   ")
    endpoint = client.load_dedicated_endpoint()
    assert endpoint.base_url == "http://127.0.0.1:9000/custom/api"
    assert endpoint.api_key == "dedicated%key"
    assert endpoint.timeout == 300
    assert client.load_api_key() == "public_secret"


def test_missing_dedicated_url_does_not_use_public_default(monkeypatch):
    monkeypatch.setenv("ECOHASH_API_KEY", "public_secret")
    with pytest.raises(client.EcoHashError, match="ECOHASH_DEDICATED_BASE_URL"):
        client.load_dedicated_endpoint()


@pytest.mark.parametrize("key", ["", "YOUR_DEDICATED_KEY_HERE"])
def test_missing_dedicated_key_never_uses_public_key(monkeypatch, key):
    monkeypatch.setenv("ECOHASH_API_KEY", "public_secret")
    client.CONFIG_PATH.write_text(
        f"[ecohash]\napi_key = public_file_secret\n"
        f"[dedicated]\nbase_url = https://dedicated.example/v1\napi_key = {key}\n"
    )
    with patch.object(client.requests, "request") as request:
        with pytest.raises(client.EcoHashAuthError, match="ECOHASH_DEDICATED_API_KEY"):
            image_nodes.EcoHashDedicatedImageGenerate().generate("private/model", "p", "512x512", 0, -1)
    request.assert_not_called()


@pytest.mark.parametrize("url", [
    "dedicated.example/v1", "file:///tmp/image", "https:///v1",
    "https://user:secret@dedicated.example/v1", "https://dedicated.example:bad/v1",
    "https://dedicated.example/v1?token=secret", "https://dedicated.example/v1#fragment",
    "https://dedicated.example/bad path",
])
def test_invalid_dedicated_url_is_rejected(monkeypatch, dedicated_env, url):
    monkeypatch.setenv("ECOHASH_DEDICATED_BASE_URL", url)
    with pytest.raises(client.EcoHashError, match="Invalid base_url") as error:
        client.load_dedicated_endpoint()
    assert "secret" not in str(error.value)


@pytest.mark.parametrize("timeout", ["0", "-1", "nan", "inf", "bad"])
def test_invalid_timeout_is_rejected(monkeypatch, dedicated_env, timeout):
    monkeypatch.setenv("ECOHASH_DEDICATED_TIMEOUT", timeout)
    with pytest.raises(client.EcoHashError, match="positive number"):
        client.load_dedicated_endpoint()


def test_config_error_does_not_echo_secrets(dedicated_env):
    client.CONFIG_PATH.write_text("dedicated_secret_without_section\n")
    with pytest.raises(client.EcoHashError, match="config file") as error:
        client.load_dedicated_endpoint()
    assert "dedicated_secret" not in str(error.value)


def test_dedicated_request_uses_exact_prefix_key_and_timeout(monkeypatch, dedicated_env):
    monkeypatch.setenv("ECOHASH_API_KEY", "public_secret")
    endpoint = client.load_dedicated_endpoint()
    with patch.object(client.requests, "request", return_value=_mock_response(payload={"ok": True})) as request:
        assert client.request_json("POST", "/images/generations", json_body={"model": "private/model"}, endpoint=endpoint) == {"ok": True}
    assert request.call_args.args == ("POST", "https://dedicated.example/tenant/v1/images/generations")
    assert request.call_args.kwargs["headers"] == {"Authorization": "Bearer dedicated_secret"}
    assert request.call_args.kwargs["timeout"] == 300
    assert request.call_args.kwargs["allow_redirects"] is False


@pytest.mark.parametrize("status,fragment", [
    (301, "redirected"), (401, "authentication failed"), (403, "access denied"),
    (404, "deployed model ID"), (429, "rate limited"), (503, "503"),
])
def test_dedicated_errors_do_not_point_to_public_billing(dedicated_env, status, fragment):
    endpoint = client.load_dedicated_endpoint()
    with patch.object(client.requests, "request", return_value=_mock_response(status, {"error": "dedicated_secret"})):
        with pytest.raises(client.EcoHashError, match=fragment) as error:
            client.request_json("POST", "/images/generations", json_body={}, endpoint=endpoint)
    assert "dedicated_secret" not in str(error.value)
    assert "ecohash.com/billing" not in str(error.value)


def test_dedicated_timeout_is_actionable_and_does_not_echo_credentials(dedicated_env):
    endpoint = client.load_dedicated_endpoint()
    with patch.object(client.requests, "request", side_effect=requests.Timeout("dedicated_secret")):
        with pytest.raises(client.EcoHashError, match="Timeout") as error:
            client.request_json("POST", "/images/generations", endpoint=endpoint)
    assert "dedicated_secret" not in str(error.value)


def test_dedicated_non_json_and_async_responses_are_actionable(dedicated_env):
    endpoint = client.load_dedicated_endpoint()
    response = _mock_response()
    response.json.side_effect = ValueError("dedicated_secret")
    with patch.object(client.requests, "request", return_value=response):
        with pytest.raises(client.EcoHashError, match="not valid JSON") as error:
            client.request_json("POST", "/images/generations", endpoint=endpoint)
    assert "dedicated_secret" not in str(error.value)
    with patch.object(client.requests, "request", return_value=_mock_response(202, {"id": "job"})):
        with pytest.raises(client.EcoHashError, match="task-polling adapter"):
            client.request_json("POST", "/images/generations", endpoint=endpoint)


def test_dedicated_schema_needs_no_public_catalog(monkeypatch):
    def unavailable(*args, **kwargs):
        raise AssertionError("dedicated nodes must not access the public catalog")

    monkeypatch.setattr(image_nodes.catalog, "model_ids", unavailable)
    monkeypatch.setattr(image_nodes.catalog, "models_where", unavailable)
    for node in (image_nodes.EcoHashDedicatedImageGenerate, image_nodes.EcoHashDedicatedImageEdit):
        schema = node.INPUT_TYPES()["required"]
        assert schema["model"][0] == "STRING"
        assert not ({"api_key", "base_url"} & schema.keys())


def test_dedicated_nodes_use_private_model_ids(dedicated_env):
    generate = image_nodes.EcoHashDedicatedImageGenerate()
    edit = image_nodes.EcoHashDedicatedImageEdit()
    with patch.object(client.requests, "request", return_value=_mock_response(payload={"data": [{"b64_json": _png_b64()}]})) as request:
        (image,) = generate.generate(" private/custom-model ", "p", "512x512", 8, 42)
        assert request.call_args.kwargs["json"]["model"] == "private/custom-model"
        assert request.call_args.kwargs["json"]["seed"] == 42
        assert request.call_args.kwargs["json"]["steps"] == 8
        (edited,) = edit.edit(image, "private/custom-edit", "edit p", "auto")
        assert request.call_args.kwargs["data"]["model"] == "private/custom-edit"
        assert request.call_args.kwargs["data"]["size"] == f"{image.shape[2]}x{image.shape[1]}"
        assert request.call_args.kwargs["files"]["image"][2] == "image/png"
    assert image.shape == edited.shape


def test_blank_private_model_fails_before_network(dedicated_env):
    with patch.object(client.requests, "request") as request:
        with pytest.raises(client.EcoHashError, match="deployed model ID"):
            image_nodes.EcoHashDedicatedImageGenerate().generate("  ", "p", "512x512", 0, -1)
    request.assert_not_called()


@pytest.mark.parametrize("payload", [
    {"data": []}, {"data": "bad"}, {"data": [None]}, {"data": [{"b64_json": "bad"}]},
    {"data": [{"url": "file:///private/image"}]}, {"data": [{"url": 123}]},
])
def test_invalid_image_response_has_node_error(dedicated_env, payload):
    with patch.object(client.requests, "request", return_value=_mock_response(payload=payload)):
        with pytest.raises(client.EcoHashError):
            image_nodes.EcoHashDedicatedImageGenerate().generate("private/model", "p", "512x512", 0, -1)


def test_download_image_never_sends_inference_key(monkeypatch, dedicated_env):
    monkeypatch.setenv("ECOHASH_API_KEY", "public_secret")
    with patch.object(client.requests, "get", return_value=_mock_response(content=b"image")) as get:
        assert client.download_image("https://images.example/result.png?signature=abc") == b"image"
    assert "headers" not in get.call_args.kwargs
    assert "auth" not in get.call_args.kwargs


def test_endpoint_settings_invalidate_cached_images(monkeypatch, dedicated_env):
    generate = image_nodes.EcoHashDedicatedImageGenerate
    edit = image_nodes.EcoHashDedicatedImageEdit
    original = generate.IS_CHANGED()
    assert original == generate.IS_CHANGED() == edit.IS_CHANGED()
    assert "dedicated_secret" not in original
    monkeypatch.setenv("ECOHASH_DEDICATED_BASE_URL", "https://another.example/v1")
    changed_url = generate.IS_CHANGED()
    assert changed_url != original
    monkeypatch.setenv("ECOHASH_DEDICATED_API_KEY", "rotated_secret")
    assert generate.IS_CHANGED() != changed_url
