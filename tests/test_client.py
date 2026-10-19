import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from ecohash import client


def test_load_api_key_from_env(monkeypatch):
    monkeypatch.setenv("ECOHASH_API_KEY", "eco_env_key")
    assert client.load_api_key() == "eco_env_key"


def test_load_api_key_from_config(monkeypatch, tmp_path):
    monkeypatch.delenv("ECOHASH_API_KEY", raising=False)
    cfg = tmp_path / "config.ini"
    cfg.write_text("[ecohash]\napi_key = eco_cfg_key\n")
    monkeypatch.setattr(client, "CONFIG_PATH", cfg)
    assert client.load_api_key() == "eco_cfg_key"


def test_load_api_key_missing_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("ECOHASH_API_KEY", raising=False)
    monkeypatch.setattr(client, "CONFIG_PATH", tmp_path / "absent.ini")
    with pytest.raises(client.EcoHashAuthError, match="API key"):
        client.load_api_key()


def _mock_response(status=200, payload=None, content=b""):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = payload if payload is not None else {}
    resp.content = content
    resp.text = json.dumps(payload) if payload is not None else ""
    return resp


def test_request_json_sends_bearer_and_parses(monkeypatch):
    monkeypatch.setenv("ECOHASH_API_KEY", "eco_k")
    with patch.object(client.requests, "request") as mock_req:
        mock_req.return_value = _mock_response(200, {"ok": True})
        out = client.request_json("POST", "/chat/completions", json_body={"a": 1})
    assert out == {"ok": True}
    kwargs = mock_req.call_args.kwargs
    assert kwargs["headers"]["Authorization"] == "Bearer eco_k"
    assert mock_req.call_args.args == ("POST", "https://api.ecohash.com/v1/chat/completions")


@pytest.mark.parametrize("status,fragment", [(401, "Invalid EcoHash API key"), (402, "credit"), (429, "Rate limited")])
def test_request_json_maps_errors(monkeypatch, status, fragment):
    monkeypatch.setenv("ECOHASH_API_KEY", "eco_k")
    with patch.object(client.requests, "request") as mock_req:
        mock_req.return_value = _mock_response(status, {"error": "x"})
        with pytest.raises(client.EcoHashError, match=fragment):
            client.request_json("GET", "/models")


@pytest.mark.parametrize("payload", [
    {"detail": "size is unsupported; secret-key"},
    {"error": {"message": "size is unsupported; secret-key", "internal": "do not expose"}},
    {"detail": [{"msg": "size is unsupported; secret-key", "input": "do not expose"}]},
])
def test_dedicated_validation_errors_explain_failure_without_echoing_keys(payload):
    endpoint = client.DedicatedEndpoint("https://private.example/v1", "secret-key")
    with pytest.raises(client.EcoHashError, match="size is unsupported") as error:
        client._raise_for_status(_mock_response(400, payload), endpoint)
    assert "secret-key" not in str(error.value)
    assert "do not expose" not in str(error.value)


def test_request_bytes_returns_content(monkeypatch):
    monkeypatch.setenv("ECOHASH_API_KEY", "eco_k")
    with patch.object(client.requests, "request") as mock_req:
        mock_req.return_value = _mock_response(200, None, content=b"RIFFwav")
        out = client.request_bytes("POST", "/audio/speech", json_body={})
    assert out == b"RIFFwav"


def test_load_api_key_malformed_config(monkeypatch, tmp_path):
    monkeypatch.delenv("ECOHASH_API_KEY", raising=False)
    cfg = tmp_path / "config.ini"
    cfg.write_text("invalid line without section header\n[ecohash]\napi_key = key\n")
    monkeypatch.setattr(client, "CONFIG_PATH", cfg)
    with pytest.raises(client.EcoHashAuthError, match="config"):
        client.load_api_key()


def test_load_api_key_empty_env_falls_through_to_config(monkeypatch, tmp_path):
    monkeypatch.setenv("ECOHASH_API_KEY", "")
    cfg = tmp_path / "config.ini"
    cfg.write_text("[ecohash]\napi_key = eco_cfg_key\n")
    monkeypatch.setattr(client, "CONFIG_PATH", cfg)
    assert client.load_api_key() == "eco_cfg_key"


def test_load_api_key_rejects_placeholder(monkeypatch, tmp_path):
    monkeypatch.delenv("ECOHASH_API_KEY", raising=False)
    cfg = tmp_path / "config.ini"
    cfg.write_text("[ecohash]\napi_key = eco_YOUR_KEY_HERE\n")
    monkeypatch.setattr(client, "CONFIG_PATH", cfg)
    with pytest.raises(client.EcoHashAuthError, match="API key"):
        client.load_api_key()


def test_request_json_network_failure(monkeypatch):
    monkeypatch.setenv("ECOHASH_API_KEY", "eco_k")
    with patch.object(client.requests, "request") as mock_req:
        mock_req.side_effect = requests.exceptions.ConnectionError("boom")
        with pytest.raises(client.EcoHashError, match="Cannot reach EcoHash API"):
            client.request_json("GET", "/models")


def test_non_json_success_body_becomes_ecohash_error(monkeypatch):
    """A 2xx whose body isn't JSON must not leak requests' JSONDecodeError."""
    import pytest
    import requests
    from ecohash import client

    class FakeResp:
        status_code = 200
        text = ""
        content = b""

        def json(self):
            raise requests.exceptions.JSONDecodeError("Expecting value", "", 0)

    monkeypatch.setenv("ECOHASH_API_KEY", "eco_test")
    monkeypatch.setattr(client.requests, "request", lambda *a, **k: FakeResp())
    with pytest.raises(client.EcoHashError, match="not valid JSON"):
        client.request_json("POST", "/chat/completions", json_body={})


def test_public_validation_errors_redact_the_active_key(monkeypatch):
    monkeypatch.setenv("ECOHASH_API_KEY", "eco_private_key")
    response = _mock_response(400, {"error": {"message": "Unsupported size; eco_private_key", "request": "private prompt"}})
    monkeypatch.setattr(client.requests, "request", lambda *a, **k: response)
    with pytest.raises(client.EcoHashError, match="Unsupported size") as error:
        client.request_json("POST", "/images/generations", json_body={})
    assert "eco_private_key" not in str(error.value)
    assert "private prompt" not in str(error.value)


@pytest.mark.parametrize("failure", ["transport", "invalid_json", "html_error"])
def test_public_errors_never_echo_transport_or_raw_response_secrets(monkeypatch, failure):
    secret = "eco_private_key"
    monkeypatch.setenv("ECOHASH_API_KEY", secret)
    if failure == "transport":
        def request(*args, **kwargs):
            raise requests.exceptions.InvalidHeader(f"Authorization: Bearer {secret}")
    else:
        response = _mock_response(200 if failure == "invalid_json" else 500, content=secret.encode())
        response.text = secret
        response.json.side_effect = ValueError(secret)
        request = lambda *args, **kwargs: response
    monkeypatch.setattr(client.requests, "request", request)
    with pytest.raises(client.EcoHashError) as error:
        client.request_json("POST", "/chat/completions", json_body={})
    assert secret not in str(error.value)
    assert error.value.__suppress_context__ or failure == "html_error"
