# ComfyUI-Manager Legacy Collection PR

To add ComfyUI-EcoHash to the ComfyUI-Manager legacy node list, fork `Comfy-Org/ComfyUI-Manager`, insert the following JSON entry alphabetically into `custom-node-list.json`, and open a pull request.

```json
{
    "author": "ecohash-ai",
    "title": "ComfyUI-EcoHash",
    "id": "comfyui-ecohash",
    "reference": "https://github.com/ecohash-ai/ComfyUI-EcoHash",
    "files": ["https://github.com/ecohash-ai/ComfyUI-EcoHash"],
    "install_type": "git-clone",
    "description": "Official EcoHash nodes: cloud image generation & editing (qwen-image, flux2-klein, z-image-turbo), LLM prompt tools, vision captioning, TTS/STT. Bring your EcoHash API key."
}
```

Note: verify a legacy-list entry is still required — ComfyUI-Manager ingests Registry nodes directly; skip this PR if the Registry listing already appears in Manager.
