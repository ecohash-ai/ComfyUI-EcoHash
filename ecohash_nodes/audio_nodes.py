try:
    from ..ecohash import catalog, client, conversions
except ImportError:
    from ecohash import catalog, client, conversions


def _get_text(out):
    """Guard: extract 'text' from response, raise EcoHashError if missing."""
    text = out.get("text")
    if text is None:
        try:
            from ..ecohash.client import EcoHashError
        except ImportError:
            from ecohash.client import EcoHashError
        raise EcoHashError("EcoHash returned no transcription. The audio may be silent or in an unsupported language; try again with clearer audio.")
    return text


class EcoHashTTS:
    CATEGORY = "EcoHash"
    FUNCTION = "speak"
    RETURN_TYPES = ("AUDIO",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": (catalog.model_ids("speech_tts"),),
                "text": ("STRING", {"multiline": True, "default": ""}),
                "voice": ("STRING", {"default": "af_bella",
                                     "tooltip": "Voice ID supported by the selected model"}),
                "speed": ("FLOAT", {"default": 1.0, "min": 0.5, "max": 2.0, "step": 0.05}),
            }
        }

    def speak(self, model, text, voice, speed):
        wav = client.request_bytes("POST", "/audio/speech", json_body={
            "model": model, "input": text, "voice": voice,
            "response_format": "wav", "speed": speed,
        })
        return (conversions.wav_bytes_to_audio(wav),)


class EcoHashSTT:
    CATEGORY = "EcoHash"
    FUNCTION = "transcribe"
    RETURN_TYPES = ("STRING",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "model": (catalog.model_ids("speech_stt"),),
                "language": ("STRING", {"default": "",
                                        "tooltip": "ISO-639-1 code, empty = auto-detect"}),
            }
        }

    def transcribe(self, audio, model, language):
        wav = conversions.audio_to_wav_bytes(audio)
        data = {"model": model}
        if language.strip():
            data["language"] = language.strip()
        out = client.request_json("POST", "/audio/transcriptions",
                                  data=data, files={"file": ("audio.wav", wav, "audio/wav")})
        return (_get_text(out),)
