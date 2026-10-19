# EcoHash Dedicated STT

Connect one AUDIO clip, choose a dedicated connection and enter its deployed model ID.
Leave language blank for auto-detection, or enter an ISO-639-1 code such as `zh` or `en`.

The node sends `POST {base_url}/audio/transcriptions` with Bearer auth and multipart
fields `model`, optional `language`, and `file` containing a WAV. The service must
return JSON with a string `text` field. The STRING output can feed an LLM or image prompt.
