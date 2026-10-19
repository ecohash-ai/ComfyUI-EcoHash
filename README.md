<p align="center">
  <a href="https://ecohash.com?utm_source=github&utm_medium=referral&utm_campaign=api-comfyui-always-on&utm_content=readme.logo"><img src="https://raw.githubusercontent.com/ecohash-ai/ComfyUI-EcoHash/main/assets/ecohash-logo.png" width="280" alt="EcoHash"></a>
</p>

<h1 align="center">ComfyUI-EcoHash</h1>

<p align="center">EcoHash nodes for ComfyUI — image generation &amp; editing, LLM prompt tools, vision captioning, TTS and STT, powered by the EcoHash API.</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT">
  <a href="https://registry.comfy.org/nodes/comfyui-ecohash"><img src="https://img.shields.io/badge/Comfy%20Registry-comfyui--ecohash-1a1a1a" alt="Comfy Registry"></a>
  <a href="https://docs.ecohash.com?utm_source=github&utm_medium=referral&utm_campaign=api-comfyui-always-on&utm_content=readme.docs-badge"><img src="https://img.shields.io/badge/documentation-6D28D9" alt="Documentation"></a>
  <a href="https://x.com/ecohashdev"><img src="https://img.shields.io/badge/X-@ecohashdev-000000?logo=x&logoColor=white" alt="X"></a>
  <a href="https://huggingface.co/ecohash-ai"><img src="https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-ecohash--ai-FFD21E" alt="Hugging Face"></a>
</p>

---

## What is EcoHash

