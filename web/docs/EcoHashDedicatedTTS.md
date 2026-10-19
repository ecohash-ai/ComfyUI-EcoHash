# EcoHash Dedicated TTS

Select a dedicated connection and enter the deployed speech model ID, text and voice ID.
**Choose voice** lists voices when the endpoint supplies them; otherwise enter a voice
supported by that model. No public-model voice is assumed for a private model.

The service must support synchronous `POST {base_url}/audio/speech` with Bearer auth,
`model`, `input`, `voice`, `speed` and `response_format=wav`. It must return 16-bit PCM
WAV bytes. Connect AUDIO to Preview Audio, Save Audio or a transcription node.
