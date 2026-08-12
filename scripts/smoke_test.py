#!/usr/bin/env python3
"""Live smoke test for ComfyUI-EcoHash against a running local ComfyUI instance.

This script does NOT need the EcoHash API key itself: the key lives in the
environment of the ComfyUI *server* process (ECOHASH_API_KEY), which is where
the EcoHash nodes read it from when they execute. This script is just an HTTP
client that queues API-format prompt graphs and polls for results.

Usage:
    # In one terminal (from the ComfyUI checkout):
    ECOHASH_API_KEY=eco_... .venv/bin/python main.py --cpu --port 8188

    # In another terminal (from this repo, or anywhere with `requests`):
    python3 scripts/smoke_test.py [--url http://127.0.0.1:8188]

Exit code is 0 if all EcoHash nodes passed, 1 otherwise.
"""

import argparse
import sys
import time
import uuid
from datetime import datetime, timezone

import requests

DEFAULT_URL = "http://127.0.0.1:8188"
POLL_INTERVAL = 2.0
GRAPH_TIMEOUT = 240.0

# Sinks used purely so the graphs have OUTPUT_NODE entry points; ComfyUI will
# not execute any node unreachable from an output node.
PREVIEW_IMAGE = "PreviewImage"
PREVIEW_AUDIO = "PreviewAudio"
PREVIEW_ANY = "PreviewAny"


def build_graphs():
    """Return the list of (label, graph, ecohash_nodes) tuples to run.

    ecohash_nodes maps node_id -> EcoHash node class name, for the nodes in
    that graph we're actually trying to cover (excludes the Preview* sinks).
    """
    graphs = []

    # Graph 1: ImageGenerate -> ImageEdit -> PreviewImage
    #                       \-> VLMDescribe -> PreviewAny
    graph1 = {
        "1": {
            "class_type": "EcoHashImageGenerate",
            "inputs": {
                "model": "z-image-turbo",
                "prompt": "a small red apple on a plain white background, product photo",
                "size": "512x512",
                "steps": 0,
                "seed": 12345,
            },
        },
        "2": {
            "class_type": "EcoHashImageEdit",
            "inputs": {
                "image": ["1", 0],
                "model": "flux2-klein",
                "prompt": "make the apple bright green",
                "size": "auto",
            },
        },
        "3": {
            "class_type": PREVIEW_IMAGE,
            "inputs": {"images": ["2", 0]},
        },
        "4": {
            "class_type": "EcoHashVLMDescribe",
            "inputs": {
                "image": ["1", 0],
                "model": "qwen3-vl-8b-instruct",
                "prompt": "Describe this image in one short sentence.",
                "max_tokens": 128,
            },
        },
        "5": {
            "class_type": PREVIEW_ANY,
            "inputs": {"source": ["4", 0]},
        },
    }
    graphs.append((
        "image_chain",
        graph1,
        {"1": "EcoHashImageGenerate", "2": "EcoHashImageEdit", "4": "EcoHashVLMDescribe"},
    ))

    # Graph 2: LLM (prompt_enhance) -> PreviewAny
    graph2 = {
        "1": {
            "class_type": "EcoHashLLM",
            "inputs": {
                "model": "GLM-5.2",
                "mode": "prompt_enhance",
                "text": "a cat astronaut floating above the moon",
                "system_prompt": "",
                "temperature": 0.7,
                "max_tokens": 200,
            },
        },
        "2": {
            "class_type": PREVIEW_ANY,
            "inputs": {"source": ["1", 0]},
        },
    }
    graphs.append(("llm_prompt_enhance", graph2, {"1": "EcoHashLLM"}))

    # Graph 3: TTS -> PreviewAudio
    #             \-> STT -> PreviewAny
    graph3 = {
        "1": {
            "class_type": "EcoHashTTS",
            "inputs": {
                "model": "kokoro-82m",
                "text": "Hello from the EcoHash smoke test.",
                "voice": "af_bella",
                "speed": 1.0,
            },
        },
        "2": {
            "class_type": PREVIEW_AUDIO,
            "inputs": {"audio": ["1", 0]},
        },
        "3": {
            "class_type": "EcoHashSTT",
            "inputs": {
                "audio": ["1", 0],
                "model": "whisper-large-v3-turbo",
                "language": "",
            },
        },
        "4": {
            "class_type": PREVIEW_ANY,
            "inputs": {"source": ["3", 0]},
        },
    }
    graphs.append(("tts_then_stt", graph3, {"1": "EcoHashTTS", "3": "EcoHashSTT"}))

    return graphs


def queue_prompt(base_url, graph):
    client_id = str(uuid.uuid4())
    resp = requests.post(
        f"{base_url}/prompt",
        json={"prompt": graph, "client_id": client_id},
        timeout=30,
    )
    if resp.status_code != 200:
        return None, resp
    data = resp.json()
    return data.get("prompt_id"), resp


