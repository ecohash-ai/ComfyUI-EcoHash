"""HTTP layer for the EcoHash API: key loading, auth, error mapping."""

import configparser
import os
from pathlib import Path

import requests

BASE_URL = "https://api.ecohash.com/v1"
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.ini"

_KEY_HELP = (
    "EcoHash API key not found. Set the ECOHASH_API_KEY environment variable, or copy "
    "config.ini.example to config.ini inside the ComfyUI-EcoHash folder and paste your key. "
    "Get a key at https://docs.ecohash.com/getting-started/api-keys"
)

_STATUS_MESSAGES = {
    401: "Invalid EcoHash API key (401). Check ECOHASH_API_KEY or config.ini. "
         "Manage keys at https://docs.ecohash.com/getting-started/api-keys",
    402: "EcoHash account has insufficient credit (402). Top up at https://docs.ecohash.com/billing/adding-credit",
    404: "Model not found on EcoHash (404). The catalog may have changed; try refreshing ComfyUI.",
    429: "Rate limited by EcoHash (429). Wait a moment and retry. See https://docs.ecohash.com/api-reference/rate-limits",
}


class EcoHashError(RuntimeError):
    pass


class EcoHashAuthError(EcoHashError):
    pass


def load_api_key() -> str:
    key = os.environ.get("ECOHASH_API_KEY", "").strip()
    if key:
        return key
    if CONFIG_PATH.exists():
        parser = configparser.ConfigParser()
        try:
            parser.read(CONFIG_PATH)
        except configparser.Error as exc:
            raise EcoHashAuthError(
                f"Malformed config file at {CONFIG_PATH}: {exc}\n\n{_KEY_HELP}"
            ) from exc
        key = parser.get("ecohash", "api_key", fallback="").strip()
        if key and key != "eco_YOUR_KEY_HERE":
            return key
    raise EcoHashAuthError(_KEY_HELP)


def _raise_for_status(resp) -> None:
    if resp.status_code < 400:
        return
    message = _STATUS_MESSAGES.get(resp.status_code)
    if message is None:
        message = f"EcoHash API error {resp.status_code}: {resp.text[:300]}"
    if resp.status_code == 401:
        raise EcoHashAuthError(message)
    raise EcoHashError(message)


def _request(method: str, path: str, *, json_body=None, data=None, files=None, timeout=180):
    headers = {"Authorization": f"Bearer {load_api_key()}"}
    try:
        resp = requests.request(
            method, BASE_URL + path,
            json=json_body, data=data, files=files, headers=headers, timeout=timeout,
        )
    except requests.RequestException as exc:
        raise EcoHashError(f"Cannot reach EcoHash API: {exc}") from exc
    _raise_for_status(resp)
    return resp


def request_json(method: str, path: str, *, json_body=None, data=None, files=None, timeout=180) -> dict:
    resp = _request(method, path, json_body=json_body, data=data, files=files, timeout=timeout)
    try:
        return resp.json()
    except ValueError as exc:
        # A 2xx with a body that isn't JSON does happen (observed once: an empty body on
        # /chat/completions, which succeeded on retry). Decoding outside this guard would
        # surface a bare requests.exceptions.JSONDecodeError traceback in ComfyUI instead
        # of an actionable message.
        raise EcoHashError(
            f"EcoHash returned a {resp.status_code} response that is not valid JSON "
            f"({len(resp.content)} bytes). This is usually transient — retry. "
            f"Body starts: {resp.text[:200]!r}"
        ) from exc


def request_bytes(method: str, path: str, *, json_body, timeout=180) -> bytes:
    return _request(method, path, json_body=json_body, timeout=timeout).content
