# Example workflows

Open **Workflow → Browse Templates**, find this plugin, or drag a JSON file into the canvas.
Configure credentials in the **EcoHash** sidebar / **Connections** dialog before running.

- `text_to_image.json`: public Image Generate → Preview Image.
- `dedicated_text_to_image.json`: Dedicated Image Generate → Preview Image. Configure
  a connection, select it in the node, then replace `YOUR_DEPLOYED_MODEL_ID`.
- `enhance_then_generate.json`: public LLM prompt enhancement → Image Generate → Preview Image.
- `describe_and_regenerate.json`: Load Image → public VLM Describe → Image Generate → Preview Image.
- `tts_voiceover.json`: public TTS → Preview Audio.
- `text_to_video.json`: public text-to-video → Save Video (with audio).
- `dedicated_text_to_video.json`: dedicated text-to-video → Save Video. Select a connection,
  exact served model ID, duration and size. No protocol configuration is needed; the service
  handles model adaptation. Existing job IDs under Advanced settings resume polling/download
  instead of submitting a new generation. Native-only containers need a service-side adapter.
- `dedicated_enhance_then_generate.json`: Dedicated LLM → Dedicated Image Generate → Preview Image.
- `dedicated_describe_and_regenerate.json`: Load Image → Dedicated VLM Describe → Dedicated Image Generate → Preview Image.
- `dedicated_tts_voiceover.json`: Dedicated TTS → Preview Audio. Replace both model and voice placeholders.
- `dedicated_speech_roundtrip.json`: Dedicated TTS → Dedicated STT → Preview as Text, with an audio preview. Select each deployment's connection and replace model/voice placeholders.

`describe_and_regenerate.json` references ComfyUI's sample `example.png`; select your own
input if that file is absent (also applies to the Dedicated version). Dedicated examples start
with an empty connection selection; select a saved connection per node. Models on different
instances can use different connections.
Dedicated STT accepts AUDIO from Load Audio, a TTS node or another audio source; its STRING output
can feed a Dedicated LLM or an image prompt. A shared
workflow contains only connection IDs and model IDs; recipients configure matching IDs
locally or select existing connections. Endpoint keys are excluded from all examples.

Image examples include optional dimension/connection defaults, the seed companion control
and named widget values. The original public node-chain smoke test is recorded in
`../tests/SMOKE_RESULTS.md`. Dedicated and connection-manager verification is tracked in
`../tests/DEDICATED_RESULTS.md`.

See the [complete User Guide](../docs/USER_GUIDE.md) for step-by-step configuration,
all node parameters, task recovery, caching and deployment compatibility.
