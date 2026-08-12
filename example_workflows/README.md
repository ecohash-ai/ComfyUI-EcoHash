# Example Workflows

Ready-to-load ComfyUI workflow JSON files (UI format — drag into the ComfyUI canvas, or use
Workflow → Open) demonstrating each EcoHash node:

- `text_to_image.json` — `EcoHashImageGenerate` → `PreviewImage`
- `enhance_then_generate.json` — `EcoHashLLM` (`prompt_enhance` mode) → `EcoHashImageGenerate` → `PreviewImage`
- `describe_and_regenerate.json` — `LoadImage` → `EcoHashVLMDescribe` → `EcoHashImageGenerate` → `PreviewImage`
- `tts_voiceover.json` — `EcoHashTTS` → `PreviewAudio`

These were hand-authored against the exact current ComfyUI workflow schema (node
`pos`/`size`/`inputs`/`outputs`/`properties`/`widgets_values`, and the `links` array format),
derived by inspecting real workflows shipped in the `comfyui-workflow-templates` package and
cross-checked node-by-node against a live ComfyUI instance's `/object_info` (input order, which
inputs are widgets vs. link-only sockets, and frontend-injected companion widgets such as
`control_after_generate`), not written from memory. They are validated to:

- parse as JSON,
- reference only real, registered node types (`EcoHash*` class names match
  `NODE_CLASS_MAPPINGS`; `PreviewImage`/`PreviewAudio`/`LoadImage` are ComfyUI built-ins),
- have `widgets_values` arrays of the correct length and order for each node's non-socket
  inputs, and
- have internally consistent `links` (every link's origin/target node, slot, and type agree on
  both ends).

The node chains they encode (`EcoHashLLM` → `EcoHashImageGenerate`, `EcoHashVLMDescribe` →
`EcoHashImageGenerate`, plain `EcoHashImageGenerate`, plain `EcoHashTTS`) were exercised live
against the real EcoHash API as part of the Task 9 smoke test (see `../tests/SMOKE_RESULTS.md`)
— the same node combinations, run through the HTTP API rather than a browser. What was **not**
done is a literal "load this exact file in a browser and click Queue" pass, since that requires
a GUI browser session this environment doesn't have. If you hit anything unexpected loading one
of these in ComfyUI's UI, please open an issue.

`describe_and_regenerate.json` uses `example.png`, the sample image ComfyUI ships by default in
its `input/` folder — swap in your own image via the `LoadImage` node's file picker.
