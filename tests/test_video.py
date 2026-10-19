"""Video protocol, async lifecycle and credential isolation over real loopback HTTP."""

from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

import pytest
import requests

from ecohash import client, video

# Transport fixture only; actual MP4 decoding is checked in running ComfyUI.
MP4 = b"\x00\x00\x00\x18ftypisom" + b"video-transport-fixture"


@pytest.fixture
def video_server():
    records, config = [], {"polls": 0, "status": "completed", "blob": MP4}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, status, payload, content_type="application/json", **headers):
            if content_type == "application/json":
                payload = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(payload)

        def record(self):
            item = {"method": self.command, "path": self.path, "auth": self.headers.get("Authorization")}
            records.append(item)
            return item

        def do_POST(self):
            item = self.record()
            body = self.rfile.read(int(self.headers["Content-Length"]))
            if self.headers["Content-Type"].startswith("multipart/"):
                message = BytesParser(policy=policy.default).parsebytes(
                    b"Content-Type: " + self.headers["Content-Type"].encode() + b"\r\nMIME-Version: 1.0\r\n\r\n" + body)
                item["form"] = {part.get_param("name", header="content-disposition"): part.get_payload(decode=True).decode() for part in message.iter_parts()}
            else:
                item["json"] = json.loads(body)
            return self.respond(202, {"id": "job-123", "status": "queued"})

        def do_GET(self):
            self.record()
            if self.path == "/blob":
                return self.respond(200, config["blob"], "video/mp4")
            if self.path.endswith("/content"):
                return self.respond(302, {}, Location="/blob")
            config["polls"] += 1
            result = {"id": "job-123", "status": "processing" if config["polls"] == 1 else config["status"]}
            if result["status"] == "completed" and "/video/jobs/" in self.path:
                result["url"] = f"http://127.0.0.1:{self.server.server_port}/blob"
            if result["status"] == "failed":
                result["error"] = {"code": "model_failure", "message": "Invalid model configuration, private-key"}
            return self.respond(200, result)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", records, config
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _body(protocol):
    return video.build_request(protocol, "private/h3", "a cat in the rain", 4, "16:9", "720p", True, 50, 42)


@pytest.mark.parametrize("protocol", video.PROTOCOLS)
def test_async_submit_poll_download_and_auth_isolation(protocol, video_server, tmp_path, monkeypatch):
    base, records, config = video_server
    monkeypatch.setenv("ECOHASH_API_KEY", "public-only-key")
    endpoint = client.DedicatedEndpoint(base + "/private/v1", "private-key", 5, "studio")
    progress = []
    path, job = video.generate(protocol=protocol, body=_body(protocol), endpoint=endpoint,
                               output_dir=tmp_path, poll_interval=0, progress=lambda *args: progress.append(args))
    assert job == "job-123" and path.read_bytes() == MP4
    assert [r["method"] for r in records].count("POST") == 1
    assert config["polls"] == 2
    assert records[0]["auth"] == "Bearer private-key"
    assert records[-1] == {"method": "GET", "path": "/blob", "auth": None}
    assert all(r["auth"] == "Bearer private-key" for r in records[:-1])
    assert progress[-1] == ("job-123", "completed", 100)
    if protocol == "openai":
        assert records[0]["form"]["seconds"] == "4"
        assert records[0]["form"]["size"] == "1280x720"
    elif protocol == "minimax_h3":
        assert records[0]["json"]["target"] == {"short_edge": 768, "aspect_ratio": "16:9", "duration_seconds": 4.0}
        assert not {"fps", "num_frames", "size", "extra_params"} & records[0]["json"].keys()
    else:
        assert records[0]["json"]["duration"] == 4
        assert records[0]["path"] == "/private/v1/video/generations"


def test_public_video_uses_public_key_and_download_has_no_auth(video_server, tmp_path, monkeypatch):
    base, records, _ = video_server
    monkeypatch.setattr(client, "BASE_URL", base + "/v1")
    monkeypatch.setenv("ECOHASH_API_KEY", "public-key")
    path, _ = video.generate(protocol="ecohash", body=_body("ecohash"), output_dir=tmp_path, poll_interval=0)
    assert path.read_bytes() == MP4
    assert [r["auth"] for r in records] == ["Bearer public-key"] * 3 + [None]


def test_resume_performs_no_post(video_server, tmp_path):
    base, records, _ = video_server
    endpoint = client.DedicatedEndpoint(base + "/v1", "private-key", 5)
    video.generate(protocol="minimax_h3", body={}, job_id="job-123", endpoint=endpoint,
                   output_dir=tmp_path, poll_interval=0)
    assert all(r["method"] == "GET" for r in records)


