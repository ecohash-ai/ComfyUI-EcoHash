import wave

try:
    from ..ecohash import catalog, client, conversions
except ImportError:
    from ecohash import catalog, client, conversions

from .dedicated import DedicatedNode, MODEL_INPUT, model_id


def _get_text(out):
    """Guard: extract 'text' from response, raise EcoHashError if missing."""
    text = out.get("text")
    if not isinstance(text, str):
        try:
            from ..ecohash.client import EcoHashError
        except ImportError:
            from ecohash.client import EcoHashError
        raise EcoHashError("Inference API returned no transcription text. The audio may be silent or in an unsupported language; check that the API returns a JSON text field.")
    return text


def _tts_inputs(model_input, voice=""):
    return {
        "required": {
            "model": model_input,
            "text": ("STRING", {"multiline": True, "default": ""}),
            "voice": ("STRING", {"default": voice, "tooltip": "Voice ID supported by the selected model"}),
            "speed": ("FLOAT", {"default": 1.0, "min": 0.5, "max": 2.0, "step": 0.05}),
        }
    }


def _speak(model, text, voice, speed, endpoint=None):
    if not voice.strip():
        raise client.EcoHashError("Choose or enter a voice ID supported by the selected TTS model. Use the node's model information for available voices.")
    options = {"endpoint": endpoint} if endpoint is not None else {}
    wav = client.request_bytes("POST", "/audio/speech", json_body={
        "model": model, "input": text, "voice": voice,
        "response_format": "wav", "speed": speed,
    }, **options)
    try:
        return (conversions.wav_bytes_to_audio(wav),)
    except (ValueError, wave.Error, EOFError):
        raise client.EcoHashError("Speech API returned unsupported audio. Expected a 16-bit PCM WAV response (response_format=wav).") from None


class EcoHashTTS:
    CATEGORY = "EcoHash/PublicModels"
    FUNCTION = "speak"
    RETURN_TYPES = ("AUDIO",)
    DESCRIPTION = "Generate speech through the public EcoHash API. Voice IDs are model-specific; discovery shows available voices when supplied by the service."

    @classmethod
    def INPUT_TYPES(cls):
        return _tts_inputs((catalog.model_ids("speech_tts"),))

    def speak(self, model, text, voice, speed):
        return _speak(model, text, voice, speed)


def _stt_inputs(model_input):
    return {
        "required": {
            "audio": ("AUDIO",),
            "model": model_input,
            "language": ("STRING", {"default": "", "tooltip": "ISO-639-1 code, empty = auto-detect"}),
        }
    }


def _transcribe(audio, model, language, endpoint=None):
    wav = conversions.audio_to_wav_bytes(audio)
    data = {"model": model}
    if language.strip():
        data["language"] = language.strip()
    options = {"endpoint": endpoint} if endpoint is not None else {}
    out = client.request_json("POST", "/audio/transcriptions",
                              data=data, files={"file": ("audio.wav", wav, "audio/wav")}, **options)
    return (_get_text(out),)


class EcoHashSTT:
    CATEGORY = "EcoHash/PublicModels"
    FUNCTION = "transcribe"
    RETURN_TYPES = ("STRING",)
    DESCRIPTION = "Transcribe one audio clip through the public EcoHash API. Leave language blank for automatic detection."

    @classmethod
    def INPUT_TYPES(cls):
        return _stt_inputs((catalog.model_ids("speech_stt"),))

    def transcribe(self, audio, model, language):
        return _transcribe(audio, model, language)


class EcoHashDedicatedTTS(DedicatedNode, EcoHashTTS):
    DESCRIPTION = "Generate speech using a dedicated model. Choose its connection, deployed model ID and supported voice ID. The endpoint must return 16-bit PCM WAV audio."

    @classmethod
    def INPUT_TYPES(cls):
        inputs = _tts_inputs(MODEL_INPUT, voice="")
        inputs["optional"] = {"connection": cls.connection_input()}
        return inputs

    def speak(self, model, text, voice, speed, connection="dedicated"):
        return _speak(model_id(model), text, voice, speed, client.load_dedicated_endpoint(connection))


class EcoHashDedicatedSTT(DedicatedNode, EcoHashSTT):
    DESCRIPTION = "Transcribe one audio clip using a dedicated model. Choose its connection and deployed model ID. Leave language blank for automatic detection."

    @classmethod
    def INPUT_TYPES(cls):
        inputs = _stt_inputs(MODEL_INPUT)
        inputs["optional"] = {"connection": cls.connection_input()}
        return inputs

    def transcribe(self, audio, model, language, connection="dedicated"):
        return _transcribe(audio, model_id(model), language, client.load_dedicated_endpoint(connection))
