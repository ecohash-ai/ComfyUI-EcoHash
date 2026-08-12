# Live Smoke Test Results

- Date: 2026-08-12 11:10 UTC
- ComfyUI base URL: http://127.0.0.1:8188
- ComfyUI version: 0.32.0 (comfyanonymous/ComfyUI @ `bd34f338ac505ea79e43968753968a464060e609`, cloned `--depth 1`)
- ComfyUI run mode: `--cpu --port 8188` (CPU-only; the EcoHash nodes never run local inference,
  so this only affects how ComfyUI itself starts up)
- Models exercised: `z-image-turbo` (image), `flux2-klein` (image edit), `qwen3-vl-8b-instruct`
  (VLM describe), `GLM-5.2` (LLM, `prompt_enhance` mode), `kokoro-82m` (TTS), `whisper-large-v3-turbo`
  (STT) — all confirmed present in both the packaged catalog snapshot and the live
  `api.ecohash.com/platform/models` catalog at test time.

## Packaging bug found and fixed during this test run

The plugin **could not load at all** in a real ComfyUI install before this task. ComfyUI's own
core module is named `nodes` (`ComfyUI/nodes.py`), and this package's node subpackage was also
named `nodes/`. `__init__.py`'s `from nodes.audio_nodes import ...` therefore resolved to
ComfyUI's own core module (already present in `sys.modules` by the time custom nodes load), not
to this package's subpackage, raising `ModuleNotFoundError: No module named 'nodes.audio_nodes';
'nodes' is not a package`. Fixed by renaming the subpackage to `ecohash_nodes/` and adding an
explicit `sys.path` entry for this package's own directory in `__init__.py` (ComfyUI loads
`__init__.py` via `importlib.util.spec_from_file_location`, which does not add the plugin's own
directory to `sys.path`, unlike pytest's rootdir insertion that let the existing unit tests pass
despite this bug). Full unit suite (43 tests) still passes after the rename. See commit history
for the exact diff.

## Per-node results

| Graph | Node ID | EcoHash Node | Result | Detail |
|---|---|---|---|---|
| image_chain | 1 | EcoHashImageGenerate | PASS | ok |
| image_chain | 2 | EcoHashImageEdit | PASS | ok |
| image_chain | 4 | EcoHashVLMDescribe | PASS | ok |
| llm_prompt_enhance | 1 | EcoHashLLM | PASS | ok |
| tts_then_stt | 1 | EcoHashTTS | PASS | ok |
| tts_then_stt | 3 | EcoHashSTT | PASS | ok |

## Graph durations

- `image_chain`: 20.2s (ImageGenerate → ImageEdit → PreviewImage, and ImageGenerate → VLMDescribe → PreviewAny)
- `llm_prompt_enhance`: 20.1s (LLM → PreviewAny)
- `tts_then_stt`: 6.0s (TTS → PreviewAudio, and TTS → STT → PreviewAny)

**6/6 EcoHash node checks passed.**

## Evidence (no key material)

- **ImageGenerate** (`z-image-turbo`, prompt "a small red apple on a plain white background,
  product photo", 512x512): produced a 1024x1024-appearing RGB image (loaded fine as an IMAGE
  tensor); passed on to both ImageEdit and VLMDescribe.
- **ImageEdit** (`flux2-klein`, prompt "make the apple bright green", `size=auto`): output image
  visually confirmed as a bright green apple (source was red) — the edit instruction was followed
  correctly.
- **VLMDescribe** (`qwen3-vl-8b-instruct`, fed the *original* generated image, not the edited
  one): returned `"A glossy, vibrant red apple with a short stem sits centered against a plain
  white background."` — correctly describes the pre-edit (red) image it was actually given.
- **LLM** (`GLM-5.2`, `prompt_enhance` mode, input "a cat astronaut floating above the moon"):
  returned a detailed English image-generation prompt starting `"A cinematic, hyper-realistic
  portrait of a fluffy orange tabby cat astronaut wearing a custom-fit futuristic white
  spacesuit..."`.
- **TTS** (`kokoro-82m`, text "Hello from the EcoHash smoke test.", voice `af_bella`): returned a
  16-bit WAV/FLAC-savable audio clip; loaded fine as an AUDIO dict and played back via
  PreviewAudio.
- **STT** (`whisper-large-v3-turbo`, fed the TTS output audio directly, no LoadImage/LoadAudio
  round-trip through disk): returned `"Hello from the EcoHash smoke test."` — an exact
  round-trip match of the TTS input text.

No platform-side anomalies (rate limits, 5xx, content filtering) were observed in this run.

