# Global EcoHash API Key verification

Date: 2026-10-19. Branch: `feat/dedicated-inference`.

The plugin now has one EcoHash API Key setting, shared by public models and dedicated
connections at the exact `https://api.ecohash.com` origin on the default HTTPS port.
Dedicated instance proxy prefixes use the same credential. New official connections save
only their address/name/settings and reference the global key. No legacy credential
migration or per-official-connection override was added, as requested.

Other origins, including HTTP, alternate ports, lookalike domains and other subdomains,
require an independent endpoint key. The global key is never a fallback for those URLs.
Endpoint keys are configured under Advanced connection settings. Global-key rotation
invalidates all seven public and seven dedicated node cache signatures and the affected
dedicated model-discovery caches; third-party credentials and caches stay independent.

Validation:

- Full Python suite: 224 passed. Frontend helper suite: 22 passed.
- JavaScript syntax and `git diff --check`: passed.
- Tests cover the origin boundary, global configuration precedence, one-key/multiple-endpoint
  settings API flow, no key copies in new official connection records, key rotation, all
  node cache signatures, authenticated request headers, missing-key prevalidation and redaction.
- Local ComfyUI loaded all 14 nodes with no API key, URL or protocol inputs on the nodes.
- Real authenticated connection checks passed (HTTP 200) for `public`, `minimax-h3-demo`
  (instance-247 proxy) and `qwen-image-248` (platform API). Both dedicated connections
  reported `sources.api_key = global` and resolved the exact same credential as the public API.
- These live checks only read model catalogs; no image, video, text or audio generation
  was submitted. They verify authentication/discovery, not inference support for every model.
- Browser verification confirmed a single global key input and a working Verify action;
  selected dedicated connections showed name/address and no separate key input. Adding
  an official connection required no key; changing the unsaved URL to an independent
  origin exposed its required key under Advanced settings. That temporary form was not saved.

The settings API returned no credentials. Existing local files were preserved by the install
helper; the plugin's new official-connection resolver ignores per-connection key values.
Keys stay on the ComfyUI server and are not serialized into workflows.

Redacted local evidence: `/private/tmp/ecohash-global-key-live.json`.
