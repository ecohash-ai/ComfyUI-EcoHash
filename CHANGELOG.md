# Changelog

## 1.1.0

- Add dedicated-model nodes for image generation and editing, language, vision,
  text-to-speech, and speech-to-text.
- Add asynchronous public and dedicated text-to-video generation, with task
  progress, MP4 output, and recovery using an existing task ID.
- Organize the fourteen nodes into Public Models and Dedicated Models.
- Add a connection manager with one global EcoHash API Key for official public
  and dedicated endpoints, connection verification, and image/text test actions.
- Discover models and capabilities dynamically, with manual model IDs when
  needed, without model-family routing rules or a protocol selector.
- Support explicit server-side request mappings for dedicated video deployments
  that require additional creation fields.
- Improve connection loading, credential redaction, parameter guidance, and
  workflow migration.
- Add a comprehensive English user guide, Comfy Registry installation
  instructions, and public/dedicated workflow templates.
