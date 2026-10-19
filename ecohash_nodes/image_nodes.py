try:
    from ..ecohash import catalog, client, conversions
except ImportError:
    from ecohash import catalog, client, conversions

from .dedicated import DedicatedNode, MODEL_INPUT, model_id

SIZES = ["1024x1024", "1024x768", "768x1024", "768x768", "512x512", "1536x864", "864x1536", "custom"]


def _dimension_inputs():
    return {name: ("INT", {"default": 1024, "min": 64, "max": 8192, "step": 16,
                           "tooltip": "Used only when size = custom. Check the selected model's supported dimensions."})
            for name in ("width", "height")}


def _size(size, width, height):
    if size != "custom":
        return size
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 64 or value > 8192 or value % 16 for value in (width, height)):
        raise client.EcoHashError("Custom width and height must be multiples of 16 between 64 and 8192.")
    return f"{width}x{height}"


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
        },
        "optional": _dimension_inputs(),
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
        },
        "optional": _dimension_inputs(),
    }


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
    DESCRIPTION = "Generate an image through the public EcoHash API. Configure your key with the Connections button or EcoHash sidebar."

    @classmethod
    def INPUT_TYPES(cls):
        return _generate_inputs((catalog.model_ids("image"),))

    def generate(self, model, prompt, size, steps, seed, width=1024, height=1024):
        return _generate(model, prompt, _size(size, width, height), steps, seed)


class EcoHashImageEdit:
    CATEGORY = "EcoHash"
    FUNCTION = "edit"
    RETURN_TYPES = ("IMAGE",)
    DESCRIPTION = "Edit one image through the public EcoHash API. Choose a model that supports image editing."

    @classmethod
    def INPUT_TYPES(cls):
        edit_models = [
            m["model_id"] for m in catalog.models_where(category="image", supports_image_edit=True)
            if m.get("model_id")
        ]
        return _edit_inputs((edit_models or ["(catalog unavailable)"],))

    def edit(self, image, model, prompt, size, width=1024, height=1024):
        return _edit(image, model, prompt, _size(size, width, height))


class EcoHashDedicatedImageGenerate(DedicatedNode, EcoHashImageGenerate):
    DESCRIPTION = "Generate images using the dedicated inference endpoint configured outside the workflow."

    @classmethod
    def INPUT_TYPES(cls):
        inputs = _generate_inputs(MODEL_INPUT)
        inputs["optional"]["connection"] = cls.connection_input()
        return inputs

    def generate(self, model, prompt, size, steps, seed, width=1024, height=1024, connection="dedicated"):
        model = model_id(model)
        return _generate(model, prompt, _size(size, width, height), steps, seed, client.load_dedicated_endpoint(connection))


class EcoHashDedicatedImageEdit(DedicatedNode, EcoHashImageEdit):
    DESCRIPTION = "Edit images using the dedicated inference endpoint configured outside the workflow."

    @classmethod
    def INPUT_TYPES(cls):
        inputs = _edit_inputs(MODEL_INPUT)
        inputs["optional"]["connection"] = cls.connection_input()
        return inputs

    def edit(self, image, model, prompt, size, width=1024, height=1024, connection="dedicated"):
        model = model_id(model)
        return _edit(image, model, prompt, _size(size, width, height), client.load_dedicated_endpoint(connection))
