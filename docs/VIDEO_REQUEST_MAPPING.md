# Server-side request mappings for nonstandard dedicated video services

Standard compatible services do not need this feature. Their nodes require only
a connection, model, prompt, duration and size. For an existing deployment that
requires native JSON fields to create a video task, a ComfyUI server administrator
can add a `video_requests` entry to that connection in the plugin's local
`connections.json`.

This is a deployment-specific compatibility bridge. It does not change or deploy
EcoLink; platform-level normalization of instance requests and capability metadata
remains a service responsibility. No protocol or native-parameter selector is
added to nodes or workflow JSON. See the [User Guide](USER_GUIDE.md#16-required-inference-api-behavior)
for the ordinary API contract and limits.

Mappings affect only the JSON creation payload at `/videos`. Polling and download
still use `/videos/{id}` and `/videos/{id}/content`. They do not rewrite API routes,
classify model families, execute arbitrary ComfyUI graphs, or add reference inputs.

## Configuration example

The following illustrates the structure, not a ready-to-use adapter. Replace the
URL, exact served model ID, identity constraints, supported capabilities and native
request fields with values established from the actual deployment's documentation
and verification.

```json
{
  "version": 1,
  "connections": {
    "studio": {
      "name": "My instance",
      "base_url": "https://api.ecohash.com/inference-instances/INSTANCE_ID/proxy/v1",
      "video_requests": {
        "exact-served-model-id": {
          "base_url": "https://api.ecohash.com/inference-instances/INSTANCE_ID/proxy/v1",
          "requires": {"pipeline_class": "DeploymentPipeline"},
          "capabilities": {
            "category": "video",
            "input_modalities": ["text"],
            "output_modalities": ["video"],
            "supported_resolutions": ["768p"],
            "video_min_duration_seconds": 4,
            "video_max_duration_seconds": 15
          },
          "request": {
            "model": {"$input": "model"},
            "prompt": {"$input": "prompt"},
            "task": "DEPLOYMENT_DOCUMENTED_TASK",
            "target": {
              "duration": {"$input": "duration"},
              "short_edge": {"$input": "short_edge"},
              "aspect_ratio": {"$input": "aspect_ratio"}
            }
          }
        }
      }
    }
  }
}
```

**Merge the mapping into the existing connection record; do not replace the whole
file with this example.** UI-created connections have generated IDs: use that
existing ID rather than creating a new `studio` record accidentally. Preserve the
saved global `public` key record and all other connections. Official EcoHash URLs
reference the global key and need no key in their own record. An independent
origin still needs its separate endpoint key.

This file contains credentials and stays outside version control. Preserve its
access permissions and protect backups. The settings API returns neither the
mapping nor saved keys. Editing a connection's name or timeout in the manager
preserves its mapping. Discovery can expose only the declared, verified capability
metadata to the frontend.

## Matching and validation

The mapping is selected by the exact API prefix, including its path, and exact
served model ID. `requires` must be a nonempty object. Every field it specifies
must match live `/models` metadata before creation. Known identity fields include
`pipeline_class`, `pipeline_name`, `task_type` and `root`, together with exposed
capability fields.

An identity mismatch or unavailable live metadata stops the mapped request before
submission. The plugin does not guess a new model, choose a native protocol from
a model name, or retry generation. If the configured URL or model ID changes,
the old mapping no longer applies and the default standard request is used.

`request` is a JSON template with typed `{"$input":"name"}` substitutions. No code
is evaluated. Available input names are:

| Input | Value |
| --- | --- |
| `model`, `prompt` | The selected model ID and prompt, which the mapping must preserve |
| `duration` | Requested whole seconds |
| `resolution` | Selected resolution label |
| `width`, `height` | Dimensions from the preset or explicit custom size |
| `short_edge` | The smaller dimension |
| `aspect_ratio` | Selected preset ratio; for custom dimensions, the reduced width/height ratio |
| `size` | The `widthxheight` string |

Fixed native defaults such as inference steps belong to the deployment mapping,
not to node widgets or workflow JSON. Reverify them when a deployment changes.
Capabilities may declare real categories, modalities, supported sizes/resolutions,
and duration limits. Leave unverified capabilities unspecified. Duration and
resolution limits declared here are checked before mapped creation; metadata
does not establish arbitrary backend behavior beyond the verified contract.

Mapping changes invalidate discovery and affected node execution cache signatures.
All creation POSTs remain single-attempt. Resuming an existing task queries and
downloads it without applying a creation mapping or creating another task.
