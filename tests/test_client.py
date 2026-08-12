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
