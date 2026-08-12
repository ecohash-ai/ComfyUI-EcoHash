"""Regenerate ecohash/catalog_snapshot.json from the live public catalog. Run before each release."""

import json
from pathlib import Path

import requests

out = Path(__file__).resolve().parent.parent / "ecohash" / "catalog_snapshot.json"
data = requests.get("https://api.ecohash.com/platform/models", params={"status": "active"}, timeout=15).json()
out.write_text(json.dumps(data, indent=1, ensure_ascii=False))
print(f"wrote {len(data)} models to {out}")
