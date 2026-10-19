# EcoHash Image Generate

Configure the **public** API key in the **EcoHash** sidebar or click **Connections / 连接设置**.
Choose a public model, enter a prompt and connect `IMAGE` to Preview Image or Save Image.

**Refresh models** updates the dropdown and reports whether live or cached data was used.
`steps=0` uses model defaults. Use ComfyUI's seed control to choose fixed or randomized output.
Choose `size=custom` to reveal width/height; supported sizes depend on the selected model.

This node always uses the public API. For a private deployment use **EcoHash Dedicated Image Generate**.
Keys stay in server settings and are excluded from workflow JSON.
