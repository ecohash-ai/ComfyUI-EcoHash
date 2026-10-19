"""One EcoHash account credential, with independent credentials for other origins."""

import asyncio
import json
from unittest.mock import patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
import pytest

from ecohash import api_routes, client, connections, discovery
from ecohash_nodes.dedicated import DedicatedNode, PublicNode
from tests.test_client import _mock_response


@pytest.mark.parametrize("url", ["https://api.ecohash.com/v1", "https://API.ECOHASH.COM:443/inference-instances/999/proxy/v1"])
def test_official_connections_reference_the_single_global_credential(url):
    connections.save_connection("public", {"api_key": "global-key"})
    profile = connections.save_connection("studio", {"name": "My instance", "base_url": url})
    assert profile["configured"] and profile["uses_global_key"]
    assert profile["sources"]["api_key"] == "global"
    assert connections.resolve("studio").api_key == "global-key"
    assert "api_key" not in connections._store()["studio"]
    assert "global-key" not in json.dumps(connections.list_connections())


@pytest.mark.parametrize("url", ["http://api.ecohash.com/v1", "https://api.ecohash.com:8443/v1",
    "https://api.ecohash.com.evil.example/v1", "https://other.ecohash.com/v1", "https://third.example/api.ecohash.com/v1"])
def test_other_origins_never_inherit_the_global_credential(url):
    connections.save_connection("public", {"api_key": "global-key"})
    profile = connections.save_connection("studio", {"base_url": url})
    assert not profile["configured"] and not profile["uses_global_key"]
    with patch.object(client.requests, "request") as request:
        with pytest.raises(client.EcoHashAuthError):
            connections.resolve("studio")
    request.assert_not_called()
    connections.save_connection("studio", {"api_key": "endpoint-key"})
    assert connections.resolve("studio").api_key == "endpoint-key"


def test_official_connections_do_not_accept_a_per_connection_key():
    with pytest.raises(client.EcoHashError, match="global API Key"):
        connections.save_connection("studio", {"base_url": "https://api.ecohash.com/v1", "api_key": "per-endpoint-key"})
    assert not connections.CONNECTIONS_PATH.exists()


def test_missing_global_key_points_to_global_settings_and_does_not_submit(monkeypatch):
    monkeypatch.setenv("ECOHASH_DEDICATED_BASE_URL", "https://api.ecohash.com/inference-instances/999/proxy/v1")
    monkeypatch.setenv("ECOHASH_DEDICATED_API_KEY", "ignored-per-endpoint-key")
    with patch.object(client.requests, "request") as request:
        with pytest.raises(client.EcoHashAuthError, match="global EcoHash API Key"):
            connections.resolve("dedicated")
    request.assert_not_called()


def test_global_precedence_applies_to_every_official_connection(monkeypatch):
    client.CONFIG_PATH.write_text("[ecohash]\napi_key=ini-global\n[dedicated]\nbase_url=https://api.ecohash.com/v1\n")
    connections.save_connection("studio", {"base_url": "https://api.ecohash.com/inference-instances/999/proxy/v1"})
    for value, setter in [("ini-global", lambda: None),
                          ("saved-global", lambda: connections.save_connection("public", {"api_key": "saved-global"})),
                          ("env-global", lambda: monkeypatch.setenv("ECOHASH_API_KEY", "env-global"))]:
        setter()
        assert client.load_api_key() == value
        assert connections.resolve("dedicated").api_key == value
        assert connections.resolve("studio").api_key == value


def test_switching_origin_requires_its_own_key_without_copying_global_credentials():
    connections.save_connection("public", {"api_key": "global-key"})
    connections.save_connection("studio", {"base_url": "https://api.ecohash.com/v1"})
    changed = connections.save_connection("studio", {"base_url": "https://third.example/v1"})
    assert not changed["configured"] and not changed["has_api_key"]
    connections.save_connection("studio", {"api_key": "independent-key"})
    changed = connections.save_connection("studio", {"base_url": "https://api.ecohash.com/v1"})
    assert changed["uses_global_key"] and connections.resolve("studio").api_key == "global-key"
    assert "api_key" not in connections._store()["studio"]


