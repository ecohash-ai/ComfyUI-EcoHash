# 非标准专有视频实例的服务端请求映射

标准实例无需配置此功能。节点仍然只需要连接、模型、提示词、时长和尺寸。
对于必须使用原生 JSON 创建任务的已有部署，可由 ComfyUI 服务管理员在插件的
`connections.json` 中为现有连接增加 `video_requests`。这是本地兼容桥接，
没有修改或部署 EcoLink；长期应由平台统一实例创建请求和能力元数据。

映射只支持 `/videos` 创建 JSON，查询和下载仍使用 `/videos/{id}`、
`/videos/{id}/content`，不会改写调用地址或按品牌匹配模型。需要参考媒体的生成任务不在此功能范围内。

以下是结构示例，字段值必须以实际部署的接口文档和验证结果为准，不能直接用于任意实例：

```json
{
  "version": 1,
  "connections": {
    "studio": {
      "base_url": "https://service.example/v1",
      "api_key": "KEEP_EXISTING_KEY",
      "video_requests": {
        "exact-served-model-id": {
          "base_url": "https://service.example/v1",
          "requires": {"pipeline_class": "DeploymentPipeline"},
          "capabilities": {
            "category": "video",
            "input_modalities": ["text"],
            "output_modalities": ["video"],
            "video_min_duration_seconds": 4,
            "video_max_duration_seconds": 15
          },
          "request": {
            "model": {"$input": "model"},
            "prompt": {"$input": "prompt"},
            "task": "DEPLOYMENT_DOCUMENTED_TASK",
            "target": {
              "duration": {"$input": "duration"},
              "short_edge": {"$input": "short_edge"},
              "aspect_ratio": {"$input": "aspect_ratio"}
            }
          }
        }
      }
    }
  }
}
```

请在已有连接记录中合并映射，保留密钥；不要用示例覆盖整个文件。该文件包含凭据，
应保持仅当前用户可读写，不提交版本库。连接设置 API 仅返回脱敏摘要，不返回映射或密钥；
在界面中修改连接名称、超时等会保留映射。模型列表仅展示映射声明的能力信息。

只有准确的 URL（包括 API 前缀）和模型 ID 才能选中映射；`requires` 必须非空，
其中声明的字段必须与实时 `/models` 返回的部署信息逐项一致。当前支持校验
`pipeline_class`、`pipeline_name`、`task_type`、`root` 及已公开的能力字段。
映射身份不匹配或无法获取实时信息时，在创建前报错；不会切换到另一个模型、猜协议或重发生成请求。
URL 或模型 ID 变化后，旧映射不再适用，使用默认标准请求。

`request` 是 JSON 模板，仅支持类型保持的 `{"$input":"名称"}` 替换，不执行代码。
可引用 `model`、`prompt`、`duration`、`resolution`、`width`、`height`、`short_edge`、
`aspect_ratio`、`size`。宽高为当前尺寸预设或自定义尺寸，`short_edge` 是其中较小值，
预设尺寸保留所选画面比例，自定义尺寸的比例由宽高约分获得，`size` 为 `宽x高`。
映射必须原样保留所选模型和提示词。
步数等固定原生参数属于部署配置，不进入节点或工作流。默认值应随部署版本更新并重新验证。

`capabilities` 可声明真实的类别、输入/输出模态、支持尺寸/分辨率以及时长上下限；
没有可靠依据的能力应留空。生成前会校验声明的时长和分辨率限制。未映射模型仍走默认标准请求。
修改映射会使模型发现和节点执行缓存失效；无论请求采用何种表示，创建 POST 均不会自动重试。
已有任务恢复只查询和下载，不执行映射，也不再次生成。
