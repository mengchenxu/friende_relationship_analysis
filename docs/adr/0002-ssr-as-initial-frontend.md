# Server-Side Rendering (Jinja2) as Initial Frontend Strategy

MVP 阶段采用 FastAPI + Jinja2 服务端渲染的 Web 界面，而非现代 SPA 框架（React/Vue）。

## Considered Options

- **Jinja2 SSR（选中）**：Python 端渲染 HTML，配合渐进式 JavaScript 增强交互。学习曲线平缓，适合以 Python 为主的开发者
- **React/Vue SPA**：前后端分离，交互体验更好。拒绝理由：对项目作者当前技能水平来说门槛过高，需同时学习 JS/TS、组件化、打包工具和状态管理，会严重拖慢 MVP 交付
- **Streamlit/Gradio**：纯 Python 写 UI，最简单。拒绝理由：灵活性不足，无法学到 Web 开发核心概念

## Consequences

- MVP 开发效率高，项目作者在熟悉的技术栈中工作
- 界面交互体验相对传统（页面刷新），但对分析报告场景完全够用
- 现代前端框架重写已进入后续路线图；届时作者已通过 SSR 理解 HTTP 请求-响应模型，能更好地理解 SPA 解决的问题
