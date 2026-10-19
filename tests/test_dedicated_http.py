"""Real loopback HTTP round trips, without a ComfyUI server or external API calls."""

import base64
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import threading

import pytest
from PIL import Image

from ecohash import client
from ecohash_nodes.image_nodes import (
    EcoHashDedicatedImageEdit, EcoHashDedicatedImageGenerate, EcoHashImageGenerate,
)


def _png(color):
    buffer = io.BytesIO()
    Image.new("RGB", (48, 32), color).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def inference_server():
    records = []
    generated = _png((255, 0, 0))
    edited = _png((0, 255, 0))

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

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            record = {"path": self.path, "auth": self.headers.get("Authorization")}
            records.append(record)
            if self.path.startswith("/redirect/"):
                return self.respond(307, {}, Location="/unexpected-forward")
            if self.path.startswith("/async/"):
                return self.respond(202, {"id": "queued-job"})
            if self.path.endswith("/images/generations"):
                record["json"] = json.loads(body)
                return self.respond(200, {"data": [{"b64_json": base64.b64encode(generated).decode()}]})
            if self.path.endswith("/images/edits"):
                content_type = self.headers["Content-Type"].encode()
                message = BytesParser(policy=policy.default).parsebytes(
                    b"Content-Type: " + content_type + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
                )
                parts = {part.get_param("name", header="content-disposition"): part for part in message.iter_parts()}
                record["fields"] = {name: part.get_payload(decode=True).decode() for name, part in parts.items() if name != "image"}
                image = parts["image"]
                record["filename"] = image.get_filename()
                record["image"] = Image.open(io.BytesIO(image.get_payload(decode=True))).getpixel((0, 0))
                return self.respond(200, {"data": [{"url": f"http://127.0.0.1:{self.server.server_port}/result.png?signature=test"}]})
            self.respond(404, {})

        def do_GET(self):
            records.append({"path": self.path, "auth": self.headers.get("Authorization")})
            self.respond(200, edited, "image/png")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", records
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_public_and_dedicated_generation_edit_round_trip(monkeypatch, inference_server):
    base_url, records = inference_server
    monkeypatch.setattr(client, "BASE_URL", base_url + "/public/v1")
    monkeypatch.setenv("ECOHASH_API_KEY", "public-test-key")
    client.CONFIG_PATH.write_text(
        f"[dedicated]\nbase_url = {base_url}/tenant/deployment/v1/\n"
        "api_key = dedicated-test-key\ntimeout = 5\n"
    )

    (public,) = EcoHashImageGenerate().generate("z-image-turbo", "public prompt", "512x512", 0, -1)
    (private,) = EcoHashDedicatedImageGenerate().generate("my/private-model", "红色苹果", "512x512", 8, 42)
    (edited,) = EcoHashDedicatedImageEdit().edit(private, "my/private-edit", "make it green", "auto")

    assert tuple(public.shape) == tuple(private.shape) == tuple(edited.shape) == (1, 32, 48, 3)
    assert private[0, 0, 0].tolist() == [1, 0, 0]
    assert edited[0, 0, 0].tolist() == [0, 1, 0]
    assert [r["path"] for r in records] == [
        "/public/v1/images/generations", "/tenant/deployment/v1/images/generations",
        "/tenant/deployment/v1/images/edits", "/result.png?signature=test",
    ]
    assert [r["auth"] for r in records] == [
        "Bearer public-test-key", "Bearer dedicated-test-key", "Bearer dedicated-test-key", None,
    ]
    assert records[0]["json"] == {
        "model": "z-image-turbo", "prompt": "public prompt", "size": "512x512", "response_format": "b64_json",
    }
    assert records[1]["json"] == {
        "model": "my/private-model", "prompt": "红色苹果", "size": "512x512",
        "response_format": "b64_json", "steps": 8, "seed": 42,
    }
    assert records[2]["fields"] == {"model": "my/private-edit", "prompt": "make it green", "size": "48x32"}
    assert records[2]["filename"] == "input.png"
    assert records[2]["image"] == (255, 0, 0)


@pytest.mark.parametrize("path,message", [("redirect", "redirected"), ("async", "task-polling adapter")])
def test_dedicated_incompatible_response_does_not_send_another_request(monkeypatch, inference_server, path, message):
    base_url, records = inference_server
    monkeypatch.setenv("ECOHASH_DEDICATED_BASE_URL", base_url + f"/{path}/v1")
    monkeypatch.setenv("ECOHASH_DEDICATED_API_KEY", "dedicated-test-key")
    with pytest.raises(client.EcoHashError, match=message):
        EcoHashDedicatedImageGenerate().generate("private-model", "p", "512x512", 0, -1)
    assert len(records) == 1


def test_dedicated_smoke_command_saves_both_results(monkeypatch, inference_server, tmp_path, capsys):
    from scripts.smoke_dedicated import main

    base_url, records = inference_server
    monkeypatch.setenv("ECOHASH_DEDICATED_BASE_URL", base_url + "/private/v1")
    monkeypatch.setenv("ECOHASH_DEDICATED_API_KEY", "dedicated-test-key")
    assert main([
        "--model", "private/model", "--edit-model", "private/edit",
        "--output-dir", str(tmp_path),
    ]) == 0
    with Image.open(tmp_path / "generated.png") as image:
        assert image.getpixel((0, 0)) == (255, 0, 0)
    with Image.open(tmp_path / "edited.png") as image:
        assert image.getpixel((0, 0)) == (0, 255, 0)
    assert "PASS generation: 48x32" in capsys.readouterr().out
    assert len(records) == 3
