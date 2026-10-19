# EcoHash Dedicated VLM Describe

Connect one IMAGE, select a dedicated connection and enter a deployed model ID that
supports image inputs. Model discovery filters known vision capabilities; a model
without metadata can still be entered manually. A text-only model cannot describe images.

The node sends `POST {base_url}/chat/completions` with a PNG data URL and text prompt
in the user message. It reads `choices[0].message.content` as STRING. Connect this to
an image generator's prompt, including one using a different dedicated connection.

The service must support synchronous OpenAI-compatible vision messages and Bearer auth.
