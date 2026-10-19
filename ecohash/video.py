"""Asynchronous video adapters. A submission is never automatically retried."""

from pathlib import Path
import re
import time
from urllib.parse import urljoin
import uuid

import requests

from . import client

PROTOCOLS = ["ecohash", "openai"]
RATIOS = ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"]
RESOLUTIONS = ["480p", "720p", "768p", "1080p", "4k"]
_PENDING = {"queued", "pending", "processing", "in_progress", "running"}
_MAX_BYTES = 512 * 1024 * 1024


def dimensions(resolution, aspect_ratio):
    # These are size-label conventions, not a model compatibility table.
    match = re.fullmatch(r"([1-9][0-9]*)(p|k)", str(resolution).lower())
    if not match or not re.fullmatch(r"[1-9][0-9]*:[1-9][0-9]*", str(aspect_ratio)):
        raise client.EcoHashError("Use a resolution such as 720p and a numeric aspect ratio such as 16:9, or choose custom size.")
    short_edge = int(match[1]) * (540 if match[2] == "k" else 1)
    x, y = map(int, aspect_ratio.split(":"))
    # Use ordinary OpenAI sizes at the common 720p/1080p 16:9 shapes.
    return round(short_edge * x / min(x, y)), round(short_edge * y / min(x, y))


def _job_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,200}", value) or value in {".", ".."}:
        raise client.EcoHashError("Video API requires a valid job ID (letters, digits, dots, hyphens or underscores).")
    return value


def build_request(protocol, model, prompt, duration, aspect_ratio, resolution, generate_audio,
                  steps=0, seed=-1, width=1280, height=720):
    if protocol not in PROTOCOLS:
        raise client.EcoHashError("Unsupported video transport. Dedicated services must implement the OpenAI Videos API.")
    if not isinstance(model, str) or not model.strip() or not isinstance(prompt, str) or not prompt.strip():
        raise client.EcoHashError("Enter a model ID and a nonempty video prompt.")
    if isinstance(duration, bool) or not isinstance(duration, int) or not 1 <= duration <= 86400:
        raise client.EcoHashError("Video duration must be a positive integer in seconds, supported by the selected model.")
    body = {"model": model.strip(), "prompt": prompt.strip()}
    if protocol == "openai":
        if any(isinstance(v, bool) or not isinstance(v, int) or not 128 <= v <= 8192 for v in (width, height)):
            raise client.EcoHashError("Video width and height must be between 128 and 8192, supported by the selected model.")
        body.update(seconds=str(duration), size=f"{width}x{height}")
    else:
        # The gateway owns model-native defaults, limits and provider adaptation.
        body.update(duration=duration, aspect_ratio=aspect_ratio, resolution=resolution, generate_audio=bool(generate_audio))
    return body


def _download(url, target, timeout, check_interrupt, *, endpoint=None, authenticated=False):
    """Only the constructed /content route gets auth; redirects and result URLs never do."""
    headers = {}
    if authenticated:
        headers["Authorization"] = f"Bearer {endpoint.api_key if endpoint else client.load_api_key()}"
    try:
        for _ in range(6):
            client._validate_http_url(url)
            with requests.get(url, headers=headers, timeout=timeout, stream=True, allow_redirects=False) as response:
                if response.is_redirect:
                    location = response.headers.get("Location")
                    if not location:
                        raise client.EcoHashError("Video content redirect is missing its download URL.")
                    url = urljoin(url, location)
                    headers = {}
                    continue
                client._raise_for_status(response, endpoint if authenticated else None)
                if not response.ok:
                    raise client.EcoHashError("Cannot download the completed video.")
                count = 0
                with target.open("wb") as output:
                    for chunk in response.iter_content(1024 * 1024):
                        check_interrupt()
                        count += len(chunk)
                        if count > _MAX_BYTES:
                            raise client.EcoHashError("Video exceeds the supported 512 MiB download limit.")
                        output.write(chunk)
                with target.open("rb") as output:
                    header = output.read(12)
                if len(header) < 12 or header[4:8] != b"ftyp":
                    raise client.EcoHashError("Video API did not return a valid MP4 file. Check its content endpoint or result URL.")
                return
        raise client.EcoHashError("Video download redirected too many times.")
    except requests.RequestException as exc:
        raise client.EcoHashError(f"Video download failed ({type(exc).__name__}). Resume using the existing job ID.") from None


