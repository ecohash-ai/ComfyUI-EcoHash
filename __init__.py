# ComfyUI loads this file via importlib.util.spec_from_file_location with
# submodule_search_locations set to this directory, which makes this file the
# __init__ of a real package -- so relative imports below resolve correctly
# inside a real ComfyUI install. Under pytest (and any other direct/top-level
# load of this file, e.g. `import __init__`), there is no parent package, so
# the relative form raises ImportError and we fall back to the absolute form,
# which resolves because pytest puts the repo root on the import path.
# NOTE: this package's node subpackage is deliberately named `ecohash_nodes`,
# not `nodes` -- ComfyUI itself has a top-level module named `nodes` (its core
# nodes.py), and a same-named subpackage here would silently resolve to that
# module instead of ours once ComfyUI has already imported it.
try:
    from .ecohash_nodes.audio_nodes import EcoHashSTT, EcoHashTTS
    from .ecohash_nodes.image_nodes import EcoHashImageEdit, EcoHashImageGenerate
    from .ecohash_nodes.llm_nodes import EcoHashLLM, EcoHashVLMDescribe
except ImportError:  # direct/pytest context where this file is not loaded as a package
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
