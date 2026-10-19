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

## Connection list and naming follow-up

The unused default dedicated endpoint is no longer listed without an explicitly configured
URL. Dedicated node schemas and example templates start with an empty connection selection,
which is a UI state rather than a fabricated endpoint. An explicit environment/INI endpoint
remains available when configured. Missing selections are rejected before inference.

The list, Connection name field and node picker now share one human-readable name.
Internal IDs are generated automatically and are absent from normal and advanced settings.
Duplicate names (including case-only variants) are rejected; renaming keeps the connection ID.
Empty selections open the new-connection form without querying a nonexistent endpoint.

The complete Python suite passed 226 tests; frontend helpers passed 23 tests. The live
settings API listed only the current public connection and the saved Qwen connection.
All seven dedicated node schemas listed only the empty selection and that actual connection;
none included a default `dedicated` option. Browser inspection confirmed the default option
and ID suffixes were gone, with Connection name matching the list and no ID input even in
Advanced settings. No inference was submitted. Read-only evidence:
`/private/tmp/ecohash-connection-naming.json`.
