"""HTTP layer for the EcoHash API: key loading, auth, error mapping."""

import configparser
from dataclasses import dataclass, field
import os
from pathlib import Path
from urllib.parse import urlsplit

import requests

BASE_URL = "https://api.ecohash.com/v1"
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.ini"

_KEY_HELP = (
    "EcoHash API key not found. Open the EcoHash connection manager from the sidebar or a node's Connections button. "
    "Alternatively, set the ECOHASH_API_KEY environment variable, or copy "
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


@dataclass(frozen=True)
class DedicatedEndpoint:
    base_url: str
    api_key: str = field(repr=False)
    timeout: float = 300
    connection_id: str = "dedicated"


def _read_config():
    # Interpolation would interpret '%' in credentials as config syntax.
    parser = configparser.ConfigParser(interpolation=None)
    try:
        with CONFIG_PATH.open() as config_file:
            parser.read_file(config_file)
    except FileNotFoundError:
        pass
    except (configparser.Error, OSError, UnicodeError):
        # Do not include the parser error: it may quote a line containing a key.
        raise EcoHashError(f"Cannot read config file at {CONFIG_PATH}. Check its INI syntax and permissions.") from None
    return parser


def _validate_http_url(url, *, base_url=False):
    try:
        if not isinstance(url, str):
            raise ValueError
        parsed = urlsplit(url)
        valid = (
            parsed.scheme in ("http", "https") and parsed.hostname
            and not parsed.username and not parsed.password
            and not parsed.fragment and not any(c.isspace() for c in url)
        )
        parsed.port  # validate the port if one is present
        if base_url and parsed.query:
            valid = False
    except ValueError:
        valid = False
    if not valid:
        kind = "base_url" if base_url else "image URL"
        raise EcoHashError(
            f"Invalid {kind}: use an absolute http:// or https:// URL without embedded credentials or fragments."
        )
    return url


def load_dedicated_endpoint(connection="dedicated") -> DedicatedEndpoint:
    from .connections import resolve
    if connection == "public":
        raise EcoHashError("Select a dedicated connection for a Dedicated node.")
    return resolve(connection)


def load_api_key() -> str:
    key = os.environ.get("ECOHASH_API_KEY", "").strip()
    if key:
        return key
    from .connections import values
    try:
        key = values("public")["api_key"]
    except EcoHashError as exc:
        raise EcoHashAuthError(f"{exc}\n\n{_KEY_HELP}") from None
    if key and key != "eco_YOUR_KEY_HERE":
        return key
    raise EcoHashAuthError(_KEY_HELP)


def _raise_for_status(resp, endpoint=None) -> None:
    if endpoint is not None:
        if resp.status_code < 300:
            return
        key_hint = "Check ECOHASH_DEDICATED_API_KEY or [dedicated] api_key." if endpoint.connection_id == "dedicated" else "Check the selected connection's key in EcoHash connections."
        messages = {
            401: f"Dedicated inference authentication failed (401). {key_hint}",
            403: "Dedicated inference access denied (403). Check the dedicated key's access to this deployment.",
            404: "Dedicated inference endpoint or model not found (404). Check base_url (including its API prefix) and the deployed model ID.",
            429: "Dedicated inference rate limited (429). Wait a moment and retry.",
        }
        message = messages.get(resp.status_code, f"Dedicated inference API error {resp.status_code}.")
        if resp.status_code in (400, 405, 409, 422, 500, 502, 503):
            # Show validation reasons, never arbitrary response dumps or request
            # payloads. Invalid endpoint parameters should be actionable.
            try:
                payload = resp.json()
            except ValueError:
                payload = None
            detail = None
            if isinstance(payload, dict):
                detail = payload.get("detail") or payload.get("error") or payload.get("message")
                if isinstance(detail, dict):
                    detail = detail.get("message")
                elif isinstance(detail, list):
                    detail = "; ".join(item["msg"] for item in detail if isinstance(item, dict) and isinstance(item.get("msg"), str))
            if isinstance(detail, str) and detail.strip():
                message += " " + detail.replace(endpoint.api_key, "[REDACTED]")[:400]
        if 300 <= resp.status_code < 400:
            message = "Dedicated inference redirected the request. Configure the final API base_url directly."
        if resp.status_code in (401, 403):
            raise EcoHashAuthError(message)
        raise EcoHashError(message)
    if resp.status_code < 400:
        return
    message = _STATUS_MESSAGES.get(resp.status_code)
    if message is None:
        message = f"EcoHash API error {resp.status_code}: {resp.text[:300]}"
    if resp.status_code == 401:
        raise EcoHashAuthError(message)
    raise EcoHashError(message)


def _request(method: str, path: str, *, json_body=None, data=None, files=None, timeout=None, endpoint=None, allow_redirects=None, params=None):
    key = endpoint.api_key if endpoint is not None else load_api_key()
    base_url = endpoint.base_url if endpoint is not None else BASE_URL
    if timeout is None:
        timeout = endpoint.timeout if endpoint is not None else 180
    headers = {"Authorization": f"Bearer {key}"}
    try:
        resp = requests.request(
            method, base_url + path,
            json=json_body, data=data, files=files, headers=headers, timeout=timeout,
            **({"params": params} if params is not None else {}),
            **({"allow_redirects": allow_redirects} if allow_redirects is not None else
               {"allow_redirects": False} if endpoint is not None else {}),
        )
    except requests.RequestException as exc:
        if endpoint is not None:
            raise EcoHashError(
                f"Cannot reach dedicated inference API ({type(exc).__name__}). Check base_url, connectivity and timeout."
            ) from None
        raise EcoHashError(f"Cannot reach EcoHash API: {exc}") from exc
    _raise_for_status(resp, endpoint)
    return resp


def request_json(method: str, path: str, *, json_body=None, data=None, files=None, timeout=None, endpoint=None, allow_async=False, allow_redirects=None) -> dict:
    resp = _request(method, path, json_body=json_body, data=data, files=files, timeout=timeout, endpoint=endpoint, allow_redirects=allow_redirects)
    if resp.status_code == 202 and not allow_async:
        raise EcoHashError(
            "Inference API returned an asynchronous job (HTTP 202). These nodes require a synchronous "
            "response; this endpoint needs a task-polling adapter."
        )
    try:
        result = resp.json()
    except ValueError as exc:
        # A 2xx with a body that isn't JSON does happen (observed once: an empty body on
        # /chat/completions, which succeeded on retry). Decoding outside this guard would
        # surface a bare requests.exceptions.JSONDecodeError traceback in ComfyUI instead
        # of an actionable message.
        if endpoint is not None:
            raise EcoHashError(
                f"Dedicated inference returned a {resp.status_code} response that is not valid JSON. Check the API prefix and response format."
            ) from None
        raise EcoHashError(
            f"EcoHash returned a {resp.status_code} response that is not valid JSON "
            f"({len(resp.content)} bytes). This is usually transient — retry. "
            f"Body starts: {resp.text[:200]!r}"
        ) from exc
    if not isinstance(result, dict):
        raise EcoHashError("Inference API must return a JSON object. Check the endpoint's response format.")
    return result


def request_bytes(method: str, path: str, *, json_body, timeout=None, endpoint=None) -> bytes:
    response = _request(method, path, json_body=json_body, timeout=timeout, endpoint=endpoint)
    if response.status_code == 202:
        raise EcoHashError("Speech API returned an asynchronous job (HTTP 202). A task-polling adapter is required.")
    return response.content


def download_image(url: str, *, timeout=180) -> bytes:
    """Fetch an API result URL without forwarding either inference API credential."""
    _validate_http_url(url)
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise EcoHashError(f"Cannot download inference image ({type(exc).__name__}).") from None
    return resp.content
