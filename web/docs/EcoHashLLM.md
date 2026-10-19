# EcoHash LLM

Configure the **public** key with **Connections**. Choose a public language model and mode:

- `prompt_enhance`: turn an idea into an English image prompt.
- `translate_to_english`: translate text into English.
- `chat`: send a plain user message.
- `custom`: reveal and use your own system prompt.

Connect `STRING` to a downstream prompt. Reasoning models may need a larger `max_tokens`
budget before they produce visible text. This node uses the public API, independently of
the dedicated image connections.
