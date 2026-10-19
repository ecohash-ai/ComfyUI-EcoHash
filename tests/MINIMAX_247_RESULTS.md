# MiniMax-H3 dedicated instance 247 — video verification

- Date: 2026-10-19
- Branch: `feat/dedicated-inference`
- User-supplied gateway ID: `/mnt/shared/MiniMaxAI/MiniMax-H3:247`.
- Credential: existing local EcoHash key, explicitly configured in a separate
  `minimax-h3-247` connection. No key is stored in workflow exports or this repository.

## Route and model-ID findings

1. Authenticated `GET https://api.ecohash.com/v1/models` returned the exact supplied
   model ID. Its `:247` suffix is correct for the EcoHash gateway model list.
2. `POST https://api.ecohash.com/v1/video/generations` using that ID returned
   **404**, `{"error":"model not found or not active"}`. No job ID was created.
   Model discovery alone therefore does not establish that this route can serve it.
3. The instance proxy's `/v1/models` returned the raw ID
   `/mnt/shared/MiniMaxAI/MiniMax-H3`. The proxy already selects instance 247:
   `https://api.ecohash.com/inference-instances/247/proxy/v1`.
4. The instance's OpenAPI exposed `/v1/videos`, `/{id}`, and `/{id}/content`.
   Its generic multipart schema does not document all native H3 JSON fields.
   An explicit `fps` parameter was rejected with HTTP 400 because H3 derives its
   temporal shape from `target.duration_seconds`; that rejected request created no job.
5. The corrected native JSON request follows the
   [official SGLang H3 contract](https://github.com/sgl-project/sglang/blob/main/docs/cookbook/diffusion/MiniMax/MiniMax-H3.mdx)
   and was accepted. It uses the raw model ID without the gateway suffix.

## Real API generation

Request to `POST {instance_proxy_prefix}/videos`:

```json
{
  "model": "/mnt/shared/MiniMaxAI/MiniMax-H3",
  "prompt": "An orange cat wearing a blue scarf sits in a neon-lit alley after rain. The cat slowly turns its head toward the camera and blinks. Rain droplets fall from an awning, colorful reflections shimmer on the wet pavement. A gentle slow camera push-in. Natural ambient rain and a soft cat meow. Cinematic photorealistic style, no visible text, logos or watermarks.",
  "seconds": 4,
  "task": "t2va",
  "conditions": [],
  "target": {"short_edge": 768, "aspect_ratio": "16:9", "duration_seconds": 4.0},
  "num_outputs_per_prompt": 1,
  "num_inference_steps": 50,
  "flow_shift": 12,
  "audio_flow_shift": 3,
  "seed": 42
}
```

- HTTP 200, asynchronous job **`3726b91b-196b-4faf-a064-e199cd82e439`**.
- Polling returned `completed`; server-reported inference time **65.8477 s**.
- Downloaded its authenticated `/videos/{id}/content` route successfully.
- Full decode: **1344×768 H.264, 24 fps, 107 frames, 4.458333 s**; **AAC stereo,
  32 kHz**, 142400 decoded samples. The server aligned the requested 4 s duration.
- Extracted frames confirm a blue-scarf orange cat turning toward the camera and
  blinking in a wet neon alley. Audio format/decoding was verified; semantic audio
  quality was not assessed by listening.
- Artifacts: `/private/tmp/ecohash-minimax-247/minimax-h3-247-cat.mp4`,
  `video-frames.jpg`, `media-check.json`, native request/submission/status records.

## Plugin implementation

- Added `EcoHashVideoGenerate` and `EcoHashDedicatedVideoGenerate`, bringing the
  registry to fourteen nodes, seven per public/dedicated group. Existing IDs remain.
- Protocols: EcoHash JSON `/video/generations`, OpenAI-style multipart `/videos`,
  and native SGLang H3 JSON `/videos`. All submit once and poll an accepted job.
- Outputs are ComfyUI `VIDEO` plus job-ID `STRING`. Native **Save Video** supplies
  playback and permanent saving with audio. Downloads use the ComfyUI temp directory.
- Separate total wait and per-request timeouts; local cancellation; resumable job ID;
  failed-job errors; invalid-status/content checks; partial-file cleanup; 512 MiB limit.
  No automatic POST retry or protocol fallback that might duplicate generation.
- Only an API's own constructed content route receives its key. Returned download
  URLs and all content redirects are fetched without inference credentials.
- Dedicated connections reuse existing configuration, discovery and credential-based
  cache invalidation. Conditional widgets expose only the chosen protocol's controls.
- Added public/dedicated text-to-video example workflows and Chinese labels/help.

Reference-dependent video generation is not implemented by these text-only nodes.
Real public-video and generic OpenAI-video services are not established by the H3
test; those protocol lifecycles are covered with synthetic loopback HTTP responses.

## Running ComfyUI verification

Updated the existing ComfyUI 0.42.1 / frontend 1.55.18 installation, preserving its
credentials and existing workflows. It loaded all fourteen EcoHash nodes. Added
the named instance connection and saved **MiniMax_H3_EcoHash_247**:
`EcoHashDedicatedVideoGenerate → SaveVideo`.

- Queued a new generation through the browser using `minimax_h3`, the raw model ID,
  4 requested seconds, 16:9, 50 steps, seed 42 and a blank `job_id`.
- ComfyUI prompt **`38f56fa3-2b8a-4232-bfc3-b332c5b5545e`** succeeded in
  **74.337 s**. Remote job: **`b11771a7-8dfe-4ee6-a1e6-e1f56afc6de0`**.
- Save Video produced `output/video/EcoHash_MiniMax_247_00001_.mp4`; the player
  displayed the orange-cat clip. Full decode of this saved file verified 107 H.264
  frames, 1344×768 at 24 fps, 4.458333 s and stereo AAC at 32 kHz. Audio RMS was
  0.17443, so the decoded audio track is not silent.
- Entered that existing remote job ID and queued again. Prompt
  **`2b141217-fbb3-43e3-879e-57f62d328901`** succeeded in **16.395 s** and saved
  `_00002_.mp4` using the same remote job. The resume path performs only status and
  content GETs, with no new generation submission. Restored blank `job_id` afterward.
- Switched between all three protocol choices in the property inspector. EcoHash
  exposed resolution/audio/aspect ratio; OpenAI exposed width/height; H3 exposed
  aspect ratio and native step/seed controls. Restored H3 before saving.
- Export verified **15 core widget values**, including the fixed-seed companion
  control, without UI-only buttons/status fields or API credentials.
- Verified the library's 公共模型 / 专有模型 branches each include their video node.

Artifacts: `/private/tmp/ecohash-minimax-247/comfyui-minimax-h3-247.mp4`,
`minimax-h3-247-workflow.json`, `comfyui-result.json`, `comfyui-media-check.json`.

Automated verification: **166 Python tests**, **9 frontend helper tests**; JavaScript
syntax and `git diff --check` pass. Loopback video tests cover the three request
formats, HTTP 202, polling, credential isolation, auth-free result redirects, failure,
malformed status, timeout, cancellation, resume, malformed downloads, path injection
and no POST retry after a lost submission response. They use synthetic transport data;
the real MP4 decode and native Save Video integration are established by the run above.
