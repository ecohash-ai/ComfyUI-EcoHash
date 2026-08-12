from unittest.mock import MagicMock, patch

from ecohash import catalog

FAKE = [
    {"model_id": "qwen-image", "category": "image", "supports_image_edit": False},
    {"model_id": "flux2-klein", "category": "image", "supports_image_edit": True},
    {"model_id": "glm-5.2", "category": "llm", "supports_image_edit": False},
]


def _fresh():
    catalog._CACHE.update({"data": None, "ts": 0.0})


def test_get_catalog_fetches_live(monkeypatch):
    _fresh()
    resp = MagicMock(status_code=200)
    resp.json.return_value = FAKE
    with patch.object(catalog.requests, "get", return_value=resp) as mock_get:
        data = catalog.get_catalog(force_refresh=True)
    assert data == FAKE
    assert mock_get.call_args.kwargs["params"] == {"status": "active"}


def test_get_catalog_falls_back_to_snapshot(monkeypatch):
    _fresh()
    with patch.object(catalog.requests, "get", side_effect=OSError("offline")):
        data = catalog.get_catalog(force_refresh=True)
    assert isinstance(data, list) and len(data) > 0  # snapshot shipped with the package


def test_model_ids_filters_by_category(monkeypatch):
    _fresh()
    monkeypatch.setattr(catalog, "get_catalog", lambda force_refresh=False: FAKE)
    assert catalog.model_ids("image") == ["qwen-image", "flux2-klein"]
    assert catalog.model_ids("llm", "image") == ["qwen-image", "flux2-klein", "glm-5.2"]


def test_model_ids_never_empty(monkeypatch):
    monkeypatch.setattr(catalog, "get_catalog", lambda force_refresh=False: [])
    assert catalog.model_ids("video") == ["(catalog unavailable)"]


def test_models_where(monkeypatch):
    monkeypatch.setattr(catalog, "get_catalog", lambda force_refresh=False: FAKE)
    assert [m["model_id"] for m in catalog.models_where(supports_image_edit=True)] == ["flux2-klein"]


def test_warm_cache_short_circuits_network(monkeypatch):
    """Warm cache within TTL should not call network on subsequent get_catalog()."""
    _fresh()
    # First call with force_refresh=True populates cache
    resp = MagicMock(status_code=200)
    resp.json.return_value = FAKE
    with patch.object(catalog.requests, "get", return_value=resp) as mock_get:
        data1 = catalog.get_catalog(force_refresh=True)
    assert data1 == FAKE
    assert mock_get.call_count == 1

    # Second call without force_refresh should NOT call network (cache hit within TTL)
    def fail_if_called(*args, **kwargs):
        raise AssertionError("network should not be called for warm cache")

    with patch.object(catalog.requests, "get", side_effect=fail_if_called):
        data2 = catalog.get_catalog()
    assert data2 == FAKE


def test_stale_cache_preferred_over_snapshot(monkeypatch):
    """Stale in-memory cache should be returned before falling back to snapshot."""
    # Prime cache with FAKE data and expired timestamp
    catalog._CACHE.update({"data": FAKE, "ts": 0.0})

    # Network fails
    with patch.object(catalog.requests, "get", side_effect=OSError("offline")):
        data = catalog.get_catalog(force_refresh=True)

    # Should return stale cache (FAKE), not snapshot
    assert data == FAKE


def test_snapshot_read_failure_returns_empty(monkeypatch):
    """Snapshot read failure should return [] and not crash."""
    _fresh()
    # Network fails
    with patch.object(catalog.requests, "get", side_effect=OSError("offline")):
        # Patch SNAPSHOT_PATH to a nonexistent file
        monkeypatch.setattr(catalog, "SNAPSHOT_PATH", "/nonexistent/path/to/snapshot.json")
        data = catalog.get_catalog(force_refresh=True)

    assert data == []
    # Verify model_ids converts empty list to placeholder
    monkeypatch.setattr(catalog, "get_catalog", lambda force_refresh=False: [])
    assert catalog.model_ids("any_category") == ["(catalog unavailable)"]
