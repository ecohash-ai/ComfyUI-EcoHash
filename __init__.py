import os
import sys

# ComfyUI loads this file via importlib.util.spec_from_file_location, which does
# not add this package's own directory to sys.path. Without this, the absolute
# imports below (`ecohash_nodes`, `ecohash`) would not resolve inside a real
# ComfyUI install (though they do resolve under pytest, since pytest's rootdir
# insertion already covers it). Insert it explicitly so both contexts work.
# NOTE: this package's node subpackage is deliberately named `ecohash_nodes`,
# not `nodes` -- ComfyUI itself has a top-level module named `nodes` (its core
# nodes.py), and a same-named subpackage here would silently resolve to that
# module instead of ours once ComfyUI has already imported it.
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

from ecohash_nodes.audio_nodes import EcoHashSTT, EcoHashTTS
from ecohash_nodes.image_nodes import EcoHashImageEdit, EcoHashImageGenerate
from ecohash_nodes.llm_nodes import EcoHashLLM, EcoHashVLMDescribe

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
