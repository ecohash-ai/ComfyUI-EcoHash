import json
import stat
from unittest.mock import patch

import pytest

from ecohash import client, connections, discovery
from ecohash_nodes import image_nodes
from tests.test_client import _mock_response
from tests.test_conversions import _png_b64


def save(name="studio", **kwargs):
    return connections.save_connection(name, {"name": name, "base_url": "https://private.example/v1", "api_key": "private-secret", **kwargs})


def test_named_profiles_persist_redacted_and_private():
    profile = save()
    assert profile["configured"] is True
    assert "private-secret" not in json.dumps(profile)
    assert connections.resolve("studio").api_key == "private-secret"
    assert stat.S_IMODE(connections.CONNECTIONS_PATH.stat().st_mode) == 0o600
    assert connections.connection_ids() == ["public", "dedicated", "studio"]
    assert connections.connection_ids(dedicated_only=True) == ["dedicated", "studio"]


def test_blank_key_keeps_secret_and_renaming_keeps_id():
    save()
    connections.save_connection("studio", {"name": "New display name", "api_key": "", "timeout": 60})
    assert connections.resolve("studio").api_key == "private-secret"
    assert connections.summary("studio")["name"] == "New display name"
    assert connections.resolve("studio").timeout == 60


@pytest.mark.parametrize("suffix", ["images/generations", "images/edits", "chat/completions", "audio/speech", "audio/transcriptions", "video/generations", "videos"])
def test_copied_operation_urls_are_normalized_to_the_existing_api_prefix(suffix):
    save(base_url=f"https://private.example/tenant/v1/{suffix}/")
    assert connections.resolve("studio").base_url == "https://private.example/tenant/v1"


def test_unconfigured_connection_is_reported_before_execution():
    node = image_nodes.EcoHashDedicatedImageGenerate
    assert node.IS_CHANGED(connection="dedicated") == "unconfigured:dedicated"
    assert "Select your saved connection" in node.VALIDATE_INPUTS(connection="dedicated")
    save("dedicated")
    assert node.VALIDATE_INPUTS(connection="dedicated") is True
    assert node.IS_CHANGED(connection="dedicated") != "unconfigured:dedicated"


@pytest.mark.parametrize("model_id", ["MiniMaxAI/MiniMax-H3:247", "seedance-next", "wan3-next", "ltx-next"])
def test_discovery_never_guesses_capabilities_from_model_names(model_id):
    assert discovery._normalize_model({"id": model_id}) == {"id": model_id, "name": model_id}
    declared = discovery._normalize_model({"id": model_id, "category": "video", "video_max_duration_seconds": 30,
        "supported_resolutions": ["1440p"], "openai_compatible": True})
    assert declared["category"] == "video"
    assert declared["video_max_duration_seconds"] == 30
    assert declared["supported_resolutions"] == ["1440p"]
    assert declared["openai_compatible"] is True


def test_settings_override_ini_and_environment_overrides_settings(monkeypatch):
    client.CONFIG_PATH.write_text("[ecohash]\napi_key=ini-public\n[dedicated]\nbase_url=https://ini.example/v1\napi_key=ini-dedicated\n")
    connections.save_connection("public", {"api_key": "ui-public"})
    save("dedicated")
    assert client.load_api_key() == "ui-public"
    assert client.load_dedicated_endpoint().api_key == "private-secret"
    monkeypatch.setenv("ECOHASH_API_KEY", "env-public")
    monkeypatch.setenv("ECOHASH_DEDICATED_API_KEY", "env-dedicated")
    assert client.load_api_key() == "env-public"
    assert client.load_dedicated_endpoint().api_key == "env-dedicated"
    assert connections.summary("dedicated")["sources"]["api_key"] == "environment"


def test_ini_named_connection_can_be_used_without_settings_file():
    client.CONFIG_PATH.write_text("[connection:production]\nname=Production\nbase_url=https://prod.example/api\napi_key=ini-secret\n")
    assert "production" in connections.connection_ids()
    assert connections.resolve("production").base_url == "https://prod.example/api"
    assert not connections.summary("production")["can_delete"]
    with pytest.raises(client.EcoHashError, match="config.ini"):
        connections.delete_connection("production")


@pytest.mark.parametrize("name", ["", "../config", "has space", "a" * 65])
def test_invalid_connection_id_does_not_write(name):
    with pytest.raises(client.EcoHashError, match="connection ID"):
        save(name)
    assert not connections.CONNECTIONS_PATH.exists()


def test_public_destination_is_fixed_and_key_does_not_fall_back():
    with pytest.raises(client.EcoHashError, match="fixed"):
        save("public")
    connections.save_connection("public", {"api_key": "public-secret"})
    assert client.load_api_key() == "public-secret"
    save("no-key", api_key="")
    with pytest.raises(client.EcoHashAuthError, match="API key not found"):
        connections.resolve("no-key")