def test_rotation_invalidates_shared_model_and_node_caches_but_keeps_third_party_independent():
    connections.save_connection("public", {"api_key": "first-global"})
    connections.save_connection("studio", {"base_url": "https://api.ecohash.com/inference-instances/999/proxy/v1"})
    connections.save_connection("third", {"base_url": "https://third.example/v1", "api_key": "third-key"})
    before = [PublicNode.IS_CHANGED(), DedicatedNode.IS_CHANGED(connection="studio"), DedicatedNode.IS_CHANGED(connection="third")]
    with patch.object(client.requests, "request", return_value=_mock_response(payload={"data": [{"id": "model"}]})) as request:
        discovery.models("studio")
        discovery.models("third")
        connections.save_connection("public", {"api_key": "second-global"})
        discovery.models("studio")
        discovery.models("third")
    after = [PublicNode.IS_CHANGED(), DedicatedNode.IS_CHANGED(connection="studio"), DedicatedNode.IS_CHANGED(connection="third")]
    assert before[0] != after[0] and before[1] != after[1] and before[2] == after[2]
    assert "second-global" not in json.dumps(after)
    assert [call.kwargs["headers"]["Authorization"] for call in request.call_args_list] == ["Bearer first-global", "Bearer third-key", "Bearer second-global"]


def test_all_public_and_dedicated_node_types_use_credential_cache_signatures():
    import __init__ as plugin
    connections.save_connection("public", {"api_key": "global-key"})
    connections.save_connection("studio", {"base_url": "https://api.ecohash.com/v1"})
    before = {name: node.IS_CHANGED(connection="studio") for name, node in plugin.NODE_CLASS_MAPPINGS.items()}
    connections.save_connection("public", {"api_key": "rotated-global"})
    for name, node in plugin.NODE_CLASS_MAPPINGS.items():
        assert before[name] != node.IS_CHANGED(connection="studio")
        assert not {"api_key", "base_url"} & (node.INPUT_TYPES()["required"] | node.INPUT_TYPES().get("optional", {})).keys()


def test_official_authentication_error_identifies_global_key_settings():
    endpoint = client.DedicatedEndpoint("https://api.ecohash.com/inference-instances/999/proxy/v1", "global-key")
    with pytest.raises(client.EcoHashAuthError, match="global EcoHash API Key") as error:
        client._raise_for_status(_mock_response(401), endpoint)
    assert "global-key" not in str(error.value)


def test_settings_api_saves_one_key_and_multiple_official_endpoints_without_echoing_secrets():
    async def run():
        routes = web.RouteTableDef()
        api_routes.register_routes(routes)
        app = web.Application()
        app.add_routes(routes)
        async with TestClient(TestServer(app)) as browser:
            headers = {"X-EcoHash-Settings": "1"}
            denied = await browser.put("/ecohash/connections/public", json={"api_key": "global-key"})
            assert denied.status == 403
            response = await browser.put("/ecohash/connections/public", json={"api_key": "global-key"}, headers=headers)
            assert response.status == 200 and "global-key" not in await response.text()
            for name in ("image", "language", "video"):
                response = await browser.put("/ecohash/connections/" + name,
                    json={"base_url": f"https://api.ecohash.com/inference-instances/{name}/proxy/v1"}, headers=headers)
                assert response.status == 200 and (await response.json())["uses_global_key"]
            response = await browser.get("/ecohash/connections")
            assert "global-key" not in await response.text()
            assert response.headers["Cache-Control"] == "no-store"
            with patch.object(client.requests, "request", return_value=_mock_response(payload={"data": []})) as request:
                for name in ("public", "image", "language", "video"):
                    response = await browser.post(f"/ecohash/connections/{name}/test", json={}, headers=headers)
                    assert response.status == 200
                assert all(call.args[0] == "GET" and call.kwargs["headers"]["Authorization"] == "Bearer global-key" for call in request.call_args_list)
            store = connections._store()
            assert [name for name, profile in store.items() if "api_key" in profile] == ["public"]
    asyncio.run(run())
