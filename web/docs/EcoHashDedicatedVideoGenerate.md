# EcoHash Dedicated Video Generate

Select **Connection** and **Model**, then enter the prompt, duration and size. Open
**Connections** to add a deployment; **Save and connect** applies it to the current node.
Use a discovered model ID or enter the exact ID manually. Custom resolution exposes width/height.

There is no protocol setting. The instance must implement the platform video API; native-only
containers require a service-side adapter. Model names do not select adapters or imply capabilities.
Connect VIDEO to **Save Video** to preserve the returned MP4 and any audio track.

The `job_id` STRING output is optional: leave it unconnected, or connect to **Preview as Text**
(`source`) / **Save Text** (`text`) to record the completed task ID. During execution or after
failure, copy the ID from **Video task** instead. Do not connect it back to this same node.

**Advanced settings** contains `job_id` and the total wait timeout. An existing job ID resumes
polling/download on the same connection without generating again. Blank means new generation.
This node supports text-to-video; reference-media inputs are not implemented.
