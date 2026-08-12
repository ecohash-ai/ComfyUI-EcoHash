def test_node_mappings_complete():
    # ComfyUI loads the repo folder's __init__.py via importlib.util.spec_from_file_location
    # (see custom_nodes loading in ComfyUI's nodes.py); this imports the same file directly.
    import __init__ as root  # works because tests run from repo root with rootdir on sys.path
    assert set(root.NODE_CLASS_MAPPINGS) == {
        "EcoHashImageGenerate", "EcoHashImageEdit", "EcoHashLLM",
        "EcoHashVLMDescribe", "EcoHashTTS", "EcoHashSTT",
    }
    assert all(v for v in root.NODE_DISPLAY_NAME_MAPPINGS.values())
