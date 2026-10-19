# EcoHash Dedicated LLM

Configure a dedicated connection in the EcoHash sidebar, then select it in this node.
Choose a discovered language model or enter its exact deployed model ID manually.

Modes: `chat`, `prompt_enhance`, `translate_to_english` and `custom`. The system prompt
is used only in custom mode. Connect the STRING output to an image node's prompt or
another text input. Increase `max_tokens` if a reasoning model returns no answer text.

The endpoint must support synchronous, non-streaming `POST {base_url}/chat/completions`
with Bearer authentication, `messages`, `temperature`, `max_tokens`, and response text
at `choices[0].message.content`. Use **Test text inference** in Connections for an
explicitly confirmed real test. The connection test only queries `/models`.

Each node can use a different connection. Credentials are stored outside the workflow.
