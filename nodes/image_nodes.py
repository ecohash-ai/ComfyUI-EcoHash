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
        edit_models = [m["model_id"] for m in catalog.models_where(supports_image_edit=True)]
        return {
            "required": {
                "image": ("IMAGE",),
                "model": (edit_models or ["(catalog unavailable)"],),
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "size": (SIZES, {"default": "1024x1024"}),
            }
        }

    def edit(self, image, model, prompt, size):
        png = conversions.image_tensor_to_png_bytes(image)
        out = client.request_json(
            "POST", "/images/edits",
            data={"model": model, "prompt": prompt, "size": size},
            files={"image": ("input.png", png, "image/png")},
        )
        return (conversions.b64_to_image_tensor(_first_b64(out)),)
