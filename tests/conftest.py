import pytest

from ecohash import client


@pytest.fixture(autouse=True)
def isolate_credentials(monkeypatch, tmp_path):
    """Tests must never read a developer's real inference credentials."""
    for name in (
        "ECOHASH_API_KEY", "ECOHASH_DEDICATED_BASE_URL",
        "ECOHASH_DEDICATED_API_KEY", "ECOHASH_DEDICATED_TIMEOUT",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(client, "CONFIG_PATH", tmp_path / "config.ini")