[EcoHash](https://ecohash.com?utm_source=github&utm_medium=referral&utm_campaign=api-comfyui-always-on&utm_content=readme.intro) runs an NVIDIA RTX PRO 6000 GPU cloud and, on top of it,
an OpenAI-compatible inference API for open models: image generation and editing, LLM chat,
vision-language description, text-to-speech, and speech-to-text. This package adds eight ComfyUI
nodes that call that API directly from your workflows — no local GPU or model download required
for these nodes.

Need a whole GPU instead of an API call? The same account rents
[RTX PRO 6000 Blackwell instances](https://ecohash.com/gpu/rtx-pro-6000?utm_source=github&utm_medium=referral&utm_campaign=api-comfyui-always-on&utm_content=readme.gpu) (96 GB VRAM)
by the hour, so you can run a full ComfyUI stack with local checkpoints alongside these nodes.
See the [GPU cloud docs](https://docs.ecohash.com/gpu-compute/overview?utm_source=github&utm_medium=referral&utm_campaign=api-comfyui-always-on&utm_content=readme.gpu-docs).

Sign up at **[ecohash.com](https://ecohash.com?utm_source=github&utm_medium=referral&utm_campaign=api-comfyui-always-on&utm_content=readme.signup)** to get an API key. New accounts receive a small free
starter credit so you can try the nodes before adding a payment method. Full docs live at
**[docs.ecohash.com](https://docs.ecohash.com?utm_source=github&utm_medium=referral&utm_campaign=api-comfyui-always-on&utm_content=readme.docs)**.

## Install

**Option A — ComfyUI-Manager**

Open ComfyUI-Manager, search for `EcoHash`, and install "ComfyUI-EcoHash".

**Option B — git clone**

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/ecohash-ai/ComfyUI-EcoHash.git
cd ComfyUI-EcoHash
pip install -r requirements.txt
```

Restart ComfyUI after installing.

Dependencies must use **ComfyUI's Python**. For Windows Portable, run from the portable folder:

```powershell
.\python_embeded\python.exe -m pip install -r .\ComfyUI\custom_nodes\ComfyUI-EcoHash\requirements.txt
```

For Desktop or a virtual-environment install, use that installation's Python environment.
After updating the plugin, restart the ComfyUI server and refresh the browser.

## Connection manager

Open the **EcoHash** cloud tab in the sidebar, click **Connections** (Chinese: **连接设置**) on any EcoHash
node, or use **Extensions → EcoHash → EcoHash connections**.

1. For public models (A), select `public`, enter your EcoHash key and **Save**.
2. For dedicated images (B), configure `dedicated` or **Add connection**. Give it a stable
   ID (for example `studio`), display name, API prefix URL, key and timeout.
3. Click **Test connection**. This only queries `/models`; it does not generate an image.
   A successful model-list response verifies that request. A server without `/models` is
   shown as reachable with authentication/image support still unverified.
4. Use **Refresh models** to discover models. Dedicated nodes also accept manual model IDs.
5. Select a connection and model in your workflow, enter the prompt and run.

**Generate test image** is a separate action requiring a model ID and explicit confirmation
before making a real, potentially billable generation request. Its preview appears in the manager.

Keys are saved only on the ComfyUI server in git-ignored `connections.json` (owner-readable
and writable on POSIX). The settings API never returns saved keys. Leave a key field blank to
keep its value. Per-field precedence: **nonempty environment variable → saved settings →
config.ini → default**. Environment-managed fields are marked and locked. The public API URL
and public timeout (180 seconds) are fixed; dedicated timeout defaults to 300 seconds.

Each Dedicated image node has an optional `connection` selection; existing workflows default
to `dedicated`. Multiple independent deployments can run in one workflow. Shared workflows store
only connection IDs and model IDs. Recipients create the same ID locally or select another
connection. Missing IDs produce a mapping error and never fall back to another deployment.
The original six public nodes keep using `public`.

The manager configures this ComfyUI server. Use it from the same trusted server environment
where you manage your existing ComfyUI configuration.

## Set your API key

This package deliberately has **no API-key input widget on any node**. Workflow JSON files are
frequently shared, screenshotted, or committed to git, and a key typed into a node widget would
be saved right there in plain text for anyone who opens the file. Instead, the key is read once
at request time from outside the workflow graph. The connection manager is the easiest option;
server deployments can also use:

1. **Environment variable** — set `ECOHASH_API_KEY` in the environment ComfyUI runs in, e.g.:

   ```bash
   export ECOHASH_API_KEY="eco_..."
   ```

2. **`config.ini`** — copy `config.ini.example` (in this folder) to `config.ini` and paste your
   key:

   ```ini
   [ecohash]
   api_key = eco_YOUR_KEY_HERE
   ```

   `config.ini` is git-ignored by this repo so it won't be committed by accident.

Get or manage your key in the [API keys guide](https://docs.ecohash.com/getting-started/api-keys?utm_source=github&utm_medium=referral&utm_campaign=api-comfyui-always-on&utm_content=readme.apikey).

> **Never paste your API key into a node widget, a workflow JSON, or a screenshot.** Any key
> value embedded in a saved workflow is exposed to everyone who receives that file.

## Nodes

| Node | Inputs | Outputs | Purpose |
|---|---|---|---|
| **EcoHash Image Generate** | `model`, `prompt`, `size` (presets / `custom`), `steps` (0 = model default), `seed` (-1 = random), optional `width`/`height` | `IMAGE` | Generate an image from a text prompt. |
| **EcoHash Image Edit** | `image` (`IMAGE`), `model` (catalog models that support image edit), `prompt` (string), `size` (`auto` + preset sizes; `auto` keeps the source image's dimensions) | `IMAGE` | Edit/transform an existing image with a text instruction. |
| **EcoHash Dedicated Image Generate** | `model` (deployed ID), `prompt`, `size`, `steps`, `seed`, optional `width`/`height` and `connection` | `IMAGE` | Generate via the selected dedicated endpoint. |
| **EcoHash Dedicated Image Edit** | `image`, `model` (deployed ID), `prompt`, `size`, optional `width`/`height` and `connection` | `IMAGE` | Edit via the selected dedicated endpoint, if supported. |
| **EcoHash LLM** | `model` (catalog `llm`/`llm_vision` models), `mode` (`chat` / `prompt_enhance` / `translate_to_english` / `custom`), `text` (string), `system_prompt` (string, used only when `mode = custom`), `temperature` (float, 0–2), `max_tokens` (int) | `STRING` | Run a chat completion. `prompt_enhance` rewrites a rough idea into a detailed image-generation prompt; `translate_to_english` converts non-English text; useful chained before an Image Generate node. |
| **EcoHash VLM Describe** | `image` (`IMAGE`), `model` (catalog `llm_vision` models), `prompt` (string, defaults to a detailed-description instruction), `max_tokens` (int) | `STRING` | Describe an input image in detail with a vision-language model — handy for turning an existing image into a prompt for regeneration or variation. |
| **EcoHash TTS** | `model` (catalog `speech_tts` models), `text` (string), `voice` (string, e.g. `af_bella`), `speed` (float, 0.5–2.0) | `AUDIO` | Synthesize speech from text. |
| **EcoHash STT** | `audio` (`AUDIO`), `model` (catalog `speech_stt` models), `language` (string, ISO-639-1 code, empty = auto-detect) | `STRING` | Transcribe speech audio to text. |

Public model menus initially use the cache or packaged snapshot without blocking node loading
on the network. The frontend refreshes separately; **Refresh models** updates menus and reports
live/cache/fallback status. Capability hints show editing support, default steps, supported sizes
and voices when supplied by the service. Unknown private-model capabilities remain unspecified.

Image nodes offer landscape/portrait presets and `custom` dimensions (multiples of 16, 64–8192
per side). Width/height appear only in custom mode; the model must support the requested size.
LLM's system prompt appears only in custom mode. TTS lists voices when provided by the service;
otherwise enter a model-specific voice ID. Switching away from Kokoro clears its `af_bella`
default unless the new model supplies voice choices.

ComfyUI caches node outputs — re-queueing an identical graph returns cached results without a new
API call; change any input (e.g. seed) to force a fresh call.
Node status shows waiting, completed, cached, interrupted or failed execution.

## Dedicated inference (B)

The two **EcoHash/Dedicated** nodes call a separately deployed image model. The original six
nodes continue to use the public EcoHash API (A), so both can be used in the same workflow.
Dedicated nodes accept a free-text model ID and do not consult the public model catalog.

Add the following to your local, git-ignored `config.ini` (also see `config.ini.example`):

```ini
[dedicated]
base_url = https://YOUR_DEDICATED_HOST/v1
api_key = YOUR_DEDICATED_KEY_HERE
timeout = 300
```

Alternatively, set these variables in the environment of the **ComfyUI server process**:

```bash
export ECOHASH_DEDICATED_BASE_URL="https://YOUR_DEDICATED_HOST/v1"
export ECOHASH_DEDICATED_API_KEY="YOUR_DEDICATED_KEY_HERE"
export ECOHASH_DEDICATED_TIMEOUT="300"
```

Nonempty environment values override saved UI settings, which override INI values. Timeout is in seconds
and defaults to 300. `base_url` must include the service's actual API prefix: `/v1` is **not**
added automatically. Trailing slashes are removed; a prefix such as `/deployments/my-model/v1`
is preserved. The dedicated key is independent of `ECOHASH_API_KEY`; there is no fallback to
the public key. Neither the endpoint nor its key is stored in node widgets or workflow JSON.

Additional connections can also be configured as INI sections:

```ini
[connection:studio]
name = Studio image model
base_url = https://ANOTHER_HOST/v1
api_key = YOUR_DEDICATED_KEY_HERE
timeout = 300
```

In ComfyUI, add **EcoHash Dedicated Image Generate**, enter the exact model ID served by your
deployment, select its `connection`, then connect its output to **Preview Image** or **Save Image**. To edit, connect
an `IMAGE` to **EcoHash Dedicated Image Edit** and enter a model ID that supports editing.
An example workflow is in [`example_workflows/dedicated_text_to_image.json`](example_workflows/dedicated_text_to_image.json).
Dedicated nodes invalidate their cached result when their endpoint, key or timeout changes.

The current protocol is a **synchronous, OpenAI-compatible image API**:

- Generation: `POST {base_url}/images/generations`, JSON with `model`, `prompt`, `size`,
  `response_format=b64_json`, and optional `steps` / `seed`.
- Editing: `POST {base_url}/images/edits`, multipart form with `model`, `prompt`, `size` and
  an `image` PNG file. `size=auto` sends the source dimensions explicitly.
- Authentication: `Authorization: Bearer <dedicated key>`.
- Result: `{"data": [{"b64_json": "..."}]}` or `{"data": [{"url": "https://..."}]}`.
  Result URLs must be downloadable without the inference key; that key is never forwarded
  when fetching an image URL. Each call produces one `IMAGE` from the first result.

An HTTP 202 job response requires a task-polling adapter and is reported as unsupported.
Other response schemas, authentication schemes, and deployment-routing headers also require
an adapter. API requests do not follow redirects; configure the final API base URL directly.
LoRA, ControlNet and other deployment-specific parameters are not exposed by these nodes yet.

Before testing a real service, verify it implements this protocol. The automated tests cover
configuration, credential isolation and real loopback HTTP generation/editing against a test
service; they do not establish compatibility with any particular dedicated deployment.
See [`tests/DEDICATED_RESULTS.md`](tests/DEDICATED_RESULTS.md) for the verification record.

After configuring your real endpoint, run the node-level smoke test in a Python environment
with the ComfyUI dependencies available (this makes real, billable API calls):

```bash
python scripts/smoke_dedicated.py --model YOUR_DEPLOYED_MODEL_ID
# If the deployment also supports editing:
python scripts/smoke_dedicated.py --model YOUR_DEPLOYED_MODEL_ID --edit-model YOUR_EDIT_MODEL_ID
# Use a named connection:
python scripts/smoke_dedicated.py --connection studio --model YOUR_DEPLOYED_MODEL_ID
```

The script saves generated/edited PNGs in a temporary directory and prints their paths and
dimensions. It exercises the node implementations directly; it does not start ComfyUI or
validate browser interaction or workflow execution.

## Example workflows

Ready-to-load example workflows (text-to-image, prompt-enhance-then-generate,
describe-and-regenerate, and TTS voiceover) live in [`example_workflows/`](example_workflows/).
Open **Workflow → Browse Templates** and find this plugin, or drag a JSON file into the canvas.
Node help is available in each node's information panel. The original public API smoke-test
record is in [`tests/SMOKE_RESULTS.md`](tests/SMOKE_RESULTS.md); dedicated verification is
recorded separately in [`tests/DEDICATED_RESULTS.md`](tests/DEDICATED_RESULTS.md).

## Pricing

EcoHash is metered, pay-as-you-go usage on top of your free starter credit. See current plans and
per-model pricing at **[the billing docs](https://docs.ecohash.com/billing/plans?utm_source=github&utm_medium=referral&utm_campaign=api-comfyui-always-on&utm_content=readme.pricing)**.

## Support

- Bugs and feature requests: [GitHub Issues](https://github.com/ecohash-ai/ComfyUI-EcoHash/issues)
  (this repo)
- Account or billing questions: the EcoLink console support chat —
  [EcoHash support](https://docs.ecohash.com/troubleshooting/support?utm_source=github&utm_medium=referral&utm_campaign=api-comfyui-always-on&utm_content=readme.support)

## Local verification

Using a ComfyUI Python environment (including PyTorch, Pillow, NumPy and aiohttp), install
pytest and run `python -m pytest -q`. Frontend helper checks use `node --test tests/test_ui.mjs`;
no frontend build step is required. The tests isolate credentials and use temporary local HTTP
services. See [`tests/DEDICATED_RESULTS.md`](tests/DEDICATED_RESULTS.md) for the running-ComfyUI
verification and the remaining checks for a real dedicated deployment.

---

## 中文说明

EcoHash 提供 NVIDIA RTX PRO 6000 GPU 云，以及构建其上的 OpenAI 兼容推理 API。ComfyUI-EcoHash 为
ComfyUI 提供 6 个公共 API 节点，调用图像生成/编辑、LLM 对话、图像描述（VLM）、文本转语音（TTS）
和语音转文本（STT），以及 2 个专属推理图像节点。这些节点无需本地 GPU 或下载模型。

**GPU 云**：同一个账号也可按小时租用 [RTX PRO 6000 Blackwell 实例](https://ecohash.com/gpu/rtx-pro-6000?utm_source=github&utm_medium=referral&utm_campaign=api-comfyui-always-on&utm_content=readme.gpu-zh)（96 GB 显存），
用于运行带本地模型的完整 ComfyUI 环境，详见 [GPU 云文档](https://docs.ecohash.com/gpu-compute/overview?utm_source=github&utm_medium=referral&utm_campaign=api-comfyui-always-on&utm_content=readme.gpu-docs-zh)。

**注册**：前往 [ecohash.com](https://ecohash.com?utm_source=github&utm_medium=referral&utm_campaign=api-comfyui-always-on&utm_content=readme.signup-zh) 注册账号，新账号会获得少量免费额度用于试用；完整文档见
[docs.ecohash.com](https://docs.ecohash.com?utm_source=github&utm_medium=referral&utm_campaign=api-comfyui-always-on&utm_content=readme.docs-zh)。

**安装**：在 ComfyUI-Manager 中搜索 "EcoHash" 安装，或将本仓库 `git clone` 到
`ComfyUI/custom_nodes/` 目录下，然后 `pip install -r requirements.txt`。

**界面配置**：打开侧栏的 **EcoHash** 云图标，或节点上的 **Connections / 连接设置**。
公共模型选择 `public` 并保存密钥；专属模型配置 `dedicated` 或添加具名连接。先保存，再测试连接、
刷新模型。连接检测不生成图片；测试出图需要单独勾选确认，将发送实际生成请求。
密钥只保存在服务端 `connections.json`，不会写进工作流，读取配置接口也不会返回密钥。
环境变量和 `config.ini` 仍可使用，优先级为：环境变量 → 界面设置 → `config.ini`。

**专属推理（B）**：在 `config.ini` 添加 `[dedicated]`，配置 `base_url`、`api_key` 和可选的
`timeout`（秒，默认 300）；也可使用 `ECOHASH_DEDICATED_BASE_URL`、`ECOHASH_DEDICATED_API_KEY`
和 `ECOHASH_DEDICATED_TIMEOUT` 环境变量。`base_url` 要包含服务实际的 API 前缀，插件不会自动添加
`/v1`。添加 **EcoHash Dedicated Image Generate / Edit** 节点，直接填写部署模型 ID 即可调用，
无需模型出现在公共目录中。专属节点的 `connection` 可分别选择不同部署，也可通过
`[connection:连接ID]` 配置多个端点。分享工作流时接收方配置同名连接，或在节点中重新选择。
A、B 使用独立密钥，可以在同一工作流混用。当前支持同步图像生成/编辑
接口和 base64 / 图片 URL 返回；异步任务或其他协议需要另行适配，详见上方 Dedicated inference。

**参数和帮助**：`size=custom` 时显示宽高；LLM 的 `custom` 模式才显示系统提示词。
音色按模型元数据显示可选项，未提供列表时支持手填。示例可从工作流模板浏览器加载；节点的信息面板
提供使用说明。Windows Portable 安装依赖时请使用内嵌 Python，命令见上方 Install。

**价格**：按量计费，详见[计费文档](https://docs.ecohash.com/billing/plans?utm_source=github&utm_medium=referral&utm_campaign=api-comfyui-always-on&utm_content=readme.pricing-zh)。

**支持**：在本仓库的 GitHub Issues 提交问题，或通过 EcoLink 控制台的在线支持聊天获取帮助：
[支持页面](https://docs.ecohash.com/troubleshooting/support?utm_source=github&utm_medium=referral&utm_campaign=api-comfyui-always-on&utm_content=readme.support-zh)。
