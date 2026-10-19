# Pre-release review — 2026-10-19

Branch: `feat/dedicated-inference`. Package version: **1.0.1**, unchanged.
This review does not publish or approve a 1.1.0 release.

## Findings fixed

- The connection manager allowed interaction before its initial asynchronous
  profile load finished. A late response could replace a new-connection draft.
  Initial loading now uses the manager's busy/inert state. Regression tests
  exercise the real manager handlers with a delayed profile response, two
  successive connection creations, and renaming without changing the ID.
- Public API failures could echo raw response text or a transport exception
  containing an Authorization value. Errors now extract limited JSON validation
  messages with active-key redaction, suppress raw transport/JSON exception
  context, and omit non-JSON response bodies. Video content errors pass their
  active credential to the same redaction path. Regression tests cover JSON
  validation errors, invalid headers, invalid JSON, and HTML error bodies.
- TTS error guidance still referenced the removed model-information row. It now
  points to model refresh, the voice selector, and capability tooltips.
- README and template instructions omitted video entries or referred to a
  default dedicated selection and removed information rows. They now match the
  current fourteen-node UI. The administrator request-mapping guide is in English.

## Automated verification

- `.venv/bin/python -m pytest -q`: **230 passed** in 11.52 seconds.
- `node --test tests/test_ui.mjs tests/test_manager.mjs`: **25 passed**.
- `node --check web/ecohash.js`: passed.
- `git diff --check`: passed.
- Guide checks: nineteen corresponding English/Chinese topics, all eleven
  bundled templates documented, valid local documentation links and HTML anchors,
  no duplicate HTML IDs, unchanged package version.

## Local ComfyUI verification

The fixed plugin was installed into the existing ComfyUI 0.42.1 test environment
and restarted only after its queue was found idle. Configuration-file hashes were
preserved by the installation helper. ComfyUI loaded all **fourteen** EcoHash
nodes and the existing public, image-instance and video-instance connections.

Read-only authenticated connection checks returned HTTP 200 for all three
connections. The official dedicated connections resolved the single global key.
The running node schemas contained no API-key, base-URL or protocol input fields.
Browser inspection confirmed the global-key setting, consistent connection names,
and no empty default dedicated endpoint in the connection list.

The Chinese review HTML was opened through a loopback-only local server. It has
nineteen working table-of-contents links, functioning directory search, readable
tables and workflow diagrams, no page-level horizontal overflow, no external
script/style dependency, and no captured browser console errors. Its files and
screenshots remain in the ignored `local-review/` directory and are not published.

## Scope and release boundary

No new billable inference was submitted during this pre-release review. Existing
dedicated image/video verification from this session is separate evidence;
in particular, a matching dedicated-video result was decoded successfully as
1344×768 H.264 at 24 fps, 107 frames, approximately 4.458 seconds, with AAC audio.
Those results establish the tested deployment/request, not every catalog model.

Remaining operation boundaries are documented in the User Guide: API nodes do
not expose native model/latent objects or arbitrary remote ComfyUI execution;
video nodes are text-only; model-native containers may need a deployment-owned
request mapping; discovery and pricing bands do not prove inference compatibility.
Platform routing and deployment availability remain service responsibilities.

No unresolved blocking regression was found within the checks above. Package
version changes, a 1.1.0 tag, and Registry publication are deferred until the
user approves the guide review. Only the current feature branch is pushed.
