from nodes.audio_nodes import EcoHashSTT, EcoHashTTS
from nodes.image_nodes import EcoHashImageEdit, EcoHashImageGenerate
from nodes.llm_nodes import EcoHashLLM, EcoHashVLMDescribe

NODE_CLASS_MAPPINGS = {
    "EcoHashImageGenerate": EcoHashImageGenerate,
    "EcoHashImageEdit": EcoHashImageEdit,
    "EcoHashLLM": EcoHashLLM,
    "EcoHashVLMDescribe": EcoHashVLMDescribe,
    "EcoHashTTS": EcoHashTTS,
    "EcoHashSTT": EcoHashSTT,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EcoHashImageGenerate": "EcoHash Image Generate",
    "EcoHashImageEdit": "EcoHash Image Edit",
    "EcoHashLLM": "EcoHash LLM",
    "EcoHashVLMDescribe": "EcoHash VLM Describe",
    "EcoHashTTS": "EcoHash TTS",
    "EcoHashSTT": "EcoHash STT",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
