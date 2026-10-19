import hashlib
import json

try:
    from ..ecohash import catalog, client, video, video_contract
except ImportError:
    from ecohash import catalog, client, video, video_contract

from .dedicated import DedicatedNode, MODEL_INPUT, model_id


def _inputs(model_input, dedicated=False):
    required = {"model": model_input, "prompt": ("STRING", {"multiline": True, "default": ""})}
    required.update({
        "duration": ("INT", {"default": 4, "min": 1, "max": 86400, "tooltip": "Requested seconds; model limits come from the service, not the model name."}),
        "aspect_ratio": (video.RATIOS, {"default": "16:9"}),
        "resolution": (video.RESOLUTIONS + (["custom"] if dedicated else []), {"default": "720p", "tooltip": "Common size presets, not a guarantee of model support. Hover over the model selector for capabilities or use a supported custom size."}),
    })
    if not dedicated:
        required["generate_audio"] = ("BOOLEAN", {"default": True, "tooltip": "Request audio when supported by the gateway model."})
    optional = {
        "job_id": ("STRING", {"default": "", "tooltip": "Leave blank to generate. Paste an existing job ID to resume polling/download without a new generation. Keep its original connection."}),
        "wait_timeout": ("INT", {"default": 1800, "min": 10, "max": 14400, "tooltip": "Total wait for video completion in seconds; separate from the connection's per-request timeout."}),
    }
    if dedicated:
        optional = {
            "width": ("INT", {"default": 1280, "min": 128, "max": 8192, "step": 16, "tooltip": "Only used for custom resolution."}),
            "height": ("INT", {"default": 720, "min": 128, "max": 8192, "step": 16, "tooltip": "Only used for custom resolution."}),
            **optional,
        }
        optional["connection"] = DedicatedNode.connection_input()
    return {"required": required, "optional": optional, "hidden": {"unique_id": "UNIQUE_ID"}}


def _run(model, prompt, duration, aspect_ratio, resolution, generate_audio=True, *,
         steps=0, seed=-1, job_id="", wait_timeout=1800, endpoint=None, unique_id=None,
         protocol=None, width=None, height=None):
    # Old prompt fields are accepted for compatibility, but cannot select a
    # native adapter or override the endpoint/model ID chosen by the user.
    legacy_protocol = protocol
    protocol = "openai" if endpoint is not None else "ecohash"
    if protocol == "openai" and resolution != "custom" and legacy_protocol != "openai":
        width, height = video.dimensions(resolution, aspect_ratio)
    width, height = width if width is not None else 1280, height if height is not None else 720
    # Lazy imports keep node discovery and standalone tests independent of ComfyUI.
    try:
        import folder_paths
        from comfy_api.input_impl import VideoFromFile
        from comfy.model_management import throw_exception_if_processing_interrupted
    except ImportError:
        raise client.EcoHashError("Video nodes require a current ComfyUI installation with VIDEO / Save Video support. Update ComfyUI and restart.") from None

    def progress(job, status, percent):
        if unique_id is not None:
            from server import PromptServer
            instance = getattr(PromptServer, "instance", None)
            if instance:
                instance.send_sync("ecohash_video_progress", {"node": unique_id, "job_id": job, "status": status, "progress": percent})

    body = {} if job_id.strip() else video.build_request(protocol, model, prompt, duration, aspect_ratio, resolution,
                                                         generate_audio, width=width, height=height)
    mapped = video_contract.prepare(endpoint, body["model"], body["prompt"], duration, resolution, width, height,
                                    aspect_ratio=aspect_ratio if resolution != "custom" else None) if endpoint and body else None
    if mapped is not None:
        body = mapped
    path, job = video.generate(protocol=protocol, body=body, endpoint=endpoint, job_id=job_id,
                               wait_timeout=wait_timeout, output_dir=folder_paths.get_temp_directory(),
                               check_interrupt=throw_exception_if_processing_interrupted, progress=progress,
                               json_request=mapped is not None)
    result = VideoFromFile(str(path))
    try:
        result.get_dimensions()
    except Exception:
        path.unlink(missing_ok=True)
        raise client.EcoHashError(f"Downloaded video cannot be decoded by ComfyUI. Job ID: {job}. Check the MP4 codec or update ComfyUI/PyAV.") from None
    return result, job


class EcoHashVideoGenerate:
    CATEGORY = "EcoHash/PublicModels"
    FUNCTION = "generate"
    RETURN_TYPES = ("VIDEO", "STRING")
    RETURN_NAMES = ("video", "job_id")
    DESCRIPTION = "Generate a text-to-video MP4 through EcoHash, wait for its asynchronous job, and connect VIDEO to Save Video for playback and saving. Models requiring reference media are not supported by this text-only node."

    @classmethod
    def INPUT_TYPES(cls):
        return _inputs((catalog.model_ids("video"),))

    @classmethod
    def VALIDATE_INPUTS(cls, resolution="720p"):
        # The browser refreshes choices from live capabilities. Do not reject a
        # newly introduced size because the original node schema had fewer presets.
        return True if isinstance(resolution, str) and resolution.strip() else "Choose a video resolution."

    def generate(self, model, prompt, duration, aspect_ratio, resolution, generate_audio, **kwargs):
        return _run(model, prompt, duration, aspect_ratio, resolution, generate_audio, **kwargs)


class EcoHashDedicatedVideoGenerate(DedicatedNode, EcoHashVideoGenerate):
    DESCRIPTION = "Generate text-to-video on a dedicated model. Select a connection and model. Nonstandard services need an explicit server-side request mapping; no protocol selection is required. VIDEO preserves any audio in the returned MP4. Connect to Save Video."

    @classmethod
    def INPUT_TYPES(cls):
        return _inputs(MODEL_INPUT, dedicated=True)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        connection = kwargs.get("connection", "dedicated")
        settings = [DedicatedNode.IS_CHANGED(**kwargs), video_contract.configured(connection)]
        return hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()

    @classmethod
    def VALIDATE_INPUTS(cls, resolution="720p", connection="dedicated"):
        valid = DedicatedNode.VALIDATE_INPUTS(connection=connection)
        return valid if valid is not True else EcoHashVideoGenerate.VALIDATE_INPUTS(resolution)

    def generate(self, model, prompt, duration, aspect_ratio, resolution, generate_audio=True, connection="dedicated", **kwargs):
        return _run(model_id(model), prompt, duration, aspect_ratio, resolution, generate_audio,
                    endpoint=client.load_dedicated_endpoint(connection), **kwargs)
