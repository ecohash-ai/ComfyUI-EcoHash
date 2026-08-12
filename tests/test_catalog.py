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
    assert "status=active" in str(mock_get.call_args)


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