@pytest.mark.parametrize("status,message", [("failed", "Invalid model configuration"), ("strange", "unsupported job status"),
                                          (None, "string status"), ({"state": "queued"}, "string status"), ([], "string status")])
def test_failed_or_invalid_status_keeps_job_id_and_never_resubmits(status, message, video_server, tmp_path):
    base, records, config = video_server
    config["status"] = status
    endpoint = client.DedicatedEndpoint(base + "/v1", "private-key", 5)
    with pytest.raises(client.EcoHashError, match=message) as error:
        video.generate(protocol="minimax_h3", body=_body("minimax_h3"), endpoint=endpoint,
                       output_dir=tmp_path, poll_interval=0)
    assert "Job ID: job-123" in str(error.value)
    assert "private-key" not in str(error.value)
    assert sum(r["method"] == "POST" for r in records) == 1
    assert not list(tmp_path.glob("*.mp4"))


def test_timeout_reports_resumable_job(video_server, tmp_path):
    base, records, config = video_server
    config["status"] = "processing"
    with pytest.raises(client.EcoHashError, match="Timed out.*Job ID: job-123"):
        video.generate(protocol="minimax_h3", body={}, job_id="job-123", wait_timeout=1,
                       endpoint=client.DedicatedEndpoint(base + "/v1", "private-key", 5),
                       output_dir=tmp_path, poll_interval=0.1)
    assert all(r["method"] == "GET" for r in records)


def test_interrupt_stops_polling_without_another_submission(video_server, tmp_path):
    base, records, _ = video_server
    checks = []

    def check():
        checks.append(1)
        if len(checks) == 3:
            raise InterruptedError("stop")

    with pytest.raises(InterruptedError):
        video.generate(protocol="minimax_h3", body=_body("minimax_h3"), check_interrupt=check,
                       endpoint=client.DedicatedEndpoint(base + "/v1", "private-key", 5),
                       output_dir=tmp_path, poll_interval=0)
    assert sum(r["method"] == "POST" for r in records) == 1


def test_invalid_download_is_removed_and_can_be_resumed(video_server, tmp_path):
    base, _, config = video_server
    config["blob"] = b"<html>wrong route</html>"
    with pytest.raises(client.EcoHashError, match="valid MP4.*Job ID: job-123"):
        video.generate(protocol="minimax_h3", body={}, job_id="job-123",
                       endpoint=client.DedicatedEndpoint(base + "/v1", "private-key", 5),
                       output_dir=tmp_path, poll_interval=0)
    assert not list(tmp_path.glob("*.mp4"))


@pytest.mark.parametrize("job", ["../secret", "https://example.com/", "..", "bad?query", "x" * 201])
def test_resume_rejects_path_injection(job, tmp_path, monkeypatch):
    monkeypatch.setattr(client, "request_json", lambda *a, **k: pytest.fail("Unexpected request"))
    with pytest.raises(client.EcoHashError, match="valid job ID"):
        video.generate(protocol="openai", body={}, job_id=job, output_dir=tmp_path)


def test_native_h3_default_profile_and_protocol_specific_parameters():
    body = video.build_request("minimax_h3", "model", "prompt", 4, "9:16", "720p", False)
    assert body["num_inference_steps"] == 50
    assert body["target"] == {"short_edge": 768, "aspect_ratio": "9:16", "duration_seconds": 4.0}
    assert not {"generate_audio", "resolution", "fps", "seed"} & body.keys()
    assert video.build_request("ecohash", "model", "prompt", 4, "16:9", "480p", False)["generate_audio"] is False


def test_lost_submission_response_never_retries_a_potentially_billable_post(monkeypatch, tmp_path):
    calls = []

    def timeout(*args, **kwargs):
        calls.append((args, kwargs))
        raise requests.Timeout("response lost")

    monkeypatch.setattr(client.requests, "request", timeout)
    with pytest.raises(client.EcoHashError, match="No automatic resubmission"):
        video.generate(protocol="minimax_h3", body=_body("minimax_h3"), output_dir=tmp_path,
                       endpoint=client.DedicatedEndpoint("https://private.example/v1", "private-key"))
    assert len(calls) == 1


@pytest.mark.parametrize("duration,ratio", [(3, "16:9"), (16, "16:9"), (4, "adaptive")])
def test_invalid_native_parameters_are_rejected_before_submission(duration, ratio):
    with pytest.raises(client.EcoHashError):
        video.build_request("minimax_h3", "model", "prompt", duration, ratio, "720p", True)
