# EcoHash Dedicated Image Edit

Configure a named connection with **Connections / 连接设置**, select it in the node,
connect one input image and enter the exact deployed edit model ID and instruction.
Discovery lists models when `/models` is available; manual IDs remain supported.

The endpoint must support synchronous multipart `POST {base_url}/images/edits` with an
`image` PNG, `model`, `prompt` and `size`. `auto` sends the source dimensions. Services
may round dimensions. The server must actually offer image editing for the chosen model.

Connection IDs are saved in workflows; endpoint keys stay on the ComfyUI server.
