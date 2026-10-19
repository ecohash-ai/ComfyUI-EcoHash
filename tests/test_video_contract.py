"""Deployment-owned request mappings; model names never choose an adapter."""

import json
from unittest.mock import Mock

import pytest

from ecohash import client, connections, discovery, video_contract


@pytest.fixture
def mapped_service():
    endpoint = client.DedicatedEndpoint("https://private.example/v1", "private-key", 5, "studio")
    model = "arbitrary/model-v2"
    contract = {
        "base_url": endpoint.base_url,
        "requires": {"pipeline_class": "ExamplePipeline"},
        "capabilities": {"category": "video", "input_modalities": ["text"],
                         "output_modalities": ["video"], "video_min_duration_seconds": 4,
                         "video_max_duration_seconds": 15},
        "request": {"model": {"$input": "model"}, "prompt": {"$input": "prompt"},
                    "task": "text-motion", "conditions": [], "defaults": {"steps": 50},
                    "target": {"edge": {"$input": "short_edge"}, "ratio": {"$input": "aspect_ratio"},
                               "duration": {"$input": "duration"}}},
    }
    connections._write_store({"studio": {"base_url": endpoint.base_url, "api_key": endpoint.api_key,
                                         "video_requests": {model: contract}}})
    return endpoint, model, contract


def live_metadata(monkeypatch, model, pipeline="ExamplePipeline"):
    response = Mock()
    response.json.return_value = {"data": [{"id": model, "pipeline_class": pipeline}]}
    request = Mock(return_value=response)
    monkeypatch.setattr(client, "_request", request)
    return request


def prepare(endpoint, model, **kwargs):
    values = dict(prompt="原始提示词", duration=4, resolution="720p", width=1280, height=720)
    values.update(kwargs)
    return video_contract.prepare(endpoint, model, **values)


def test_typed_mapping_uses_explicit_metadata_and_preserves_requested_size(mapped_service, monkeypatch):
    endpoint, model, contract = mapped_service
    request = live_metadata(monkeypatch, model)
    body = prepare(endpoint, model)
    assert body == {"model": model, "prompt": "原始提示词", "task": "text-motion", "conditions": [],
                    "defaults": {"steps": 50}, "target": {"edge": 720, "ratio": "16:9", "duration": 4}}
    assert request.call_count == 1 and request.call_args.args == ("GET", "/models")
    assert contract["request"]["prompt"] == {"$input": "prompt"}
    item = discovery.models("studio")["models"][0]
    assert item["category"] == "video" and item["video_min_duration_seconds"] == 4


def test_preset_ratio_is_preserved_when_width_rounding_is_inexact(mapped_service, monkeypatch):
    endpoint, model, _ = mapped_service
    live_metadata(monkeypatch, model)
    body = prepare(endpoint, model, resolution="768p", width=1365, height=768, aspect_ratio="16:9")
    assert body["target"]["ratio"] == "16:9" and body["target"]["edge"] == 768


def test_unsupported_resolution_rejected_before_submission(mapped_service, monkeypatch):
    endpoint, model, contract = mapped_service
    store = connections._store()
    store["studio"]["video_requests"][model]["capabilities"]["supported_resolutions"] = ["768p"]
    connections._write_store(store)
    request = live_metadata(monkeypatch, model)
    with pytest.raises(client.EcoHashError, match="resolution declared.*No video was submitted"):
        prepare(endpoint, model)
    assert all(call.args[0] == "GET" for call in request.call_args_list)


def test_mapping_is_bound_to_exact_model_and_url(mapped_service, monkeypatch):
    endpoint, model, _ = mapped_service
    request = Mock(side_effect=AssertionError("Unexpected request"))
    monkeypatch.setattr(client, "_request", request)
    assert prepare(endpoint, "another/model") is None
    changed = client.DedicatedEndpoint("https://other.example/v1", "private-key", 5, "studio")
    assert prepare(changed, model) is None
    assert prepare(client.DedicatedEndpoint(endpoint.base_url, endpoint.api_key), model) is None
    request.assert_not_called()


@pytest.mark.parametrize("change", ["engine", "model"])
def test_changed_deployment_rejected_before_any_post(mapped_service, monkeypatch, change):
    endpoint, model, _ = mapped_service
    request = live_metadata(monkeypatch, model if change == "engine" else "another/model", "NewPipeline")
    with pytest.raises(client.EcoHashError, match="no longer matches.*No video was submitted"):
        prepare(endpoint, model)
    assert all(call.args[0] == "GET" for call in request.call_args_list)
    assert all("category" not in item for item in discovery.models("studio")["models"])


@pytest.mark.parametrize("duration", [1, 16])
def test_declared_duration_limits_checked_before_submission(mapped_service, monkeypatch, duration):
    endpoint, model, _ = mapped_service
    request = live_metadata(monkeypatch, model)
    with pytest.raises(client.EcoHashError, match="duration conflicts.*No video was submitted"):
        prepare(endpoint, model, duration=duration)
    assert all(call.args[0] == "GET" for call in request.call_args_list)


@pytest.mark.parametrize("value", [{"$input": "api_key"}, {"$input": "prompt", "other": 1}, float("nan"),
                                  [[[[[[[[[[[[[[0]]]]]]]]]]]]]]])
def test_malformed_mapping_is_rejected_before_network(mapped_service, monkeypatch, value):
    endpoint, model, contract = mapped_service
    contract["request"]["bad"] = value
    store = connections._store()
    store["studio"]["video_requests"][model] = contract
    connections._write_store(store)
    request = Mock(side_effect=AssertionError("Unexpected request"))
    monkeypatch.setattr(client, "_request", request)
    with pytest.raises(client.EcoHashError, match="Video request mapping"):
        prepare(endpoint, model)
    request.assert_not_called()


def test_mapping_cannot_change_prompt_or_model(mapped_service, monkeypatch):
    endpoint, model, contract = mapped_service
    contract["request"]["prompt"] = "silently substituted prompt"
    store = connections._store()
    store["studio"]["video_requests"][model] = contract
    connections._write_store(store)
    live_metadata(monkeypatch, model)
    with pytest.raises(client.EcoHashError, match="must preserve"):
        prepare(endpoint, model)


def test_mapping_is_private_preserved_by_ui_saves_and_invalidates_discovery_and_execution(mapped_service, monkeypatch):
    from ecohash_nodes.video_nodes import EcoHashDedicatedVideoGenerate
    endpoint, model, contract = mapped_service
    request = live_metadata(monkeypatch, model)
    discovery.models("studio")
    before = EcoHashDedicatedVideoGenerate.IS_CHANGED(connection="studio")
    summary = connections.save_connection("studio", {"name": "Renamed"})
    assert "video_requests" not in summary and "private-key" not in json.dumps(connections.list_connections())
    assert video_contract.configured("studio")[model] == contract
    store = connections._store()
    store["studio"]["video_requests"][model]["capabilities"]["video_max_duration_seconds"] = 12
    connections._write_store(store)
    assert EcoHashDedicatedVideoGenerate.IS_CHANGED(connection="studio") != before
    assert discovery.models("studio")["models"][0]["video_max_duration_seconds"] == 12
    assert request.call_count == 2
