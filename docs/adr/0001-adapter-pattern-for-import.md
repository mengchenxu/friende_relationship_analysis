# Multi-Platform Import via Adapter Pattern

聊天记录来源于不同平台（微信、QQ、Telegram 等），每个平台的导出格式不同。我们采用 **Adapter 模式**：定义一个统一的内部数据模型（Contact、Conversation、Message），每个平台对应一个 Adapter 负责将平台特有格式转换为内部模型。

## Considered Options

- **Adapter 模式（选中）**：分析引擎只依赖内部模型，平台相关内容完全隔离在 Adapter 层
- **硬编码各平台解析**：在分析引擎中直接处理各平台格式差异。拒绝理由：新增平台需要修改分析代码，耦合度高，难以测试

## Consequences

- 新增平台仅需新写一个 Adapter，分析引擎零改动
- 可用 Test Data Adapter 先跑通全链路，微信数据获取难题不阻塞开发
- 跨平台联系人合并在内部模型上有明确的实现路径
