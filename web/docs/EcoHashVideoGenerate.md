# EcoHash Video Generate

Choose a model, prompt, duration and size. Connect VIDEO to **Save Video**. Model capabilities
and priced resolution bands come from the platform; common presets do not guarantee support.
The node supports text-to-video and preserves any audio in the returned MP4.

Leave the `job_id` STRING output unconnected for normal generation. Optionally connect it
to **Preview as Text** (`source`) or **Save Text** (`text`) to record the completed task ID.
During execution or after failure, copy the ID from **Video task** instead; downstream
outputs are available only after completion. Do not connect the ID back to this same node.

No protocol configuration is needed. The platform manages model-native generation settings.
Under **Advanced settings**, leave `job_id` blank to generate, or enter an existing ID to
resume polling/download without another submission. Keep the original connection.
Stopping ComfyUI stops local waiting and does not cancel the remote task.
