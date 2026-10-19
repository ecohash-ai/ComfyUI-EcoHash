# Example workflows

Open **Workflow → Browse Templates**, find this plugin, or drag a JSON file into the canvas.
Configure credentials in the **EcoHash** sidebar / **Connections** dialog before running.

- `text_to_image.json`: public Image Generate → Preview Image.
- `dedicated_text_to_image.json`: Dedicated Image Generate → Preview Image. Configure
  `dedicated` (or choose a named connection), then replace `YOUR_DEPLOYED_MODEL_ID`.
- `enhance_then_generate.json`: public LLM prompt enhancement → Image Generate → Preview Image.
- `describe_and_regenerate.json`: Load Image → public VLM Describe → Image Generate → Preview Image.
- `tts_voiceover.json`: public TTS → Preview Audio.

`describe_and_regenerate.json` references ComfyUI's sample `example.png`; select your own
input if that file is absent. Each Dedicated node can select its own connection. A shared
workflow contains only connection IDs and model IDs; recipients configure matching IDs
locally or select existing connections. Endpoint keys are excluded from all examples.

Image examples include optional dimension/connection defaults, the seed companion control
and named widget values. The original public node-chain smoke test is recorded in
`../tests/SMOKE_RESULTS.md`. Dedicated and connection-manager verification is tracked in
`../tests/DEDICATED_RESULTS.md`.
