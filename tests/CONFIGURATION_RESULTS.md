# Configuration and dynamic-model verification

Date: 2026-10-19. Local branch: `feat/dedicated-inference`.

- Python: `194 passed` (`.venv/bin/python -m pytest -q`).
- Frontend helpers: `21 passed` (`node --test tests/test_ui.mjs`).
- JavaScript syntax and `git diff --check`: passed.

The tests cover metadata changes without model-name rules, newly introduced resolution
bands, the EcoLink coarse pricing-band expansion, models with unknown capabilities,
vision-capable chat metadata, connection normalization/prevalidation, redacted API errors,
old workflow values/link migration, credential isolation and video submission/resume.
Standard video transport tests use a loopback service, not paid model generation.

Local ComfyUI loaded all 14 nodes. Its `/object_info` had no protocol field on any EcoHash
node and no steps/seed on video nodes. Dedicated video API prompts had no protocol,
steps, seed, generate_audio or UI-only selector fields. Video workflow serialization
changed from 15 to 10 core values without shifting the selected connection or job ID.

The current public catalog and both configured dedicated connections returned HTTP 200.
The live catalog included the currently registered video models and their declared limits;
no model-family list was added to the plugin. The gateway connection uses
`/models?category=all`. Instance-proxy models without category/modalities remain unclassified.
Public pricing's `480_720p` expands to request values `480p` and `720p`, matching EcoLink's
`resolutionOptionsFromTiers`; the raw pricing key is not offered as a generation resolution.

In the browser, both the canvas and right-side inspector opened connection settings.
The form exposed display name, API URL and key; ID/timeout were under Advanced settings.
Saving applied the existing connection and loaded models, preserving the saved key.
Refreshing from the right inspector also worked. UI-only widget names use stable internal
identifiers with localized labels, avoiding the inspector callback issue with bilingual names.

An existing instance-247 job (`77e53335-6e37-4a3f-a428-24ccfea1655a`) was resumed with
the simplified node; no new generation was submitted. ComfyUI prompt
`3f0e26aa-fd82-4be9-be40-da77262103f2` succeeded in 6.834 seconds and saved
`output/video/ComfyUI_00002_.mp4`: 1344×768, 362 frames, 24 fps, 15.083 seconds.
The workflow's old 4k setting did not affect this resume; it did not generate a 4k video.

The original user workflow was saved separately as
`EcoHash_Video_before_simplify_20261019` (15 fields). The migrated resume example was saved
as `EcoHash_Video_simplified_resume_verified` (10 fields). Credentials were excluded from
both exports. Local evidence is stored in `/private/tmp/ecohash-simplified-result.json`
and `/private/tmp/ecohash-simplified-inspection.json`.

This verification does not establish standard create-request compatibility for instance 247.
Its historical native-only creation success is recorded separately in
`MINIMAX_247_RESULTS.md`. The current platform routing/metadata gaps and node-by-node
configuration audit are documented in `../docs/CONFIGURATION_AUDIT.md`.
EcoLink source was inspected read-only; no backend changes were deployed.
