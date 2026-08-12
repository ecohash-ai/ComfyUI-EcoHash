def test_node_mappings_complete():
    # ComfyUI imports the repo folder as a package; simulate by importing the root module file
    import __init__ as root  # works because tests run from repo root with rootdir on sys.path
    assert set(root.NODE_CLASS_MAPPINGS) == {
        "EcoHashImageGenerate", "EcoHashImageEdit", "EcoHashLLM",
        "EcoHashVLMDescribe", "EcoHashTTS", "EcoHashSTT",
    }
    assert all(v for v in root.NODE_DISPLAY_NAME_MAPPINGS.values())
