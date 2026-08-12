from unittest.mock import patch

import pytest

from ecohash_nodes import image_nodes
from tests.test_conversions import _png_b64  # reuse fixture helper


@pytest.fixture(autouse=True)
def fake_catalog(monkeypatch):
    monkeypatch.setattr(image_nodes.catalog, "model_ids", lambda *c: ["qwen-image", "flux2-klein"])
    monkeypatch.setattr(
        image_nodes.catalog, "models_where",
        lambda **kw: [{"model_id": "flux2-klein", "category": "image", "supports_image_edit": True}],
    )


def test_generate_calls_endpoint_and_returns_image():
    node = image_nodes.EcoHashImageGenerate()
    with patch.object(image_nodes.client, "request_json") as mock_req:
        mock_req.return_value = {"data": [{"b64_json": _png_b64()}]}
        (img,) = node.generate(model="qwen-image", prompt="a fox", size="1024x1024", steps=0, seed=-1)
    assert img.shape[3] == 3
    body = mock_req.call_args.kwargs["json_body"]
    assert body == {"model": "qwen-image", "prompt": "a fox", "size": "1024x1024",
                    "response_format": "b64_json"}  # steps=0 / seed=-1 must be omitted
    assert mock_req.call_args.args == ("POST", "/images/generations")


def test_generate_passes_steps_and_seed_when_set():
    node = image_nodes.EcoHashImageGenerate()
    with patch.object(image_nodes.client, "request_json") as mock_req:
        mock_req.return_value = {"data": [{"b64_json": _png_b64()}]}
        node.generate(model="qwen-image", prompt="p", size="512x512", steps=8, seed=42)
    body = mock_req.call_args.kwargs["json_body"]
    assert body["steps"] == 8 and body["seed"] == 42


def test_edit_sends_multipart():
    from ecohash import conversions
    node = image_nodes.EcoHashImageEdit()
    src = conversions.b64_to_image_tensor(_png_b64())
    with patch.object(image_nodes.client, "request_json") as mock_req:
        mock_req.return_value = {"data": [{"b64_json": _png_b64()}]}
        (img,) = node.edit(image=src, model="flux2-klein", prompt="sunset sky", size="1024x1024")
    assert mock_req.call_args.args == ("POST", "/images/edits")
    kwargs = mock_req.call_args.kwargs
    assert kwargs["data"]["model"] == "flux2-klein"
    assert kwargs["data"]["size"] == "1024x1024"
    assert kwargs["files"]["image"][0] == "input.png"


def test_input_types_use_catalog():
    kinds = image_nodes.EcoHashImageGenerate.INPUT_TYPES()
    assert kinds["required"]["model"][0] == ["qwen-image", "flux2-klein"]
    edit_kinds = image_nodes.EcoHashImageEdit.INPUT_TYPES()
    assert edit_kinds["required"]["model"][0] == ["flux2-klein"]


def test_generate_raises_on_empty_data():
    from ecohash.client import EcoHashError
    node = image_nodes.EcoHashImageGenerate()
    with patch.object(image_nodes.client, "request_json") as mock_req:
        mock_req.return_value = {"data": []}
        with pytest.raises(EcoHashError, match="no image data"):
            node.generate(model="qwen-image", prompt="a fox", size="1024x1024", steps=0, seed=-1)


def test_edit_raises_on_empty_data():
    from ecohash import conversions
    from ecohash.client import EcoHashError
    node = image_nodes.EcoHashImageEdit()
    src = conversions.b64_to_image_tensor(_png_b64())
    with patch.object(image_nodes.client, "request_json") as mock_req:
        mock_req.return_value = {"data": []}
        with pytest.raises(EcoHashError, match="no image data"):
            node.edit(image=src, model="flux2-klein", prompt="sunset sky", size="1024x1024")


def test_edit_auto_size_sends_source_dimensions():
    """This previously asserted that `auto` omits `size`. That was the bug: the API
    answers a missing size with 1024x1024 regardless of the source, so `auto` silently
    resized. `auto` now sends the source dimensions."""
    from ecohash import conversions
    node = image_nodes.EcoHashImageEdit()
    src = conversions.b64_to_image_tensor(_png_b64())
    height, width = src.shape[1], src.shape[2]
    with patch.object(image_nodes.client, "request_json") as mock_req:
        mock_req.return_value = {"data": [{"b64_json": _png_b64()}]}
        (img,) = node.edit(image=src, model="flux2-klein", prompt="sunset sky", size="auto")
    kwargs = mock_req.call_args.kwargs
    assert kwargs["data"]["size"] == f"{width}x{height}"
    assert kwargs["data"]["model"] == "flux2-klein"
    assert kwargs["data"]["prompt"] == "sunset sky"


def test_edit_auto_sends_source_dimensions(monkeypatch):
    """`auto` used to omit size, which the API answers with 1024x1024 regardless of the
    source (measured). It must send the real source dimensions instead."""
    from unittest.mock import patch
    import torch
    from ecohash_nodes import image_nodes
    from tests.test_conversions import _png_b64

    monkeypatch.setattr(
        image_nodes.catalog, "models_where",
        lambda **kw: [{"model_id": "flux2-klein"}],
    )
    node = image_nodes.EcoHashImageEdit()
    image = torch.rand(1, 768, 512, 3)  # H=768, W=512
    with patch.object(image_nodes.client, "request_json") as req:
        req.return_value = {"data": [{"b64_json": _png_b64()}]}
        node.edit(image=image, model="flux2-klein", prompt="p", size="auto")
    assert req.call_args.kwargs["data"]["size"] == "512x768"  # WxH, not HxW


def test_edit_explicit_size_is_passed_through(monkeypatch):
    from unittest.mock import patch
    import torch
    from ecohash_nodes import image_nodes
    from tests.test_conversions import _png_b64

    monkeypatch.setattr(
        image_nodes.catalog, "models_where",
        lambda **kw: [{"model_id": "flux2-klein"}],
    )
    node = image_nodes.EcoHashImageEdit()
    with patch.object(image_nodes.client, "request_json") as req:
        req.return_value = {"data": [{"b64_json": _png_b64()}]}
        node.edit(image=torch.rand(1, 64, 64, 3), model="flux2-klein", prompt="p", size="768x768")
    assert req.call_args.kwargs["data"]["size"] == "768x768"
