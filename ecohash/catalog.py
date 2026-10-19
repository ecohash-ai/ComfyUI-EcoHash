"""EcoHash model catalog: live fetch (public endpoint) with packaged snapshot fallback."""

import json
import time
from pathlib import Path

import requests

CATALOG_URL = "https://api.ecohash.com/platform/models"
SNAPSHOT_PATH = Path(__file__).resolve().parent / "catalog_snapshot.json"
_TTL_SECONDS = 300

_CACHE = {"data": None, "ts": 0.0, "source": "snapshot", "error": None}


def _snapshot():
    try:
        data = json.loads(SNAPSHOT_PATH.read_text())
        return [m for m in data if isinstance(m, dict)] if isinstance(data, list) else []
    except (OSError, ValueError, AttributeError):
        return []


def schema_catalog():
    """Node schemas never wait for a network request. The UI refreshes separately."""
    return _CACHE["data"] if _CACHE["data"] is not None else _snapshot()


def status():
    return {"source": _CACHE.get("source", "snapshot"), "error": _CACHE.get("error")}


def get_catalog(force_refresh: bool = False) -> list:
    now = time.monotonic()
    if not force_refresh and _CACHE["data"] is not None and now - _CACHE["ts"] < _TTL_SECONDS:
        return _CACHE["data"]
    try:
        resp = requests.get(CATALOG_URL, params={"status": "active"}, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise ValueError("Expected a model list")
        data = [m for m in data if isinstance(m, dict)]
    except (requests.RequestException, OSError, ValueError):
        data = _CACHE["data"] if _CACHE["data"] is not None else _snapshot()
        source = "stale" if _CACHE["data"] is not None else "snapshot"
        _CACHE.update({"data": data, "ts": now, "source": source, "error": "Catalog unavailable; using cached models. Retry refresh when connectivity is restored."})
        return data
    _CACHE.update({"data": data, "ts": now, "source": "live", "error": None})
    return data


def model_ids(*categories: str) -> list:
    ids = [m["model_id"] for m in schema_catalog() if m.get("category") in categories and m.get("model_id")]
    return ids or ["(catalog unavailable)"]


def models_where(**field_equals) -> list:
    return [
        m for m in schema_catalog()
        if all(m.get(field) == value for field, value in field_equals.items())
    ]
