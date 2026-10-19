# Dedicated inference and connection manager verification

- Date: 2026-10-19
- Branch: `feat/dedicated-inference`
- Environment: macOS arm64, Python 3.13.12, PyTorch 2.14.1, pytest 9.1.1
- Python: `.venv/bin/python -m pytest -q --tb=short` — **122 passed in 3.10s**
- Frontend: `node --test tests/test_ui.mjs` — **7 passed**
- Syntax/whitespace: `node --check web/ecohash.js`, `git diff --check` — passed

## Automated coverage

- Existing public image, LLM, VLM, TTS, STT, catalog and conversion checks pass.
- Eight node class names remain compatible with ComfyUI's package loader and its
  already-loaded core `nodes` module. Old Dedicated workflows default to `dedicated`.
- Environment, saved settings and INI precedence; named profiles; independent
  destinations and credentials; blank-key preservation; atomic writes with POSIX
  mode 0600; redacted settings responses and configuration errors.
- Missing workflow connection IDs produce explicit mapping errors. Changing a
  dedicated endpoint, key or timeout invalidates its cache fingerprint.
- Settings routes reject missing mutation headers and cross-origin writes. Connection
  testing sends only GET `/models`. Generation testing requires a model ID and explicit
  consent. An unsupported `/models` route leaves authentication/inference unverified
  and allows manual model IDs.
- Catalog schemas load without a network wait. Discovery and catalog caches refresh,
  report fallback status and respect credential changes. Model hints use supplied
  capabilities; unknown private capabilities are not inferred from model names.
- Real loopback HTTP checks verify generation JSON, edit multipart PNG upload,
  independent bearer credentials, custom dimensions, base64 results and URL downloads
  without inference credentials. Redirects, HTTP 202 jobs and malformed responses
  have actionable errors.
- Frontend helpers preserve Vue inspector option-array identity, restore conditional
  widget visibility under ComfyUI's hidden-type compatibility shim, retain missing
  aliases for remapping and provide localized capability hints.

The Python suite needs permission to bind temporary listeners on `127.0.0.1`.
The local HTTP services return synthetic images; they do not run a model.

## Running ComfyUI and browser checks

Used the existing installation at `/Users/litianshu/ComfyUI-Local`, listening on
`127.0.0.1:8188` with ComfyUI 0.42.1, frontend 1.55.18 and CPU mode. Updated the
installed plugin after confirming the queue was idle, preserving the original
`config.ini` and its public credential. All eight EcoHash nodes and the connection
API loaded.

- Created two named connections through the sidebar, each with a different local
  URL prefix and dummy credential. Test connection verified GET-only authentication;
  model refresh displayed the two fixture model IDs and editing capability.
- A separate, explicitly confirmed manager generation test displayed the synthetic
  red image and cleared consent after completion.
- All five packaged workflows appeared in ComfyUI's template browser. Loaded the
  Dedicated template, selected a connection/discovered model, expanded custom width
  and height, then queued it through the browser. The preview displayed a red 64×64
  fixture image and the node status changed to completed.
- The existing `enhance_then_generate` workflow loaded with its original model,
  prompt and mode. Switching to custom mode exposed the system prompt; switching
  back hid it. Its original mode was restored. Existing public workflows were not
  re-executed against the paid API during this verification.
- An actual ComfyUI graph ran Dedicated Generate → Dedicated Edit, routed to the two
  different profiles, with a PreviewImage output for each. History reported success
  for prompt `bd604c90-3af7-4767-abf1-76cd35bd7fd0`. Downloaded previews were checked
  as red `(255, 0, 0)` and green `(0, 255, 0)`, both 64×64. The fixture deliberately
  returns fixed-size images; this does not establish a model's dimension support.
- Removed both temporary profiles, stopped the fixture service and closed the new
  test workflow. The original workflow tabs and public credential remain available;
  the updated ComfyUI server remains running.

Browser screenshots from this local run are saved at
`/private/tmp/ecohash-comfyui-workflow.jpg` and
`/private/tmp/ecohash-connections.jpg` (temporary artifacts, not repository assets).

## Pending real deployment verification

No real dedicated endpoint or credential has been supplied yet. Model compatibility,
GPU allocation, output quality, cold starts and latency of a real deployment remain
unverified. The implemented protocol is synchronous image generation/editing with
Bearer auth and `data[0].b64_json` or `data[0].url` responses. An asynchronous service
or another protocol needs an adapter based on its API contract.

After configuring the real connection, run:

```bash
.venv/bin/python scripts/smoke_dedicated.py --connection studio --model YOUR_DEPLOYED_MODEL_ID
# Also exercise editing when the deployment supports it:
.venv/bin/python scripts/smoke_dedicated.py --connection studio --model YOUR_DEPLOYED_MODEL_ID --edit-model YOUR_EDIT_MODEL_ID
```

These commands make real inference requests. Then run the supplied Dedicated workflow
in ComfyUI using the same connection and model IDs.
