"""EcoHash model catalog: live fetch (public endpoint) with packaged snapshot fallback."""

import json
import time
from pathlib import Path

import requests

CATALOG_URL = "https://api.ecohash.com/platform/models"
SNAPSHOT_PATH = Path(__file__).resolve().parent / "catalog_snapshot.json"
_TTL_SECONDS = 300

_CACHE = {"data": None, "ts": 0.0}


def get_catalog(force_refresh: bool = False) -> list:
    now = time.monotonic()
    if not force_refresh and _CACHE["data"] is not None and now - _CACHE["ts"] < _TTL_SECONDS:
        return _CACHE["data"]
    try:
        resp = requests.get(CATALOG_URL, params={"status": "active"}, timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, OSError, ValueError):
        if _CACHE["data"] is not None:
            return _CACHE["data"]
        try:
            data = json.loads(SNAPSHOT_PATH.read_text())
        except Exception:
            return []
    _CACHE.update({"data": data, "ts": now})
    return data


def model_ids(*categories: str) -> list:
    ids = [m["model_id"] for m in get_catalog() if m.get("category") in categories and m.get("model_id")]
    return ids or ["(catalog unavailable)"]


def models_where(**field_equals) -> list:
    return [
        m for m in get_catalog()
        if all(m.get(field) == value for field, value in field_equals.items())
    ]
