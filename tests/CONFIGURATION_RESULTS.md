# Configuration and dynamic-model verification

Date: 2026-10-19. Local branch: `feat/dedicated-inference`.

- Python: `209 passed` (`.venv/bin/python -m pytest -q`).
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

The resume test above does not establish standard create-request compatibility for instance 247.
Its historical native-only creation success is recorded separately in `MINIMAX_247_RESULTS.md`.
The current platform routing/metadata gaps and node-by-node
configuration audit are documented in `../docs/CONFIGURATION_AUDIT.md`.
EcoLink source was inspected read-only; no backend changes were deployed.

## Original-prompt new-generation regression

The user's new-generation failure was reproduced: this instance requires a native `task`
despite its `/videos` route and generic OpenAPI schema. A declarative JSON request mapping
is now supported in the ComfyUI server's connection record. The actual instance-247 mapping
is local deployment data, bound to its exact URL, served model ID and the freshly returned
`pipeline_class`/`root`; no model-family rules were added to production code.

The original failed workflow was captured before restart. Its 565-character Chinese prompt
has SHA-256 `e0422d353d2e3cd2d7bcd7d08aa686f8913d67eb56a00a2390e745bab81e0dbb`.
A mapped 4-second/720p request was rejected with HTTP 400:
`target.short_edge must be 768 for minimax_h3, got 720`. No remote job was returned and the
plugin did not retry. The connection now explicitly declares `supported_resolutions: ["768p"]`;
incompatible resolutions are rejected locally before creation. This is an instance-specific
declared constraint, not a general rule about that model family.

After correcting the selected resolution to 768p, one new generation succeeded using the
unchanged original prompt and 4-second duration:

- ComfyUI prompt: `93bc6622-9455-4827-8adc-390d7366976f`, 80.35 seconds, no cached nodes.
- Remote job: `7f359bf4-4e50-4668-8aae-8e6748031a23`, completed, 100%.
- Saved output: `output/video/ComfyUI_00008_.mp4`, 2,290,930 bytes.
- Decoded video: H.264, 1344×768, 107 frames at 24 fps, 4.458 seconds.
- Decoded audio: AAC stereo, 32 kHz, 142,400 samples.
- Five sampled frames decoded successfully; they show the rain-soaked station, red coat,
  silver animal, umbrella and train. This verifies generation/transport/playback, not perfect
  adherence to every action in the long prompt within four seconds.

The saved workflow `EcoHash_H3_original_prompt_768p` was exported and its prompt verified
against the failed task. It has no protocol, steps or seed fields and contains no API key.
Both Model information and Connection status are absent from the refreshed node inspector.
Capability hints remain on the model selector and connection-manager model rows.
New unit tests cover exact deployment binding, runtime identity changes, typed JSON mapping,
prompt preservation, rounded preset ratios, declared limits, credential isolation, cache
invalidation and the single-POST JSON lifecycle. The 21 frontend tests also pass.

Local evidence: `/private/tmp/ecohash-minimax-247/original-failed-workflow.json`,
`original-prompt-retry-result.json` (720p rejection), `original-prompt-768p-result.json`,
`retry-768p-create-body.json`, `output-verification.json`, `original-prompt-768p.mp4`.
This is a local compatibility bridge; the EcoLink routing/metadata gaps described in the
audit remain. The plugin does not automatically configure mappings for other deployments.
