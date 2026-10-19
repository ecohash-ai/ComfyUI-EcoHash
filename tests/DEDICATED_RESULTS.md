# Dedicated inference local verification

- Date: 2026-10-19
- Branch: `feat/dedicated-inference`
- Environment: macOS arm64, Python 3.13.12, PyTorch 2.14.1, pytest 9.1.1
- Command: `.venv/bin/python -m pytest -q --tb=short`
- Result: **101 passed in 3.00s**

## Verified

- Existing public image, LLM, VLM, TTS, STT, catalog and conversion tests pass.
- Both dedicated nodes load through ComfyUI's `importlib` package-loading pattern,
  with a simulated already-loaded core `nodes` module. Their schemas accept private
  model IDs as strings without consulting the public catalog.
- Environment/INI configuration, environment precedence, exact API path prefixes,
  trailing slash normalization and configurable request timeout.
- Public and dedicated credentials remain separate. Missing dedicated credentials
  fail before a request; public credentials are never substituted.
- A real local HTTP test server receives public generation, dedicated generation,
  dedicated multipart image editing and a result-image download in sequence.
  Assertions check paths, bearer credentials, model IDs, prompts, steps, seed,
  multipart fields and uploaded PNG pixels. The result download has no inference
  bearer credential.
- The test service returns a synthetic red 48x32 PNG via base64 and a synthetic
  green 48x32 PNG via URL. Both become valid ComfyUI `IMAGE` tensors; the red image
  is correctly uploaded as input to the edit request.
- Redirects are rejected without issuing another API request. HTTP 202 asynchronous
  jobs, authentication failures, invalid URLs/timeouts, malformed JSON/images and
  network timeouts produce actionable errors.
- Dedicated endpoint/key changes alter the cache fingerprint without exposing the
  credential in that fingerprint.
- `scripts/smoke_dedicated.py` runs against the local HTTP service and saves the
  expected generated/edited PNGs.
- `dedicated_text_to_image.json` parses, matches the dedicated node's widget schema
  and has consistent image links. `git diff --check` passes.

The first sandboxed test run passed 97 checks; four HTTP tests could not bind a local
port. The full run above passed after allowing a temporary listener on `127.0.0.1`.

## Pending real deployment verification

No dedicated endpoint or credentials have been supplied yet. The local HTTP service
does not perform model inference. Compatibility, GPU allocation, output quality,
cold-start behavior and latency of a real deployment remain unverified. A live
ComfyUI server/browser workflow execution has not been performed in this session.

The implemented protocol is synchronous image generation/editing with Bearer auth
and `data[0].b64_json` or `data[0].url` responses. An asynchronous service or another
protocol needs an adapter based on its documented API.

Once the dedicated service is configured, use:

```bash
.venv/bin/python scripts/smoke_dedicated.py --model YOUR_DEPLOYED_MODEL_ID
# Also exercise editing, if the deployed service supports it:
.venv/bin/python scripts/smoke_dedicated.py --model YOUR_DEPLOYED_MODEL_ID --edit-model YOUR_EDIT_MODEL_ID
```

These commands make real inference requests. They exercise the node methods directly;
ComfyUI workflow execution should then be checked with the provided example workflow.
