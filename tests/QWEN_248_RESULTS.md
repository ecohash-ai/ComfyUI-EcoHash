# Qwen Image 2.1 dedicated instance 248 — real ComfyUI verification

- Date: 2026-10-19
- Branch: `feat/dedicated-inference`
- Model ID: `Qwen/Qwen-Image-2.1:248`
- Inference endpoint: `https://api.ecohash.com/v1/images/generations`
- Saved connection: `qwen-image-248`, API prefix `https://api.ecohash.com/v1`, timeout 300 s
- Credential: explicitly configured from the existing local EcoHash account key; no
  credential was printed, stored in the workflow, or added to this repository.

## Official template adaptation

Source: Comfy-Org's [Qwen Image 2.1 text-to-image template](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_qwen_image_2_1_t2i.json),
`image_qwen_image_2_1_t2i` from the installed `comfyui-workflow-templates` 0.11.89.

- Preserved the official positive prompt, ResolutionSelector and SaveImageAdvanced.
- Replaced the local inference subgraph (model/text encoder/VAE loading, prompt
  encoding, sampling and image decoding) with `EcoHashDedicatedImageGenerate`.
- Kept the official starting step count of 25. Used seed 42 within the plugin's
  supported range; the official template's large seed was not preserved.
- ResolutionSelector supplies width/height to `size=custom`. Square 1 MP produces
  1024×1024; its alignment was set to 32 so subsequent ratios satisfy the plugin's
  multiple-of-16 dimension requirement.
- The official prompt-enhancement option starts disabled; that branch was not enabled.
- Replaced local-checkpoint setup notes with instructions for the remote connection.

Workflow: `ResolutionSelector → EcoHash Dedicated Image Generate → SaveImageAdvanced`.

## Observed result

- The authenticated discovery route listed the exact model ID including `:248`.
- Queued once through the real ComfyUI browser interface, with the dedicated node
  selecting `qwen-image-248`. No mock service was used for this check.
- Prompt ID: `bfc30729-9d0f-4dba-ac23-0cc5619e69bf`.
- ComfyUI history: `success`; total workflow duration **15.183 seconds**.
- Output: valid **1024×1024 RGB** PNG. Visual inspection showed a monochrome fashion
  portrait, large round sunglasses and a bright green graphic background, consistent
  with the official prompt. ComfyUI displayed and saved the image successfully.
- Saved the workflow in the existing ComfyUI workflow list as
  `Qwen_Image_2.1_EcoHash_248`; retained the configured connection for reuse.
- Exported the saved workflow and checked that it contains no API key.
- Fixed frontend workflow serialization so plugin-only buttons, discovery pickers
  and status fields are omitted. Verified that the saved image node retains its nine
  core widget values, including the native fixed-seed control. The API prompt's
  existing `options.serialize=false` behavior is retained.
- Re-queued the identical workflow after export verification. Prompt
  `bb7b6375-e062-47c7-86dd-35844c3b649b` cached nodes `13`, `459` and `461`, including
  the dedicated image node, so this replay made no second remote inference request.

The shared gateway routes user instances using `<model_name>:<instance_id>`, as
documented in [Calling your endpoint](https://docs.ecohash.com/user-inference/calling-endpoint).
The API prefix therefore stays `https://api.ecohash.com/v1`; the node adds
`/images/generations` and sends the full model ID in the request body.

## Local artifacts

- `/private/tmp/ecohash-qwen-248/qwen-image-248-workflow.json` — reusable workflow, no key
- `/private/tmp/ecohash-qwen-248/generated.png` — actual model output
- `/private/tmp/ecohash-qwen-248/comfyui-verified.jpg` — browser proof
- `/private/tmp/ecohash-qwen-248/result.json` — result metadata
- `/private/tmp/ecohash-qwen-248/README.md` — configuration and usage in Chinese

This verifies text-to-image generation for instance 248 with the tested settings.
Image editing and other deployments were not exercised by this real-service check.