def test_missing_workflow_alias_has_mapping_error_and_no_fallback():
    save()
    assert "Open EcoHash connections" in image_nodes.EcoHashDedicatedImageGenerate.VALIDATE_INPUTS(connection="missing")
    with pytest.raises(client.EcoHashError, match="not configured"):
        client.load_dedicated_endpoint("missing")


def test_profiles_route_nodes_and_invalidate_cache_independently():
    save("first", base_url="https://first.example/v1", api_key="first-key")
    save("second", base_url="https://second.example/custom", api_key="second-key")
    node = image_nodes.EcoHashDedicatedImageGenerate()
    first_hash = node.IS_CHANGED(connection="first")
    assert first_hash != node.IS_CHANGED(connection="second")
    with patch.object(client.requests, "request", return_value=_mock_response(payload={"data": [{"b64_json": _png_b64()}]})) as request:
        for name in ("first", "second"):
            node.generate("private/model", "p", "512x512", 0, 42, connection=name)
        assert [call.args[1] for call in request.call_args_list] == ["https://first.example/v1/images/generations", "https://second.example/custom/images/generations"]
        assert [call.kwargs["headers"]["Authorization"] for call in request.call_args_list] == ["Bearer first-key", "Bearer second-key"]
    connections.save_connection("second", {"api_key": "changed"})
    assert node.IS_CHANGED(connection="first") == first_hash


def test_delete_named_profile_preserves_others():
    save("first")
    save("second")
    connections.delete_connection("first")
    assert "first" not in connections.connection_ids()
    assert "second" in connections.connection_ids()
    with pytest.raises(client.EcoHashError, match="Built-in"):
        connections.delete_connection("dedicated")


def test_corrupt_store_does_not_echo_secret():
    connections.CONNECTIONS_PATH.write_text('{"api_key": "private-secret"')
    with pytest.raises(client.EcoHashError) as error:
        connections.list_connections()
    assert "private-secret" not in str(error.value)


def test_discovery_understands_openai_models_and_metadata():
    save()
    response = _mock_response(payload={"data": [
        {"id": "image-private", "category": "image", "supports_image_edit": True, "internal_secret": "ignore"},
        {"id": "speech", "voices": ["voice-a", "voice-b"]}, None,
    ]})
    with patch.object(client.requests, "request", return_value=response) as request:
        first = discovery.models("studio")
        second = discovery.models("studio")
    assert first["models"][0] == {"id": "image-private", "name": "image-private", "category": "image", "supports_image_edit": True}
    assert second["source"] == "cache"
    request.assert_called_once()
    assert request.call_args.kwargs["params"] == {"category": "all"}
    assert request.call_args.args == ("GET", "https://private.example/v1/models")


def test_discovery_cache_changes_when_credentials_change():
    save()
    with patch.object(client.requests, "request", return_value=_mock_response(payload={"data": [{"id": "m"}]})) as request:
        discovery.models("studio")
        connections.save_connection("studio", {"api_key": "new-key"})
        discovery.models("studio")
    assert request.call_count == 2


def test_discovery_ignores_malformed_optional_capabilities():
    model = discovery._normalize_model({"id": "private", "display_name": {}, "category": [],
        "supports_image_edit": "false", "default_image_steps": True,
        "input_modalities": "image", "output_modalities": ["text", None], "voices": {"secret": "ignored"}})
    assert model == {"id": "private", "name": "private", "output_modalities": ["text"]}


def test_connection_test_does_not_generate_or_overclaim_404():
    save()
    with patch.object(client.requests, "request", return_value=_mock_response(404)) as request:
        result = discovery.test_connection("studio")
    assert result["status"] == "reachable"
    assert "not verified" in result["message"]
    assert request.call_args.args == ("GET", "https://private.example/v1/models")


def test_connection_test_reports_invalid_key():
    save()
    with patch.object(client.requests, "request", return_value=_mock_response(401)):
        with pytest.raises(client.EcoHashAuthError, match="authentication failed"):
            discovery.test_connection("studio")


def test_custom_dimensions_are_validated_before_requests():
    save()
    node = image_nodes.EcoHashDedicatedImageGenerate()
    with patch.object(client.requests, "request", return_value=_mock_response(payload={"data": [{"b64_json": _png_b64()}]})) as request:
        node.generate("private", "p", "custom", 0, 1, width=1280, height=720, connection="studio")
        assert request.call_args.kwargs["json"]["size"] == "1280x720"
        with pytest.raises(client.EcoHashError, match="multiples of 16"):
            node.generate("private", "p", "custom", 0, 1, width=1281, connection="studio")
        assert request.call_count == 1


def test_catalog_schema_is_offline_and_stale_cache_backs_off(monkeypatch):
    from ecohash import catalog

    catalog._CACHE.update({"data": None, "ts": 0.0})
    with patch.object(catalog.requests, "get", side_effect=OSError("offline")) as get:
        assert catalog.model_ids("image")
        get.assert_not_called()
        assert catalog.get_catalog(force_refresh=True)
        assert catalog.get_catalog()
        assert get.call_count == 1
        assert catalog.status()["source"] == "snapshot"
