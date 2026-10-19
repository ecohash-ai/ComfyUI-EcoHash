"""EcoHash model catalog: live fetch (public endpoint) with packaged snapshot fallback."""

import json
import re
import time
from pathlib import Path

import requests

CATALOG_URL = "https://api.ecohash.com/platform/models"
VIDEO_PRICING_URL = "https://api.ecohash.com/platform/video-pricing"
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
    if any(m.get("category") == "video" for m in data):
        # EcoLink prices/gates video by resolution band. Read the public matrix
        # once per catalog refresh rather than maintaining a model-name table.
        try:
            pricing = requests.get(VIDEO_PRICING_URL, timeout=5)
            pricing.raise_for_status()
            tiers = pricing.json()
            if not isinstance(tiers, list):
                raise ValueError("Expected video tiers")
            bands = {}
            for tier in tiers:
                if not isinstance(tier, dict) or tier.get("has_video_input") is not False:
                    continue
                model_id, band = tier.get("model_id"), tier.get("resolution_band")
                if isinstance(model_id, str) and isinstance(band, str) and band:
                    # Same wire convention as EcoLink's resolutionOptionsFromTiers:
                    # the coarse price key is not itself a request resolution.
                    bands.setdefault(model_id, []).extend(["480p", "720p"] if band == "480_720p" else [band])
            def height(label):
                match = re.fullmatch(r"(\d+)(p|k)", label, re.IGNORECASE)
                return int(match[1]) * (540 if match[2].lower() == "k" else 1) if match else float("inf")
            data = [{**m, **({"supported_resolutions": sorted(set(bands[m["model_id"]]), key=height)} if m.get("model_id") in bands else {})} for m in data]
        except (requests.RequestException, OSError, ValueError):
            pass  # Missing tier metadata stays unknown, not a compatibility guess.
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
