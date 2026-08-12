import base64

from ecohash import catalog, client, conversions

MODE_PRESETS = {
    "chat": "",
    "prompt_enhance": (
        "You are an expert prompt engineer for text-to-image diffusion models. Rewrite the "
        "user's idea as one vivid, detailed English image prompt: subject, style, lighting, "
        "composition, quality tags. Output only the prompt."
    ),
    "translate_to_english": (
        "Translate the user's text to natural English suitable as an image-generation prompt. "
        "Output only the translation."
    ),
    "custom": "",
}


class EcoHashLLM:
    CATEGORY = "EcoHash"
    FUNCTION = "run"
    RETURN_TYPES = ("STRING",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": (catalog.model_ids("llm", "llm_vision"),),
                "mode": (list(MODE_PRESETS), {"default": "prompt_enhance"}),
                "text": ("STRING", {"multiline": True, "default": ""}),
                "system_prompt": ("STRING", {"multiline": True, "default": "",
                                             "tooltip": "Used when mode = custom"}),
                "temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.05}),
                "max_tokens": ("INT", {"default": 1024, "min": 1, "max": 16384}),
            }
        }

    def run(self, model, mode, text, system_prompt, temperature, max_tokens):
        system = system_prompt if mode == "custom" else MODE_PRESETS[mode]
        messages = ([{"role": "system", "content": system}] if system else [])
        messages.append({"role": "user", "content": text})
        out = client.request_json("POST", "/chat/completions", json_body={
            "model": model, "messages": messages,
            "temperature": temperature, "max_tokens": max_tokens,
        })
        return (out["choices"][0]["message"]["content"],)


class EcoHashVLMDescribe:
    CATEGORY = "EcoHash"
    FUNCTION = "describe"
    RETURN_TYPES = ("STRING",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "model": (catalog.model_ids("llm_vision"),),
                "prompt": ("STRING", {"multiline": True,
                                      "default": "Describe this image in detail for use as an image-generation prompt."}),
                "max_tokens": ("INT", {"default": 512, "min": 1, "max": 8192}),
            }
        }

    def describe(self, image, model, prompt, max_tokens):
        b64 = base64.b64encode(conversions.image_tensor_to_png_bytes(image)).decode()
        out = client.request_json("POST", "/chat/completions", json_body={
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            }],
            "max_tokens": max_tokens,
        })
        return (out["choices"][0]["message"]["content"],)
