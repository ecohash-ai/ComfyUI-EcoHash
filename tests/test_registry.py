def test_node_mappings_complete():
    # ComfyUI loads the repo folder's __init__.py via importlib.util.spec_from_file_location
    # (see custom_nodes loading in ComfyUI's nodes.py); this imports the same file directly.
    import __init__ as root  # works because tests run from repo root, which pytest puts on the import path
    assert set(root.NODE_CLASS_MAPPINGS) == {
        "EcoHashImageGenerate", "EcoHashImageEdit", "EcoHashLLM",
        "EcoHashVLMDescribe", "EcoHashTTS", "EcoHashSTT",
        "EcoHashDedicatedImageGenerate", "EcoHashDedicatedImageEdit",
        "EcoHashDedicatedLLM", "EcoHashDedicatedVLMDescribe",
        "EcoHashDedicatedTTS", "EcoHashDedicatedSTT",
    }
    assert all(v for v in root.NODE_DISPLAY_NAME_MAPPINGS.values())


def test_comfyui_package_loading(monkeypatch):
    import importlib.util
    from pathlib import Path
    import sys
    import types

    # Match ComfyUI's importlib loader, including its already-loaded core nodes module.
    monkeypatch.setitem(sys.modules, "nodes", types.ModuleType("nodes"))
    name = "_ecohash_test_plugin"
    path = Path(__file__).resolve().parent.parent / "__init__.py"
    spec = importlib.util.spec_from_file_location(name, path, submodule_search_locations=[str(path.parent)])
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    try:
        spec.loader.exec_module(module)
        for node_id in (name for name in module.NODE_CLASS_MAPPINGS if name.startswith("EcoHashDedicated")):
            node = module.NODE_CLASS_MAPPINGS[node_id]
            assert node.__module__.startswith(name + ".")
            assert node.INPUT_TYPES()["required"]["model"][0] == "STRING"
    finally:
        for key in list(sys.modules):
            if key.startswith(name + "."):
                del sys.modules[key]
