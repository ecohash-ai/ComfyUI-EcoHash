import base64

try:
    from ..ecohash import catalog, client, conversions
except ImportError:
    from ecohash import catalog, client, conversions

from .dedicated import DedicatedNode, MODEL_INPUT, model_id


def _first_message_content(out):
    choices = out.get("choices") or []
    choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
    message = choice.get("message") or {}
    if not isinstance(message, dict):
        raise client.EcoHashError("Inference API returned an invalid completion message. Expected choices[0].message.content text.")
    content = message.get("content")
    if content is not None and not isinstance(content, str):
        raise client.EcoHashError("Inference API returned non-text completion content. Expected choices[0].message.content as a string.")
    # Reasoning models (GLM-*, Qwen3.5/3.6-*) can spend the whole max_tokens budget on
    # reasoning and return content as "" or null with finish_reason "length". Treat blank
    # the same as missing: returning "" here silently feeds an empty prompt downstream.
    if content is None or not content.strip():
        try:
            from ..ecohash.client import EcoHashError
        except ImportError:
            from ecohash.client import EcoHashError
        hint = ""
        if choice.get("finish_reason") == "length":
            hint = (" The token budget ran out before any answer text was produced — this "
                    "happens with reasoning models, which spend max_tokens on internal "
                    "reasoning first. Raise max_tokens (try 1024+) and retry.")
        raise EcoHashError(
            "Inference API returned no completion. The request may have been filtered or the model "
            "errored; try again or use a different model." + hint
        )
    return content


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


def _llm_inputs(model_input):
    return {
        "required": {
            "model": model_input,
            "mode": (list(MODE_PRESETS), {"default": "prompt_enhance"}),
            "text": ("STRING", {"multiline": True, "default": ""}),
            "system_prompt": ("STRING", {"multiline": True, "default": "",
                                         "tooltip": "Used when mode = custom"}),
            "temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.05}),
            "max_tokens": ("INT", {"default": 1024, "min": 1, "max": 16384}),
        }
    }


def _run(model, mode, text, system_prompt, temperature, max_tokens, endpoint=None):
    if mode not in MODE_PRESETS:
        raise client.EcoHashError("Choose a supported LLM mode: chat, prompt_enhance, translate_to_english or custom.")
    system = system_prompt if mode == "custom" else MODE_PRESETS[mode]
    messages = ([{"role": "system", "content": system}] if system else [])
    messages.append({"role": "user", "content": text})
    options = {"endpoint": endpoint} if endpoint is not None else {}
    out = client.request_json("POST", "/chat/completions", json_body={
        "model": model, "messages": messages,
        "temperature": temperature, "max_tokens": max_tokens,
    }, **options)
    return (_first_message_content(out),)


class EcoHashLLM:
    CATEGORY = "EcoHash/PublicModels"
    FUNCTION = "run"
    RETURN_TYPES = ("STRING",)
    DESCRIPTION = "Public EcoHash chat, prompt enhancement and translation. system_prompt is used in custom mode. Connect STRING outputs to downstream prompts."

    @classmethod
    def INPUT_TYPES(cls):
        return _llm_inputs((catalog.model_ids("llm", "llm_vision"),))

    def run(self, model, mode, text, system_prompt, temperature, max_tokens):
        return _run(model, mode, text, system_prompt, temperature, max_tokens)


def _vlm_inputs(model_input):
    return {
        "required": {
            "image": ("IMAGE",),
            "model": model_input,
            "prompt": ("STRING", {"multiline": True,
                                  "default": "Describe this image in detail for use as an image-generation prompt."}),
            "max_tokens": ("INT", {"default": 512, "min": 1, "max": 8192}),
        }
    }


def _describe(image, model, prompt, max_tokens, endpoint=None):
    b64 = base64.b64encode(conversions.image_tensor_to_png_bytes(image)).decode()
    options = {"endpoint": endpoint} if endpoint is not None else {}
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
    }, **options)
    return (_first_message_content(out),)


class EcoHashVLMDescribe:
    CATEGORY = "EcoHash/PublicModels"
    FUNCTION = "describe"
    RETURN_TYPES = ("STRING",)
    DESCRIPTION = "Describe one image using a public EcoHash vision model. Connect the text to an image generator's prompt."

    @classmethod
    def INPUT_TYPES(cls):
        models = [m["model_id"] for m in catalog.schema_catalog() if m.get("model_id") and
                  (m.get("category") == "llm_vision" or
                   m.get("category") == "llm" and "image" in (m.get("input_modalities") or []))]
        return _vlm_inputs((models or ["(catalog unavailable)"],))

    def describe(self, image, model, prompt, max_tokens):
        return _describe(image, model, prompt, max_tokens)


class EcoHashDedicatedLLM(DedicatedNode, EcoHashLLM):
    DESCRIPTION = "Chat, enhance prompts or translate with a dedicated language model. Choose a server-side connection and enter its deployed model ID."

    @classmethod
    def INPUT_TYPES(cls):
        inputs = _llm_inputs(MODEL_INPUT)
        inputs["optional"] = {"connection": cls.connection_input()}
        return inputs

    def run(self, model, mode, text, system_prompt, temperature, max_tokens, connection="dedicated"):
        return _run(model_id(model), mode, text, system_prompt, temperature, max_tokens, client.load_dedicated_endpoint(connection))


class EcoHashDedicatedVLMDescribe(DedicatedNode, EcoHashVLMDescribe):
    DESCRIPTION = "Describe an image using a dedicated vision-language model that supports image inputs. Choose its connection and deployed model ID."

    @classmethod
    def INPUT_TYPES(cls):
        inputs = _vlm_inputs(MODEL_INPUT)
        inputs["optional"] = {"connection": cls.connection_input()}
        return inputs

    def describe(self, image, model, prompt, max_tokens, connection="dedicated"):
        return _describe(image, model_id(model), prompt, max_tokens, client.load_dedicated_endpoint(connection))
