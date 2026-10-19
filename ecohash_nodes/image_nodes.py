import hashlib
import json

try:
    from ..ecohash import catalog, client, conversions
except ImportError:
    from ecohash import catalog, client, conversions

SIZES = ["1024x1024", "1024x768", "768x1024", "768x768", "512x512"]


def _image_result(out, endpoint=None):
    data = out.get("data") or []
    item = data[0] if isinstance(data, list) and data and isinstance(data[0], dict) else {}
    try:
        if item.get("b64_json"):
            return conversions.b64_to_image_tensor(item["b64_json"])
        if item.get("url"):
            timeout = endpoint.timeout if endpoint is not None else 180
            image_bytes = client.download_image(item["url"], timeout=timeout)
            return conversions.image_bytes_to_tensor(image_bytes)
    except client.EcoHashError:
        raise
    except (ValueError, TypeError, OSError):
        raise client.EcoHashError("Inference API returned invalid image data. Expected base64 image bytes or a downloadable image URL.") from None
    raise client.EcoHashError(
        "Inference API returned no image data. Expected data[0].b64_json or data[0].url; "
        "check the response format, or try a different prompt."
    )


def _generate_inputs(model_input):
    return {
        "required": {
            "model": model_input,
            "prompt": ("STRING", {"multiline": True, "default": ""}),
            "size": (SIZES, {"default": "1024x1024"}),
            "steps": ("INT", {"default": 0, "min": 0, "max": 100,
                              "tooltip": "0 = model default"}),
            "seed": ("INT", {"default": -1, "min": -1, "max": 2**31 - 1,
                             "tooltip": "-1 = random"}),
        }
    }


def _edit_inputs(model_input):
    return {
        "required": {
            "image": ("IMAGE",),
            "model": model_input,
            "prompt": ("STRING", {"multiline": True, "default": ""}),
            "size": (["auto"] + SIZES, {
                "default": "auto",
                "tooltip": "auto = send the source image dimensions (the service may round them)",
            }),
        }
    }


def _deployed_model_id(model):
    model = model.strip()
    if not model:
        raise client.EcoHashError("Enter the deployed model ID in the dedicated image node's model field.")
    return model


def _generate(model, prompt, size, steps, seed, endpoint=None):
    body = {"model": model, "prompt": prompt, "size": size, "response_format": "b64_json"}
    if steps > 0:
        body["steps"] = steps
    if seed >= 0:
        body["seed"] = seed
    options = {"endpoint": endpoint} if endpoint is not None else {}
    out = client.request_json("POST", "/images/generations", json_body=body, **options)
    return (_image_result(out, endpoint),)


def _edit(image, model, prompt, size, endpoint=None):
    png = conversions.image_tensor_to_png_bytes(image)
    data = {"model": model, "prompt": prompt}
    if size == "auto":
        # The public API defaults to 1024x1024 when size is omitted. Send the
        # source dimensions explicitly (the server may round to its own multiple).
        height, width = image.shape[1], image.shape[2]
        data["size"] = f"{width}x{height}"
    else:
        data["size"] = size
    options = {"endpoint": endpoint} if endpoint is not None else {}
    out = client.request_json(
        "POST", "/images/edits", data=data,
        files={"image": ("input.png", png, "image/png")}, **options,
    )
    return (_image_result(out, endpoint),)


class EcoHashImageGenerate:
    CATEGORY = "EcoHash"
    FUNCTION = "generate"
    RETURN_TYPES = ("IMAGE",)

    @classmethod
    def INPUT_TYPES(cls):
        return _generate_inputs((catalog.model_ids("image"),))

    def generate(self, model, prompt, size, steps, seed):
        return _generate(model, prompt, size, steps, seed)


class EcoHashImageEdit:
    CATEGORY = "EcoHash"
    FUNCTION = "edit"
    RETURN_TYPES = ("IMAGE",)

    @classmethod
    def INPUT_TYPES(cls):
        edit_models = [
            m["model_id"] for m in catalog.models_where(category="image", supports_image_edit=True)
            if m.get("model_id")
        ]
        return _edit_inputs((edit_models or ["(catalog unavailable)"],))

    def edit(self, image, model, prompt, size):
        return _edit(image, model, prompt, size)


_DEPLOYED_MODEL_INPUT = ("STRING", {
    "default": "",
    "tooltip": "Exact model ID served by your dedicated endpoint; it need not appear in the public EcoHash catalog.",
})


class _DedicatedImageNode:
    CATEGORY = "EcoHash/Dedicated"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # A changed destination/credential must invalidate cached images even if
        # workflow widgets are unchanged. Keep credentials out of cache metadata.
        endpoint = client.load_dedicated_endpoint()
        settings = json.dumps([endpoint.base_url, endpoint.api_key, endpoint.timeout])
        return hashlib.sha256(settings.encode()).hexdigest()


class EcoHashDedicatedImageGenerate(_DedicatedImageNode, EcoHashImageGenerate):
    DESCRIPTION = "Generate images using the dedicated inference endpoint configured outside the workflow."

    @classmethod
    def INPUT_TYPES(cls):
        return _generate_inputs(_DEPLOYED_MODEL_INPUT)

    def generate(self, model, prompt, size, steps, seed):
        model = _deployed_model_id(model)
        return _generate(model, prompt, size, steps, seed, client.load_dedicated_endpoint())


class EcoHashDedicatedImageEdit(_DedicatedImageNode, EcoHashImageEdit):
    DESCRIPTION = "Edit images using the dedicated inference endpoint configured outside the workflow."

    @classmethod
    def INPUT_TYPES(cls):
        return _edit_inputs(_DEPLOYED_MODEL_INPUT)

    def edit(self, image, model, prompt, size):
        model = _deployed_model_id(model)
        return _edit(image, model, prompt, size, client.load_dedicated_endpoint())
