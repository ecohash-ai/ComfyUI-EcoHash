try:
    from ..ecohash import catalog, client, video
except ImportError:
    from ecohash import catalog, client, video

from .dedicated import DedicatedNode, MODEL_INPUT, model_id


def _inputs(model_input, dedicated=False):
    required = {"model": model_input, "prompt": ("STRING", {"multiline": True, "default": ""})}
    if dedicated:
        required["protocol"] = (video.PROTOCOLS, {"default": "openai", "tooltip": "ecohash = /video/generations; openai = multipart /videos; minimax_h3 = native SGLang H3 JSON /videos."})
    required.update({
        "duration": ("INT", {"default": 4, "min": 4, "max": 15, "tooltip": "Requested seconds. The service may align the actual duration to its frame rules."}),
        "aspect_ratio": (video.RATIOS, {"default": "16:9"}),
        "resolution": ([r for r in video.RESOLUTIONS if r != "768p"], {"default": "720p", "tooltip": "EcoHash protocol only. Native MiniMax-H3 uses a 768-pixel short edge."}),
        "generate_audio": ("BOOLEAN", {"default": True, "tooltip": "EcoHash protocol only. MiniMax-H3 generates native audio with its video."}),
    })
    optional = {
        "width": ("INT", {"default": 1280, "min": 128, "max": 4096, "step": 16, "tooltip": "OpenAI protocol only; use dimensions supported by the model."}),
        "height": ("INT", {"default": 720, "min": 128, "max": 4096, "step": 16}),
        "steps": ("INT", {"default": 0, "min": 0, "max": 100, "tooltip": "Native endpoints only. 0 = server default, or the standard 50-step MiniMax-H3 profile."}),
        "seed": ("INT", {"default": -1, "min": -1, "max": 2**31 - 1, "tooltip": "Native endpoints only, when supported. -1 = random."}),
        "job_id": ("STRING", {"default": "", "tooltip": "Leave blank to generate. Paste an existing job ID to resume polling/download without a new generation. Keep its original connection and protocol."}),
        "wait_timeout": ("INT", {"default": 1800, "min": 10, "max": 14400, "tooltip": "Total wait for video completion in seconds; separate from the connection's per-request timeout."}),
    }
    if dedicated:
        optional["connection"] = DedicatedNode.connection_input()
    return {"required": required, "optional": optional, "hidden": {"unique_id": "UNIQUE_ID"}}


def _run(model, prompt, duration, aspect_ratio, resolution, generate_audio, *, protocol="ecohash",
         width=1280, height=720, steps=0, seed=-1, job_id="", wait_timeout=1800, endpoint=None, unique_id=None):
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
                                                         generate_audio, steps, seed, width, height)
    path, job = video.generate(protocol=protocol, body=body, endpoint=endpoint, job_id=job_id,
                               wait_timeout=wait_timeout, output_dir=folder_paths.get_temp_directory(),
                               check_interrupt=throw_exception_if_processing_interrupted, progress=progress)
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

    def generate(self, model, prompt, duration, aspect_ratio, resolution, generate_audio, **kwargs):
        return _run(model, prompt, duration, aspect_ratio, resolution, generate_audio, **kwargs)


class EcoHashDedicatedVideoGenerate(DedicatedNode, EcoHashVideoGenerate):
    DESCRIPTION = "Generate text-to-video on a dedicated instance. Select its connection and actual protocol. MiniMax-H3 requires native JSON /videos, a raw model ID on an instance proxy, and produces native audio. Connect VIDEO to Save Video."

    @classmethod
    def INPUT_TYPES(cls):
        return _inputs(MODEL_INPUT, dedicated=True)

    def generate(self, model, prompt, duration, aspect_ratio, resolution, generate_audio, protocol="openai", connection="dedicated", **kwargs):
        return _run(model_id(model), prompt, duration, aspect_ratio, resolution, generate_audio,
                    protocol=protocol, endpoint=client.load_dedicated_endpoint(connection), **kwargs)
