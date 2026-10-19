# EcoHash for ComfyUI — User Guide

This guide covers the current plugin implementation: seven public-model nodes and
seven dedicated-model nodes. It describes configuration, every node, complete
workflows, video recovery, deployment compatibility, and troubleshooting.

The package version remains **1.0.1**. Features documented from the development
branch are not a claim that version 1.1.0 has been published. Install the branch
containing these changes when reviewing them before a release.

## Contents

1. [What the plugin does](#1-what-the-plugin-does)
2. [Requirements and installation](#2-requirements-and-installation)
3. [Configure one EcoHash API Key](#3-configure-one-ecohash-api-key)
4. [Public models and dedicated connections](#4-public-models-and-dedicated-connections)
5. [Choose and refresh models](#5-choose-and-refresh-models)
6. [Node reference](#6-node-reference)
7. [Build image workflows](#7-build-image-workflows)
8. [Build language and vision workflows](#8-build-language-and-vision-workflows)
9. [Build speech workflows](#9-build-speech-workflows)
10. [Build video workflows](#10-build-video-workflows)
11. [Recover a video task](#11-recover-a-video-task)
12. [Compose public and dedicated models](#12-compose-public-and-dedicated-models)
13. [Use the bundled templates](#13-use-the-bundled-templates)
14. [Caching and fresh generations](#14-caching-and-fresh-generations)
15. [Server configuration](#15-server-configuration)
16. [Required inference API behavior](#16-required-inference-api-behavior)
17. [Troubleshooting](#17-troubleshooting)
18. [Updating, sharing, and removing the plugin](#18-updating-sharing-and-removing-the-plugin)
19. [Verification and support](#19-verification-and-support)

## 1. What the plugin does

EcoHash nodes send inference requests from your ComfyUI server to a model service.
They return normal ComfyUI `IMAGE`, `STRING`, `AUDIO`, or `VIDEO` outputs, which you
can connect to compatible nodes for further processing, previewing, or saving.

There are two groups in the node library:

| Group | Where computation runs | What you configure |
| --- | --- | --- |
| **EcoHash → Public Models** | A model exposed through the public EcoHash API | The global EcoHash API Key and a model from the catalog |
| **EcoHash → Dedicated Models** | Your selected inference deployment | The same global key for EcoHash URLs, a connection, and the exact served model ID |

For these API nodes, you do not download model weights or need a local inference
GPU. ComfyUI still needs memory, disk space, and its ordinary dependencies to
handle images, audio, and downloaded video. Other nodes in the same graph may
have their own local GPU and model requirements.

**An API node is not a remote replacement for every native diffusion node.**
It does not return a local `MODEL`, `CLIP`, `VAE`, `CONDITIONING`, or `LATENT` object.
Replacing an entire native sampling chain with a video-generation API changes
what the workflow can control. A native workflow's LoRA, sampler, scheduler,
step count, exact frame count, and VAE settings do not automatically transfer
to a remote service. Keeping all of those nodes active requires a compatible
full ComfyUI execution environment; this plugin does not submit arbitrary native
ComfyUI graphs to a remote worker.

## 2. Requirements and installation

Use a working ComfyUI installation and its own Python environment. The plugin's
declared Python requirement is 3.10 or later; your installed ComfyUI version may
require a newer interpreter. Follow [ComfyUI's installation requirements](https://docs.comfy.org/installation/system_requirements)
for ComfyUI itself. Video workflows require native `VIDEO` and **Save Video**
support. The browser needs access to the ComfyUI server; that server needs access
to the inference endpoint and any returned media download URLs.

### Install with ComfyUI-Manager

In ComfyUI-Manager, search for **EcoHash** and install **ComfyUI-EcoHash** if it is
available in your Manager catalog. Restart the ComfyUI server, then reload the
browser. For an unreleased feature branch, use the manual installation below.

### Install manually

From your ComfyUI directory:

```bash
git clone https://github.com/ecohash-ai/ComfyUI-EcoHash.git custom_nodes/ComfyUI-EcoHash
```

Install dependencies with the interpreter used to launch ComfyUI. For a virtual
environment installation, an example from that same ComfyUI directory is:

```bash
.venv/bin/python -m pip install -r custom_nodes/ComfyUI-EcoHash/requirements.txt
```

On Windows Portable, run from the portable installation directory:

```powershell
.\python_embeded\python.exe -m pip install -r .\ComfyUI\custom_nodes\ComfyUI-EcoHash\requirements.txt
```

For Desktop, use the environment belonging to that Desktop installation.
Installing into a different system Python will not install dependencies for
ComfyUI. Restart the backend after installation and refresh the browser after
frontend changes. Avoid installing two copies of the plugin under different
custom-node folder names.

After restarting, search the node library for **EcoHash**. You should see both
groups and fourteen node types. Check the ComfyUI startup log if a group is absent.

## 3. Configure one EcoHash API Key

Create or obtain a key through your EcoHash account. See the official
[API keys guide](https://docs.ecohash.com/getting-started/api-keys) for creating,
expiring, and revoking keys. The same account key is used by this plugin for
public models and official EcoHash dedicated-instance URLs.

1. Open the **EcoHash** cloud tab in ComfyUI's sidebar. Alternatively, click
   **Connections** on an EcoHash node, or use
   **Extensions → EcoHash → EcoHash connections**.
2. Enter the key in **EcoHash API Key**.
3. Click **Save and verify API Key**.
4. Wait for the verification result before adding a connection or running a node.

The field is empty when reopened; its configured placeholder indicates that a
key is already saved. Leaving it blank preserves the saved key. You do not need
to paste the key into each node or official connection.

Verification makes an authenticated model-list request. It does not generate
media, prove that every model accepts every setting, or guarantee an available
inference worker. A real node execution is a separate test and can incur charges.

The key stays on the ComfyUI server. Saved settings are in the plugin's
`connections.json`, excluded from Git by this repository. The settings API does
not return saved keys. Do not share this file, a populated `config.ini`, or
screenshots containing a key. A shared ComfyUI server uses that server's
configured credentials; use the connection manager only in your trusted server
environment.

The global key is inherited only by the exact HTTPS host `api.ecohash.com` on
the default HTTPS port, including instance proxy paths. A different host,
subdomain, HTTP URL, or port needs an independent endpoint key under
**Advanced connection settings**. The plugin does not send the global key to
those endpoints as a fallback.

## 4. Public models and dedicated connections

### Public-model setup

Use a node under **Public Models** after verifying the global key. The public
connection is built in, its API prefix is fixed to
`https://api.ecohash.com/v1`, and no extra connection is necessary. Choose a
model and the inputs required by that node.

### Dedicated-model setup

Have a running inference deployment and its API address ready. This plugin
connects to a service; adding a connection does not deploy or start a model.

1. In EcoHash settings, choose **Add connection**.
2. Enter one unique **Connection name**, such as `My video instance`.
3. Enter its **API base URL**, including the prefix the service exposes.
4. For an official EcoHash HTTPS URL, the global key is used automatically.
   For another origin, supply that endpoint's own key in Advanced settings.
5. Click **Save and connect**, then wait for model discovery to finish.
6. Add a node under **Dedicated Models** and select that connection.
7. Select a discovered model or enter the exact served ID manually.

For an instance-scoped proxy, an address can look like:

```text
https://api.ecohash.com/inference-instances/INSTANCE_ID/proxy/v1
```

Replace `INSTANCE_ID` with the real deployment ID. Use the address supplied for
your deployment; the plugin does not infer a route from a model name.

The address field accepts recognized complete operation URLs, such as an image
generation endpoint, and removes the operation suffix when saving. Still check
the saved prefix: the plugin does not add `/v1` if the service actually needs it.

### Names, IDs, and model IDs

| Value | Meaning | Example |
| --- | --- | --- |
| Connection name | A label you choose, shown in settings and nodes | `My video instance` |
| Internal connection ID | Generated locally and stored in workflow JSON | An automatically generated `connection-…` ID |
| Served model ID | The exact identifier accepted by the selected endpoint | The ID returned by that endpoint's `/models` |

Only one editable connection name is shown. You do not need to invent or manage
an internal ID in the UI. Renaming preserves that ID, so existing workflows keep
their connection. Duplicate names, including case-only variants, are rejected.

A gateway model ID may include an instance suffix while an instance-scoped
endpoint serves an unsuffixed ID. Copy the ID from the endpoint you will call;
do not add or remove suffixes by guesswork. Listing a model on the gateway does
not prove that every gateway operation supports that dedicated instance.

New nodes can select an unambiguous or deliberately preferred connection. With
multiple possible connections, select one explicitly. An empty selection is not
a usable endpoint. There is no automatically supplied empty dedicated endpoint.

Deleting a saved connection leaves workflows referencing its old ID unresolved.
Select a replacement connection in each affected node. INI-defined connections
must be removed from their INI section before their saved entry can be deleted;
the built-in public connection cannot be deleted.

## 5. Choose and refresh models

Public catalogs are loaded without blocking node registration on network access:
cached data or a packaged snapshot supplies initial choices. The frontend refreshes
separately. A dedicated connection queries its authenticated `/models` endpoint.
Use **Refresh models** after deploying a model or changing a catalog.

The discovered-model selector can fill an empty selection when there is exactly
one compatible result. **Enter model ID manually** exposes the model ID field.
Changing the connection clears the previous model selection. Refreshing preserves
an existing ID so that a changed catalog does not silently choose another model.

Filtering uses declared categories and input/output modalities, not model-name
patterns. Future model names need no new brand-specific classification in the
plugin. Missing metadata means compatibility is unknown, not confirmed. A text
model does not become a vision model just because it is selectable manually.

Hover over the model selector or ID field for available capability hints: edit
support, default image steps, supported sizes, voices, or video duration limits.
There is no separate **Model information** row or connection-status widget in
the node. Connection tests are in the manager; **Execution status** describes
workflow execution.

If a service responds but does not expose `/models`, the manager can report it
as **reachable**. Enter a model ID manually, but treat authentication and actual
inference compatibility as unverified. Live, cached, and fallback catalog status
describe where the model list came from, not whether a generation will succeed.

## 6. Node reference

Both groups contain the following operations. Dedicated variants additionally
select a connection and accept an exact served model ID.

| Operation | Public node | Dedicated node | Output |
| --- | --- | --- | --- |
| Image generation | EcoHash Image Generate | EcoHash Dedicated Image Generate | `IMAGE` |
| Image editing | EcoHash Image Edit | EcoHash Dedicated Image Edit | `IMAGE` |
| Language | EcoHash LLM | EcoHash Dedicated LLM | `STRING` |
| Vision description | EcoHash VLM Describe | EcoHash Dedicated VLM Describe | `STRING` |
| Speech synthesis | EcoHash TTS | EcoHash Dedicated TTS | `AUDIO` |
| Speech transcription | EcoHash STT | EcoHash Dedicated STT | `STRING` |
| Video generation | EcoHash Video Generate | EcoHash Dedicated Video Generate | `VIDEO`, job-ID `STRING` |

The displayed labels follow ComfyUI's language setting. The class IDs in saved
workflow JSON remain stable English identifiers such as
`EcoHashDedicatedVideoGenerate`.

### Image Generate

| Field | Behavior |
| --- | --- |
| `model` | Public catalog selection or exact dedicated model ID |
| `prompt` | Image description |
| `size` | Preset dimensions or `custom`; default `1024x1024` |
| `steps` | `0` uses the service default; positive values up to 100 are sent to the service |
| `seed` | `-1` omits a fixed seed; 0 through 2147483647 sends that seed |
| `width`, `height` | Shown for `custom`; multiples of 16 between 64 and 8192 |

Presets include square, landscape, and portrait sizes. Availability in the node
does not establish model support. The service may constrain or align dimensions,
ignore unsupported controls, or reject a request. Each call returns the first
image result as one ComfyUI image.

### Image Edit

Supply a single `IMAGE`, a model supporting image editing, and an instruction in
`prompt`. `size=auto` sends the source image dimensions; it does not guarantee the
server will preserve the exact shape. Other presets and custom dimensions work
as above. Generation support alone does not imply editing support.

### LLM

`text` is the user input. `mode` has four values:

| Mode | Result |
| --- | --- |
| `chat` | A normal completion with no preset system instruction |
| `prompt_enhance` | A detailed English image prompt from an initial idea |
| `translate_to_english` | English text suitable as an image-generation prompt |
| `custom` | A completion using your `system_prompt` |

The default mode is `prompt_enhance`. `system_prompt` is shown and used only for
`custom`. `temperature` is 0–2, default 0.7. `max_tokens` is 1–16384, default 1024.
The request is non-streaming and returns one text string. An empty answer is an
error; a reasoning model may need a larger token budget before producing final
text. Increasing the budget does not guarantee that a filtered or failed request
will succeed.

### VLM Describe

Supply one `IMAGE`, a vision-capable model, a description instruction in `prompt`,
and `max_tokens` (1–8192, default 512). The default instruction asks for an image
description suitable for an image-generation prompt. The image is sent as an
inline PNG in a chat request. The output is a `STRING`.

### TTS

Supply `model`, `text`, a model-specific `voice`, and `speed` (0.5–2, default 1).
When the service declares voices, the selector offers them. Otherwise enter a
voice ID accepted by that model. Switching models chooses a declared voice or
clears the previous voice. A blank voice is rejected before inference.

The service must return 16-bit PCM WAV audio for `response_format=wav`. A server
returning MP3, streaming chunks, or another WAV sample format needs adaptation.
The output is ComfyUI `AUDIO`.

### STT

Supply one `AUDIO` clip and a transcription model. `language` is optional; leave
it empty for automatic detection or provide a supported ISO-639-1 language code.
The plugin sends WAV audio and expects a JSON `text` string. The output is a
`STRING`.

Image-input nodes accept a batch size of one; speech transcription accepts one
audio clip per request. Split larger batches upstream. The plugin does not
silently drop extra images or audio clips.

### Video Generate

Supply `model`, `prompt`, `duration` in whole seconds, `aspect_ratio`, and
`resolution`. The public variant also exposes `generate_audio`; the dedicated
variant instead preserves any audio the service returns without requesting an
independent audio switch.

Common presets include `480p`, `720p`, `768p`, `1080p`, and `4k`. Metadata can
provide additional or narrower choices. These presets are not a compatibility
promise. Public pricing bands indicate priced resolutions, not all generation
modes a service supports.

Dedicated video also offers `resolution=custom` and `width`/`height` (128–8192).
With a preset, width and height fields are hidden and do not override it. With
custom dimensions, the explicit width and height determine the size and ratio.
The service validates supported shapes. It may align the resulting dimensions
or frame count, so requested and actual duration can differ.

Under **Advanced settings**, `job_id` is empty for a new generation and
`wait_timeout` defaults to 1800 seconds (10–14400). The read-only **Video task**
field shows progress and an accepted task's ID. These are not API credentials.

Video nodes currently support **text-to-video**. They do not accept image,
first/last frame, audio, or video reference inputs. A model requiring those
inputs needs a different workflow/adapter, even if it appears in a catalog.

## 7. Build image workflows

For a first public image:

```text
EcoHash Image Generate.IMAGE → Preview Image.images
```

For permanent output, use **Save Image** instead of or alongside the preview.
Choose a currently available image model, enter a prompt, start with dimensions
the model documents, and run. An illustrative prompt is:

```text
A ceramic teapot on a pale wooden table beside a window, soft morning light,
realistic materials, clean product photography, no text or watermark.
```

For a dedicated image, use **EcoHash Dedicated Image Generate**, choose the saved
connection and that endpoint's exact model ID, then use the same output wiring.

For editing:

```text
Load Image.IMAGE → EcoHash Image Edit.image → Preview Image
```

Choose an edit-capable model and enter an instruction such as `Make the teapot
deep blue while preserving its shape and lighting.` Use the dedicated variant
when the edit model is on your selected deployment.

## 8. Build language and vision workflows

For prompt enhancement:

```text
EcoHash LLM.STRING → EcoHash Image Generate.prompt → Preview Image
```

Convert a downstream text widget to an input if your ComfyUI UI requires it, then
connect the string socket. In the LLM, select `prompt_enhance` and enter the idea
in `text`. The LLM and image model can be public, dedicated, or one of each.

For image description and regeneration:

```text
Load Image → EcoHash VLM Describe → EcoHash Image Generate → Preview Image
```

Connect `Load Image.IMAGE` to `VLM Describe.image`, then its `STRING` to the image
generator's `prompt`. A vision-capable deployment is required for the VLM stage.
To inspect text alone, use a compatible text preview, such as **Preview as Text**
(`PreviewAny` in the bundled example). Preview-node availability and labels depend
on your ComfyUI version and installed node packs.

## 9. Build speech workflows

For speech synthesis:

```text
EcoHash TTS.AUDIO → Preview Audio.audio
```

Use **Save Audio** or another compatible audio output if you need a permanent
file. Select the model and a supported voice before running.

For transcription:

```text
Load Audio.AUDIO → EcoHash STT.audio → text preview
```

For a speech round trip:

```text
EcoHash Dedicated TTS.AUDIO → EcoHash Dedicated STT.audio → text preview
                         ↘ Preview Audio
```

The two dedicated nodes can select different connections. A transcription string
can feed an LLM's `text` or another node's prompt input.

## 10. Build video workflows

For a public video, wire:

```text
EcoHash Video Generate.video → Save Video.video
```

For a dedicated-instance demo:

1. Verify the global key and save the instance's connection.
2. Add **EcoHash Dedicated Video Generate** and **Save Video**.
3. Choose the intended connection and an exact text-to-video model ID.
4. Enter your prompt, a service-supported duration, ratio, and resolution.
5. Leave `job_id` empty for a new task.
6. Connect `video` to **Save Video.video**.
7. Set a filename prefix such as `video/EcoHash_demo`; keep Save Video's automatic
   format/codec defaults unless you need a specific supported output format.
8. Run once and wait. The Video task field shows the accepted job ID.
9. Preview the result and locate the saved file under ComfyUI's output directory.

The generator downloads an MP4 to the ComfyUI temporary directory. **Save Video**
makes the result persistent and retains the returned audio when compatible with
the selected save format/codec. Native frame decoding and audio processing are
not separate EcoHash workflow nodes in this API mode.

A dedicated instance is selected by the connection URL and the model ID accepted
at that URL. A successful public-model request does not verify your dedicated
instance, and the presence of an instance ID in a model list does not establish
the correct video submission route. The deployment must support the required
video lifecycle described in [section 16](#16-required-inference-api-behavior).

The optional `job_id` **output** is a string available after the generation node
finishes. Leave it unconnected for an ordinary demo, or connect it to a text
preview/saver you have installed. Do not connect it back to the same node's
`job_id` **input**: that would create a cycle. During execution or after failure,
copy the task ID from Video task or the ComfyUI server log instead.

## 11. Recover a video task

Video creation is submitted once. The plugin never automatically retries a
creation POST or switches to another protocol/model after a failed submission.
A lost POST response can still correspond to a remote task; inspect the service
before submitting another generation.

When you have an accepted task ID:

1. Keep the original connection; task IDs belong to their original service.
2. Open **Advanced settings** on the video node.
3. Paste the existing ID into `job_id`.
4. Increase `wait_timeout` if needed and run.

This path polls and downloads the existing task without creating a new one.
Generation fields do not regenerate or edit that task. Clear `job_id` before
intentionally creating a new video.

`wait_timeout` is the total video wait budget; the connection timeout is a
per-request setting. Individual lifecycle requests also have shorter internal
caps, so raising the connection timeout alone does not extend the whole job
budget. The video download limit is 512 MiB.

Stopping or interrupting ComfyUI stops local waiting. It does not cancel the
remote job. A failed, cancelled, or expired remote job needs investigation;
resuming it does not restart it. Keep the ID until you have recovered the output
or established what happened remotely.

## 12. Compose public and dedicated models

Normal ComfyUI socket types allow useful combinations:

| Workflow | What stays local |
| --- | --- |
| Public LLM → dedicated image generation → Save Image | The graph, returned image handling, and saving |
| Dedicated VLM → public image generation → Preview Image | Input-image encoding and output preview |
| Dedicated TTS → dedicated STT → public LLM | Audio conversion and graph execution between API calls |
| Public or dedicated video generation → local video processing | Downloaded media and any later local processing |

Each dedicated node chooses its own connection. Official EcoHash connections
share the global key, while independent services use their own credentials.
Models and available operations can change. Refresh their catalogs and verify
each operation instead of treating a brand name as a capability contract.

When adapting a native template, preserve ordinary preprocessing and downstream
output nodes that still have meaningful inputs. Native weight-loading, LoRA,
conditioning, sampling, and latent decoding cannot be retained as active controls
of an API call unless the backend explicitly supports that execution model. Do
not keep disconnected or ignored nodes merely to make the graph appear unchanged.

## 13. Use the bundled templates

Open the template browser and locate this plugin, or import a JSON from
[`example_workflows`](../example_workflows/). Depending on your ComfyUI version,
this is exposed as **Templates** or **Workflow → Browse Templates**.

| File | Workflow |
| --- | --- |
| `text_to_image.json` | Public image generation and preview |
| `dedicated_text_to_image.json` | Dedicated image generation and preview |
| `enhance_then_generate.json` | Public LLM enhancement, image generation, preview |
| `dedicated_enhance_then_generate.json` | Dedicated LLM, dedicated image generation, preview |
| `describe_and_regenerate.json` | Load image, public vision description, image generation |
| `dedicated_describe_and_regenerate.json` | Load image, dedicated vision and image models |
| `tts_voiceover.json` | Public TTS and audio preview |
| `dedicated_tts_voiceover.json` | Dedicated TTS and audio preview |
| `dedicated_speech_roundtrip.json` | Dedicated TTS, STT, and previews |
| `text_to_video.json` | Public video generation and saving |
| `dedicated_text_to_video.json` | Dedicated video generation and saving |

Dedicated templates start without a selected connection. Select your own saved
connection and replace model/voice placeholders before running. Example models
are not a live availability guarantee. Image-description examples refer to
ComfyUI's sample `example.png`; choose an actual local input if it is absent.

## 14. Caching and fresh generations

ComfyUI can reuse completed node outputs when their inputs have not changed.
Pressing Run again does not always make a new API call. **Cached result** means
the previous result was reused, not that a new request completed instantly.

For an intentionally fresh image, change an input, such as the seed or prompt.
`seed=-1` requests service-side randomness but the literal widget value `-1` is
still the same ComfyUI input; it does not by itself force a new cached node run.
Use ComfyUI's seed control, when provided, to change the actual input each time.

Video nodes have no seed or forced-regeneration switch. Change the prompt or
another valid generation input when a fresh result is intended, and leave
`job_id` empty. Setting an existing job ID explicitly requests recovery instead
of generation. A changed timeout or key can also invalidate a cache, so review
your intent before rerunning a workflow with a blank task ID.

Changing the global key invalidates public-node caches and official dedicated
connection caches. Changing a dedicated URL, key, timeout, or configured video
mapping invalidates the affected execution signature. Connection renaming keeps
the underlying connection ID.

## 15. Server configuration

The settings UI is recommended for interactive use. Environment variables and
INI files are alternatives for server administration. Set environment variables
on the **ComfyUI backend process**, not merely in a browser or unrelated shell.

```bash
export ECOHASH_API_KEY="eco_YOUR_KEY_HERE"
```

Or copy the plugin's `config.ini.example` to its local `config.ini`:

```ini
[ecohash]
api_key = eco_YOUR_KEY_HERE
```

An explicitly configured INI shortcut for one dedicated endpoint is:

```ini
[dedicated]
base_url = https://api.ecohash.com/inference-instances/INSTANCE_ID/proxy/v1
timeout = 300
```

Its internal connection ID is `dedicated`; it appears only when a URL has been
configured. That shortcut is optional. Normal UI-created connections have
automatically generated internal IDs and need no INI section.

Equivalent endpoint variables for that shortcut are:

```bash
export ECOHASH_DEDICATED_BASE_URL="https://api.ecohash.com/inference-instances/INSTANCE_ID/proxy/v1"
export ECOHASH_DEDICATED_TIMEOUT="300"
```

For an independent endpoint, use its own key:

```ini
[connection:studio]
name = Studio service
base_url = https://YOUR_SERVICE_HOST/v1
api_key = YOUR_INDEPENDENT_ENDPOINT_KEY
timeout = 300
```

`ECOHASH_DEDICATED_API_KEY` applies to an independently authenticated `dedicated`
shortcut. It does not override the global credential for official EcoHash URLs.
Named INI connection IDs use 1–64 letters, digits, underscores, or hyphens.

Per-field precedence is **nonempty environment value → saved `connections.json`
value → `config.ini` → default**. Environment-managed UI fields are locked.
Public URL and timeout are fixed; the public timeout is 180 seconds. Dedicated
timeouts default to 300 seconds and must be positive. Restart ComfyUI after
changing its launch environment.

Keep both local configuration files out of source control. The UI writes
`connections.json` with owner-only permissions on POSIX; the filesystem's access
controls still govern its protection on other platforms. These files are not a
per-user credential vault for an untrusted shared ComfyUI installation.

## 16. Required inference API behavior

No node or connection asks you to choose a protocol. The plugin uses the
operation contract appropriate to the selected node; deployments must implement
that contract or provide a service-side adapter.

| Operation | Route relative to the API prefix | Required response |
| --- | --- | --- |
| Image generation | `POST /images/generations` | JSON `data[0].b64_json` or a downloadable `data[0].url` |
| Image editing | `POST /images/edits` | Same image result; accepts multipart PNG `image` |
| LLM / VLM | `POST /chat/completions` | Text at `choices[0].message.content` |
| TTS | `POST /audio/speech` | 16-bit PCM WAV bytes |
| STT | `POST /audio/transcriptions` | JSON string at `text` |
| Public video | `POST /video/generations`, `GET /video/jobs/{id}` | Accepted job ID, supported lifecycle status, and a completed download URL |
| Dedicated video | `POST /videos`, `GET /videos/{id}`, `GET /videos/{id}/content` | Accepted job ID, supported lifecycle status, and an MP4 or returned download URL |

Image generation sends `model`, `prompt`, `size`, `response_format=b64_json`,
and optional positive `steps` / nonnegative `seed`. Image edits send multipart
`model`, `prompt`, `size`, and PNG bytes. LLM uses messages, temperature, and
max tokens; VLM uses text and inline image content. TTS requests WAV; STT uploads
WAV. Non-video nodes expect synchronous results and reject asynchronous HTTP 202
responses that would require a separate task adapter.

Dedicated video normally sends multipart `model`, `prompt`, `seconds`, and
`size`. Public video sends the EcoHash gateway's JSON generation fields. Accepted
HTTP 200/202 video tasks are polled through their corresponding lifecycle. A
`completed` result must provide downloadable video content; supported pending
states include queued, pending, processing, in-progress, and running.

Inference credentials authenticate the API call. Image result URLs are downloaded
without forwarding that credential. Video result URLs and content redirects are
also fetched without the inference key; only a constructed API content route
receives it. Returned URLs must therefore be independently downloadable, for
example through a service-issued signed link.

A route named `/videos` is not sufficient evidence of a compatible create
payload. A native-only container requiring extra JSON fields needs adaptation.
Administrators can use an explicit, server-side
[video request mapping](VIDEO_REQUEST_MAPPING.md), bound to the exact connection
URL, model ID, and current runtime metadata. It is a local deployment-specific
compatibility bridge, not a model-family switch or a protocol selector. Standard
deployments need no mapping. Unknown fields and model names do not cause the
plugin to guess an adapter or retry a creation request.

This plugin does not launch instances, install server-side weights, attach
LoRAs, offer arbitrary sampler controls, execute arbitrary remote ComfyUI graphs,
or provide reference-conditioned video generation. A dedicated model must
support the operation you select; deployment ownership alone is not evidence
of operation compatibility.

## 17. Troubleshooting

| Symptom | What to check |
| --- | --- |
| EcoHash nodes missing | Install in the actual ComfyUI custom-nodes folder; install dependencies in its Python environment; inspect the startup log; restart the backend and reload the browser. |
| Connection or model controls look stale | Finish any current save, refresh models, reload the browser after updates, and check for duplicate plugin installations. |
| A small value popup appears instead of the property panel | ComfyUI's canvas widgets use compact editors. Select the node and open ComfyUI's property/parameters panel for the full inspector; this behavior belongs to the frontend. |
| Some labels appear in Chinese | UI labels follow ComfyUI's locale. The plugin supplies translations; class IDs, model IDs, and some service errors remain unchanged. Change ComfyUI's language setting and refresh if necessary. |
| Global key missing | Save it once in EcoHash settings or configure `ECOHASH_API_KEY` / `[ecohash] api_key` for the backend process. |
| HTTP 401 | Check the active key source, expiration/revocation, and any environment variable overriding the saved key. |
| HTTP 403 | Check the account's access to the deployment or operation. Verify the selected connection and the service's access rules. |
| HTTP 402 | Check your EcoHash account credit and billing state. |
| HTTP 404 | Verify the API prefix, deployed model ID, endpoint route, and instance availability. Gateway and instance-proxy model IDs may differ. |
| HTTP 400/422 or `task is required` | The selected service rejected the payload. Check supported parameters and the deployment contract; a native-only video container may need an administrator-installed mapping. |
| Connection exists but node says select/configure a connection | Select the real connection in that node. Imported workflows may reference an ID that does not exist on this server. |
| Reachable but not verified | `/models` is absent or incompatible. Reachability alone does not establish authentication or inference support. |
| Model absent from picker | Refresh, check the correct connection, and inspect declared capabilities. Enter an exact ID manually when appropriate; manual entry does not add unsupported operations. |
| Unsupported size or duration | Use values supported by the actual deployment; preset sizes and priced resolutions do not prove support. |
| Empty LLM completion | Increase `max_tokens` for a reasoning model when the token budget ended, or investigate filtering and service failures. |
| Voice is blank or rejected | Refresh voices or enter a valid voice for this model. A voice from another model may not be compatible. |
| Unsupported audio / WAV error | TTS must return 16-bit PCM WAV; STT needs one valid audio clip. |
| Single-image / single-audio error | Split a batch upstream. These nodes do not process every element of a batch automatically. |
| Video timeout or interruption | Keep the accepted task ID, retain its original connection, and use the recovery procedure before submitting again. |
| Video completed remotely but download failed | Resume the same task; check result URL expiry, content access, valid MP4 output, available disk space, and the 512 MiB limit. |
| Run returns immediately | Check Execution status: unchanged node inputs may reuse ComfyUI's cache. |
| Native UNET/CLIP/VAE/LoRA file missing | Those are local model-loader nodes. A model API key does not supply native weights; use an API workflow or a full environment containing the required files. |

Do not repeatedly queue an identical failed video creation after a lost response.
Keep the error and any task ID; first establish whether the service created a task.

## 18. Updating, sharing, and removing the plugin

Update with Manager or Git in the plugin folder, using the intended branch.
Reinstall requirements if they change, restart the backend, and refresh the
browser. A Git update does not deploy or update inference models. Packaged
catalog snapshots and old saved selections may differ from live availability.

Workflow JSON contains model IDs, internal connection IDs, prompts, and settings.
It does not contain the connection manager's keys. Shared prompts and input media
can still be private. A recipient configures their own key and connections, then
selects the appropriate local connection in each dedicated node. Matching display
names alone do not make different internal IDs interchangeable.

Older plugin video workflows can migrate retired protocol/step/seed fields while
preserving applicable values and links. A migrated native workflow still needs
a compatible service contract; migration is not proof that native controls were
preserved as remote API parameters.

For backup, keep workflows and server configuration separately. Protect any
configuration backup as a credential file. Removing the plugin or deleting a
connection does not revoke an EcoHash key or stop a remote inference instance.
Manage those resources through EcoHash itself when needed.

## 19. Verification and support

Use the checks appropriate to the claim you need:

| Check | Establishes | Does not establish |
| --- | --- | --- |
| Global key verification | Authenticated access to the model-list endpoint | Successful inference for every model |
| Save connection / Refresh models | Discovery at the selected URL, or a clearly reported fallback | Compatibility with every operation and parameter |
| Generate test image / Test text inference | A real image/chat call for the chosen model | Other modalities or deployments |
| A workflow that returns and saves media | End-to-end execution for that connection, model, and request | Arbitrary native workflow equivalence or future catalog availability |

The manager's test-image and test-text actions require explicit inference consent
and can incur charges. Video and speech are tested through their workflows.
Existing video IDs can test retrieval without another creation request.

For maintainers, run the automated checks in an environment with the ComfyUI
tensor/audio dependencies and pytest available:

```bash
python -m pytest -q
node --test tests/test_ui.mjs tests/test_manager.mjs
node --check web/ecohash.js
git diff --check
```

Automated tests cover simulated services and error paths; they do not certify
every live deployment. Real image and dedicated-video verification records are
under [`tests`](../tests/), with historical versus current behavior identified.

When reporting a problem, include the plugin commit/version, ComfyUI/frontend
versions, node class, selected model ID, redacted API prefix, error details, and
video task ID if available. Share a sanitized workflow when useful. Never include
an API key, populated connection file, or private media without reviewing it.
Use the [repository issue tracker](https://github.com/ecohash-ai/ComfyUI-EcoHash/issues)
for plugin problems and [EcoHash documentation](https://docs.ecohash.com) for
account and deployment setup.
