from ecohash import catalog, client, conversions

SIZES = ["1024x1024", "1024x768", "768x1024", "768x768", "512x512"]


def _first_b64(out):
    data = out.get("data") or []
    if not data or "b64_json" not in data[0]:
        from ecohash.client import EcoHashError
        raise EcoHashError("EcoHash returned no image data. The request may have been filtered; try a different prompt.")
    return data[0]["b64_json"]


class EcoHashImageGenerate:
    CATEGORY = "EcoHash"
    FUNCTION = "generate"
    RETURN_TYPES = ("IMAGE",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": (catalog.model_ids("image"),),
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "size": (SIZES, {"default": "1024x1024"}),
                "steps": ("INT", {"default": 0, "min": 0, "max": 100,
                                  "tooltip": "0 = model default"}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2**31 - 1,
                                 "tooltip": "-1 = random"}),
            }
        }

    def generate(self, model, prompt, size, steps, seed):
        body = {"model": model, "prompt": prompt, "size": size, "response_format": "b64_json"}
        if steps > 0:
            body["steps"] = steps
        if seed >= 0:
            body["seed"] = seed
        out = client.request_json("POST", "/images/generations", json_body=body)
        return (conversions.b64_to_image_tensor(_first_b64(out)),)


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
        return {
            "required": {
                "image": ("IMAGE",),
                "model": (edit_models or ["(catalog unavailable)"],),
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "size": (["auto"] + SIZES, {
                    "default": "auto",
                    "tooltip": "auto = match the source image (rounded down to a multiple of 16)",
                }),
            }
        }

    def edit(self, image, model, prompt, size):
        png = conversions.image_tensor_to_png_bytes(image)
        data = {"model": model, "prompt": prompt}
        if size == "auto":
            # Omitting size does NOT preserve the source dimensions -- the API falls back
            # to 1024x1024 (measured: 512x512 and 768x768 sources both came back
            # 1024x1024). Send the source dimensions explicitly so "auto" means what it
            # says; the API floors each side to a multiple of 16 (900 -> 896, 1023 -> 1008).
            height, width = image.shape[1], image.shape[2]
            data["size"] = f"{width}x{height}"
        else:
            data["size"] = size
        out = client.request_json(
            "POST", "/images/edits",
            data=data,
            files={"image": ("input.png", png, "image/png")},
        )
        return (conversions.b64_to_image_tensor(_first_b64(out)),)
