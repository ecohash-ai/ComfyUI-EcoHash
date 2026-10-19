# EcoHash Dedicated Image Generate

1. Click **Connections / 连接设置** or open the **EcoHash** sidebar.
2. Configure `dedicated`, or add a named connection with its API prefix URL and key.
3. Save and run **Test connection**. This only queries `/models`; it does not generate.
4. Select that connection in the node. **Refresh models** discovers available IDs;
   you can also enter an exact model ID manually.
5. Enter a prompt, connect Preview Image / Save Image and queue the workflow.

Each node can select a different connection. Shared workflows carry only the connection ID
and model ID; recipients configure the same ID or choose one of their existing connections.
A missing connection is reported explicitly and never falls back to another deployment.

The API must support synchronous `POST {base_url}/images/generations`, Bearer authentication
and base64 or downloadable URL image results. Include the actual API prefix such as `/v1`.
The settings panel's **Generate test image** is a separate, explicitly confirmed real request.