def generate(*, protocol, body, output_dir, endpoint=None, job_id="", wait_timeout=1800,
             check_interrupt=lambda: None, progress=lambda *args: None, poll_interval=3):
    """Submit once, or resume a job; return the downloaded MP4 path and its ID."""
    if protocol not in PROTOCOLS:
        raise client.EcoHashError("Unknown video API protocol.")
    if not isinstance(wait_timeout, (int, float)) or isinstance(wait_timeout, bool) or not 1 <= wait_timeout <= 14400:
        raise client.EcoHashError("Video wait timeout must be between 1 and 14400 seconds.")
    deadline = time.monotonic() + wait_timeout
    request_timeout = min(endpoint.timeout if endpoint else 180, 30)
    base_url = endpoint.base_url if endpoint else client.BASE_URL
    submit_path = "/video/generations" if protocol == "ecohash" else "/videos"
    status_prefix = "/video/jobs/" if protocol == "ecohash" else "/videos/"
    options = {"endpoint": endpoint, "allow_async": True, "allow_redirects": False}
    check_interrupt()
    if job_id:
        job_id = _job_id(job_id.strip())
        result = None
    else:
        # Deliberately no retry: a lost POST response may still have created a job.
        try:
            if protocol == "openai":
                result = client.request_json("POST", submit_path, files={k: (None, str(v)) for k, v in body.items()},
                                             timeout=min(endpoint.timeout if endpoint else 180, 60), **options)
            else:
                result = client.request_json("POST", submit_path, json_body=body,
                                             timeout=min(endpoint.timeout if endpoint else 180, 60), **options)
        except client.EcoHashError as exc:
            raise client.EcoHashError(f"Video submission did not return a job: {exc} No automatic resubmission was made; check the service before submitting again.") from None
        job_id = _job_id(result.get("id"))
    print(f"[EcoHash] Video job {job_id}; set job_id to this value to resume without submitting again.")
    progress(job_id, "queued", 0)
    try:
        while True:
            check_interrupt()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise client.EcoHashError("Timed out waiting for video completion.")
            if result is None:
                result = client.request_json("GET", status_prefix + job_id, timeout=min(request_timeout, remaining), **options)
            if result.get("id", job_id) != job_id:
                raise client.EcoHashError("Video status response returned a different job ID.")
            status = result.get("status")
            if not isinstance(status, str):
                raise client.EcoHashError("Video status response must contain a string status.")
            progress(job_id, status, result.get("progress", 0))
            if status == "completed":
                break
            if status in {"failed", "cancelled", "canceled", "expired"}:
                error = result.get("error")
                if isinstance(error, dict):
                    error = error.get("message") or error.get("code")
                message = str(error or result.get("code") or status)[:500]
                message = message.replace(endpoint.api_key if endpoint else client.load_api_key(), "[REDACTED]")
                raise client.EcoHashError(f"Video generation failed: {message}")
            if status not in _PENDING:
                raise client.EcoHashError(f"Video API returned an unsupported job status: {str(status)[:80]}")
            wake = min(deadline, time.monotonic() + poll_interval)
            while time.monotonic() < wake:
                check_interrupt()
                time.sleep(min(0.25, max(0, wake - time.monotonic())))
            result = None
        url = result.get("url")
        authenticated = not url
        if not url and protocol == "ecohash":
            raise client.EcoHashError("Completed EcoHash video job has no download URL.")
        if not url:
            url = base_url + status_prefix + job_id + "/content"
        target = Path(output_dir) / f"ecohash-video-{uuid.uuid4().hex}.mp4"
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            _download(url, target, min(request_timeout, max(1, deadline - time.monotonic())),
                      check_interrupt, endpoint=endpoint, authenticated=authenticated)
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        progress(job_id, "completed", 100)
        return target, job_id
    except client.EcoHashError as exc:
        raise client.EcoHashError(f"{exc} Job ID: {job_id}. To resume without a new submission, paste it into job_id and keep the same connection.") from None