def wait_for_history(base_url, prompt_id, timeout=GRAPH_TIMEOUT):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = requests.get(f"{base_url}/history/{prompt_id}", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if prompt_id in data:
            entry = data[prompt_id]
            if entry.get("status", {}).get("completed") is True or \
               entry.get("status", {}).get("status_str") == "error":
                return entry
        time.sleep(POLL_INTERVAL)
    return None


def evaluate_graph(label, graph, ecohash_nodes, base_url):
    """Run one graph, return (results, duration, error_excerpt_or_None).

    results is a dict: node_id -> {"class": str, "passed": bool, "detail": str}
    """
    results = {nid: {"class": cls, "passed": False, "detail": "not run"}
               for nid, cls in ecohash_nodes.items()}

    start = time.monotonic()
    prompt_id, resp = queue_prompt(base_url, graph)
    if prompt_id is None:
        excerpt = resp.text[:500]
        for nid in results:
            results[nid]["detail"] = f"prompt rejected (HTTP {resp.status_code}): {excerpt}"
        return results, time.monotonic() - start, f"HTTP {resp.status_code}: {excerpt}"

    entry = wait_for_history(base_url, prompt_id)
    duration = time.monotonic() - start

    if entry is None:
        for nid in results:
            results[nid]["detail"] = f"timed out waiting for history after {GRAPH_TIMEOUT:.0f}s"
        return results, duration, "timeout"

    status = entry.get("status") or {}
    status_str = status.get("status_str")

    if status_str == "success":
        for nid in results:
            results[nid]["passed"] = True
            results[nid]["detail"] = "ok"
        return results, duration, None

    # status_str == "error": find which node failed and which ones already
    # executed successfully, via the execution_error message payload.
    executed = set()
    failing_node = None
    exc_message = None
    for event, msg in status.get("messages", []):
        if event == "execution_error":
            executed = set(msg.get("executed", []))
            failing_node = msg.get("node_id")
            exc_message = msg.get("exception_message")
            break

    for nid, info in results.items():
        if nid == failing_node:
            info["detail"] = f"FAILED: {exc_message}"
        elif nid in executed:
            info["passed"] = True
            info["detail"] = "ok (ran before graph failure)"
        else:
            info["detail"] = f"blocked: upstream/graph error at node {failing_node}: {exc_message}"

    excerpt = f"node {failing_node}: {exc_message}"
    return results, duration, excerpt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="ComfyUI base URL")
    args = parser.parse_args()

    try:
        requests.get(f"{args.url}/system_stats", timeout=10)
    except requests.RequestException as exc:
        print(f"ERROR: cannot reach ComfyUI at {args.url}: {exc}")
        return 2

    all_results = {}
    graph_meta = []

    for label, graph, ecohash_nodes in build_graphs():
        print(f"\n=== Graph: {label} ===")
        results, duration, error_excerpt = evaluate_graph(label, graph, ecohash_nodes, args.url)
        for nid, info in sorted(results.items()):
            status = "PASS" if info["passed"] else "FAIL"
            print(f"  [{status}] {info['class']} (node {nid}): {info['detail']}")
            all_results[f"{label}:{nid}"] = {"class": info["class"], "passed": info["passed"], "detail": info["detail"]}
        graph_meta.append({
            "label": label,
            "duration": duration,
            "error_excerpt": error_excerpt,
        })
        print(f"  graph duration: {duration:.1f}s")

    total = len(all_results)
    passed = sum(1 for r in all_results.values() if r["passed"])
    print(f"\n{passed}/{total} EcoHash node checks passed across {len(graph_meta)} graphs")

    write_results_md(all_results, graph_meta, args.url)

    return 0 if passed == total else 1


def write_results_md(all_results, graph_meta, base_url):
    import pathlib
    out_path = pathlib.Path(__file__).resolve().parent.parent / "tests" / "SMOKE_RESULTS.md"

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Live Smoke Test Results",
        "",
        f"- Date: {now}",
        f"- ComfyUI base URL: {base_url}",
        "",
        "## Per-node results",
        "",
        "| Graph | Node ID | EcoHash Node | Result | Detail |",
        "|---|---|---|---|---|",
    ]
    for key, info in sorted(all_results.items()):
        label, nid = key.split(":", 1)
        status = "PASS" if info["passed"] else "FAIL"
        detail = info["detail"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {label} | {nid} | {info['class']} | {status} | {detail} |")

    lines += ["", "## Graph durations", ""]
    for gm in graph_meta:
        err = f" (error: {gm['error_excerpt']})" if gm["error_excerpt"] else ""
        lines.append(f"- `{gm['label']}`: {gm['duration']:.1f}s{err}")

    total = len(all_results)
    passed = sum(1 for r in all_results.values() if r["passed"])
    lines += ["", f"**{passed}/{total} EcoHash node checks passed.**", ""]

    out_path.write_text("\n".join(lines) + "\n")
    print(f"\nWrote results to {out_path}")


if __name__ == "__main__":
    sys.exit(main())
