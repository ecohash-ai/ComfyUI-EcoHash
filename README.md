<p align="center">
  <img src="https://raw.githubusercontent.com/ecohash-ai/ComfyUI-EcoHash/main/assets/icon.png" width="96" height="96" alt="EcoHash logo">
</p>

<h1 align="center">ComfyUI-EcoHash</h1>

<p align="center">EcoHash nodes for ComfyUI — image generation &amp; editing, LLM prompt tools, vision captioning, TTS and STT, powered by the EcoHash API.</p>

---

## What is EcoHash

[EcoHash](https://ecohash.com) is a hosted inference API for image generation/editing, LLM chat,
vision-language description, text-to-speech, and speech-to-text. This package adds six ComfyUI
nodes that call the EcoHash API directly from your workflows — no local GPU or model download
required for these nodes.

Sign up at **https://ecohash.com** to get an API key. New accounts receive a small free
starter credit so you can try the nodes before adding a payment method. Full docs live at
**https://docs.ecohash.com**.

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

## Set your API key

This package deliberately has **no API-key input widget on any node**. Workflow JSON files are
frequently shared, screenshotted, or committed to git, and a key typed into a node widget would
be saved right there in plain text for anyone who opens the file. Instead, the key is read once
at request time from outside the workflow graph, using one of:

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

Get or manage your key at https://docs.ecohash.com/getting-started/api-keys.

> **Never paste your API key into a node widget, a workflow JSON, or a screenshot.** Any key
> value embedded in a saved workflow is exposed to everyone who receives that file.

## Nodes

| Node | Inputs | Outputs | Purpose |
|---|---|---|---|
| **EcoHash Image Generate** | `model` (live catalog, image models), `prompt` (string), `size` (`1024x1024`/`1024x768`/`768x1024`/`768x768`/`512x512`), `steps` (int, 0 = model default), `seed` (int, -1 = random) | `IMAGE` | Generate an image from a text prompt. |
| **EcoHash Image Edit** | `image` (`IMAGE`), `model` (catalog models that support image edit), `prompt` (string), `size` (`auto` + preset sizes; `auto` keeps the source image's dimensions) | `IMAGE` | Edit/transform an existing image with a text instruction. |
| **EcoHash LLM** | `model` (catalog `llm`/`llm_vision` models), `mode` (`chat` / `prompt_enhance` / `translate_to_english` / `custom`), `text` (string), `system_prompt` (string, used only when `mode = custom`), `temperature` (float, 0–2), `max_tokens` (int) | `STRING` | Run a chat completion. `prompt_enhance` rewrites a rough idea into a detailed image-generation prompt; `translate_to_english` converts non-English text; useful chained before an Image Generate node. |
| **EcoHash VLM Describe** | `image` (`IMAGE`), `model` (catalog `llm_vision` models), `prompt` (string, defaults to a detailed-description instruction), `max_tokens` (int) | `STRING` | Describe an input image in detail with a vision-language model — handy for turning an existing image into a prompt for regeneration or variation. |
| **EcoHash TTS** | `model` (catalog `speech_tts` models), `text` (string), `voice` (string, e.g. `af_bella`), `speed` (float, 0.5–2.0) | `AUDIO` | Synthesize speech from text. |
| **EcoHash STT** | `audio` (`AUDIO`), `model` (catalog `speech_stt` models), `language` (string, ISO-639-1 code, empty = auto-detect) | `STRING` | Transcribe speech audio to text. |

All `model` dropdowns are populated live from the EcoHash model catalog at graph-build time, so
the exact list of available models will change as EcoHash adds or retires models — check
https://docs.ecohash.com for the current lineup. If the catalog can't be reached, nodes fall back
to a packaged snapshot so the graph still loads.

ComfyUI caches node outputs — re-queueing an identical graph returns cached results without a new
API call; change any input (e.g. seed) to force a fresh call.

## Example workflows

Ready-to-load example workflows (text-to-image, prompt-enhance-then-generate,
describe-and-regenerate, and TTS voiceover) live in [`example_workflows/`](example_workflows/).
The node chains they use were exercised live against the real EcoHash API — see
[`tests/SMOKE_RESULTS.md`](tests/SMOKE_RESULTS.md) — and the workflow JSON files themselves were
validated against a live ComfyUI instance's node schema; see that folder's README for exactly
what was and wasn't verified (a literal browser load/click-Queue pass was not performed, since
this was done headlessly).

## Pricing

EcoHash is metered, pay-as-you-go usage on top of your free starter credit. See current plans and
per-model pricing at **https://docs.ecohash.com/billing/plans**.

## Support

- Bugs and feature requests: [GitHub Issues](https://github.com/ecohash-ai/ComfyUI-EcoHash/issues)
  (this repo)
- Account or billing questions: the EcoLink console support chat —
  https://docs.ecohash.com/troubleshooting/support

---

## 中文说明

ComfyUI-EcoHash 为 ComfyUI 提供 6 个节点，通过 EcoHash API 调用图像生成/编辑、LLM 对话、图像描述
（VLM）、文本转语音（TTS）和语音转文本（STT），无需本地 GPU 或下载模型。

**注册**：前往 https://ecohash.com 注册账号，新账号会获得少量免费额度用于试用；完整文档见
https://docs.ecohash.com。

**安装**：在 ComfyUI-Manager 中搜索 "EcoHash" 安装，或将本仓库 `git clone` 到
`ComfyUI/custom_nodes/` 目录下，然后 `pip install -r requirements.txt`。

**配置密钥**：本插件的节点上**没有**任何 API Key 输入框——因为工作流 JSON 经常被分享、截图或提交到
仓库，写在节点里的密钥会随之泄露。请改用环境变量 `ECOHASH_API_KEY`，或将 `config.ini.example`
复制为 `config.ini` 并填入密钥。**切勿将密钥粘贴到节点、工作流文件或截图中。**

**价格**：按量计费，详见 https://docs.ecohash.com/billing/plans。

**支持**：在本仓库的 GitHub Issues 提交问题，或通过 EcoLink 控制台的在线支持聊天获取帮助：
https://docs.ecohash.com/troubleshooting/support。
