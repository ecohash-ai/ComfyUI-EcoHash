# Example Workflows

This folder will hold ready-to-load ComfyUI workflow JSON files (UI format, exported from
ComfyUI's "Save (API Format): off" export) demonstrating each EcoHash node:

- `text_to_image.json` — `EcoHashImageGenerate` → `PreviewImage`
- `enhance_then_generate.json` — `EcoHashLLM` (prompt_enhance mode) → `EcoHashImageGenerate` → `PreviewImage`
- `describe_and_regenerate.json` — `LoadImage` → `EcoHashVLMDescribe` → `EcoHashImageGenerate` → `PreviewImage`
- `tts_voiceover.json` — `EcoHashTTS` → `PreviewAudio`

These workflows will be exported from a live local ComfyUI install and committed during
Task 9, once the nodes have been exercised against the real EcoHash API. They are
intentionally omitted here rather than hand-written, so nothing in this folder is untested
or fabricated.
