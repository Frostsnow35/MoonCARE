# GLM-5.1 聊天响应加速 SPEC

> 变更日期：2026-05-13  
> 影响范围：`backend/app/config.py`、`backend/app/services/agent_service.py`、`backend/app/agents/llm_service.py`、`backend/app/api/v1/chat.py`、`frontend/src/api/index.js`、`frontend/src/views/Chat.vue`、`backend/tests/test_p0_safety_and_prompts.py`、`backend/tests/test_vllm_integration.py`  
> 状态：已完成后端 deadline、前端等待阈值和通用 OpenAI-compatible 加速 provider；需要用真实 GLM-5.1 端点压测

## 为什么做（Why）

当聊天模型切换为 GLM-5.1 时，当前系统会长时间等待模型返回。根据当前代码，后端 OpenAI-compatible client timeout 为 60 秒，前端 Axios timeout 为 60 秒，Chat 页面本地等待为 40 秒；`AgentService.get_response()` 还会在 async API 流程中同步执行 Router 和 Agent 的 LLM 调用。结果是 GLM-5.1 慢推理时，用户会看到“正在组织回复”持续很久，缺少 15-20 秒内的可控反馈。

本次目标不是更换模型、降低 prompt 质量或绕过安全路由，而是在保留 GLM-5.1 推理能力的前提下建立两层加速：第一层是可插拔 OpenAI-compatible 推理加速端点（例如 vLLM、SGLang、LMDeploy 或其他内网服务），第二层是交互时间预算。模型能在预算内返回时使用完整模型回复；模型超时时，后端必须在 15-20 秒内返回安全、温柔、可解释的承接消息，并明确标记 `reply_status=timeout_fallback`，避免前端无响应。

## 要改变什么（What Changes / BREAKING）

| 编号 | 变更 | 类型 | 状态 |
| --- | --- | --- | --- |
| C-001 | 新增 `LLM_REQUEST_TIMEOUT_SECONDS` 与 `CHAT_AGENT_REPLY_TIMEOUT_SECONDS` 配置 | 兼容新增 | 已完成 |
| C-002 | `AgentService.get_response()` 使用 `asyncio.to_thread + wait_for` 包住同步 Router/LLM 调用 | 行为优化 | 已完成 |
| C-003 | LLM 客户端 timeout 从固定 60 秒改为配置值，默认 18 秒 | 行为优化 | 已完成 |
| C-004 | 超时返回 `timeout_fallback`，保留安全路由结果字段和 actions | 兼容新增 | 已完成 |
| C-005 | REST / WebSocket 响应增加 `reply_status` 与 `elapsed_ms` | API 兼容新增 | 已完成 |
| C-006 | 前端等待阈值改为 22 秒，并针对 `timeout_fallback` 显示可重试提示 | 体验优化 | 已完成 |
| C-007 | 补测试证明慢 Router 不会拖过时间预算，危机 fallback 仍优先 | 测试补强 | 已完成 |
| C-008 | 新增 `LLM_PROVIDER=accelerated`，通过 OpenAI-compatible 协议接入 vLLM/SGLang/LMDeploy 等推理加速引擎 | 架构优化 | 已完成 |

BREAKING：无必填参数或路径变更。新增字段为可选兼容字段，旧前端可忽略。

## 会影响什么（Impact）

| 影响面 | 正向影响 | 风险 | 规避 |
| --- | --- | --- | --- |
| 聊天体验 | 15-20 秒内有明确回复，不再无限等待 | 超时 fallback 不如 GLM 完整回复细腻 | 仅在超时时启用；正常路径仍使用 GLM-5.1 完整回复 |
| 推理质量 | 不切换小模型、不削弱主模型 prompt | deadline 可能截断慢请求 | 服务端 timeout 明确可配置；后续可接 streaming/pending 完整回复 |
| 推理引擎 | GLM-5.1 可从普通远端 API 切换到本地/内网加速端点 | 引擎兼容性依赖实际部署 | 后端只依赖 OpenAI-compatible API；不写死某个引擎私有接口 |
| 后端稳定 | 同步 LLM 调用移到线程，避免阻塞 event loop | 慢请求线程可能继续短时间运行 | LLM client timeout 与 wait_for 接近，限制滞留时间 |
| 安全 | 危机表达仍进入安全兜底或 Intervention | 高风险场景超时后仍需安全文案 | 超时 fallback 根据 `risk_level` 与危机词选择安全版本 |
| 前端 | 错误提示更快、更清楚 | 过短前端 timeout 抢在后端前失败 | 前端 22 秒，后端默认 18 秒，留网络余量 |

## 具体怎么做、怎样算完成（SHALL + WHEN/THEN）

### SHALL 需求

| 编号 | 需求 |
| --- | --- |
| R-001 | 系统 SHALL 保留现有 `PerceptionAgent -> Router -> Agent` 安全路由，不因加速绕过风险感知。 |
| R-002 | 系统 SHALL 默认在 `CHAT_AGENT_REPLY_TIMEOUT_SECONDS=18` 秒内结束后端等待。 |
| R-003 | LLMService SHALL 使用 `LLM_REQUEST_TIMEOUT_SECONDS` 配置创建 OpenAI-compatible client，默认 18 秒。 |
| R-004 | AgentService SHALL 将同步 `router.route()` 放入线程，并用 `asyncio.wait_for` 控制总等待。 |
| R-005 | WHEN 模型在预算内返回，系统 SHALL 使用完整模型回复，不替换为小模型或模板。 |
| R-006 | WHEN 模型超时且无危机信号，系统 SHALL 返回温柔承接型 fallback，说明“这次模型响应慢，我先接住你”，并允许重试。 |
| R-007 | WHEN 模型超时且用户有自杀/自残/轻生等危机信号，系统 SHALL 返回安全兜底，不等待普通模型回复。 |
| R-008 | API SHALL 返回 `reply_status`：`ok`、`timeout_fallback` 或 `error_fallback`。 |
| R-009 | API SHALL 返回 `elapsed_ms`，用于后续定位 GLM-5.1 响应耗时。 |
| R-010 | 前端 SHALL 把聊天等待阈值改为略高于后端 deadline，并对 `timeout_fallback` 给出重试提示。 |
| R-011 | LLMService SHALL 支持 `LLM_PROVIDER=accelerated`，读取 `ACCELERATED_LLM_BASE_URL`、`ACCELERATED_LLM_API_KEY`、`ACCELERATED_LLM_MODEL_NAME`。 |
| R-012 | 加速引擎架构 SHALL 不改变 Agent prompt、记忆上下文、安全感知和危机路由。 |

### WHEN/THEN 验收场景

| 编号 | WHEN | THEN |
| --- | --- | --- |
| A-001 | WHEN Router/LLM 调用 5 秒仍不返回，且测试 deadline 为 0.01 秒 | THEN `get_response()` 在短时间内返回 `intent=timeout_fallback` |
| A-002 | WHEN 普通用户消息触发 timeout fallback | THEN 回复不包含医疗诊断，不制造危机焦虑，并包含“先陪你/先接住你”类承接 |
| A-003 | WHEN 用户说“我想自残”且 Router 超时 | THEN 返回 `SAFE_INTERVENTION_FALLBACK` 或等价安全兜底 |
| A-004 | WHEN Router 在 deadline 内返回 | THEN 保留 Router 的模型回复、intent 和 actions |
| A-005 | WHEN REST API 成功返回 | THEN payload 包含 `reply_status` 与 `elapsed_ms` |
| A-006 | WHEN 前端等待超过 22 秒 | THEN 停止本轮等待并提示可重试，不让用户无限等 |
| A-007 | WHEN `LLM_PROVIDER=accelerated` 且模型名为 `glm-5.1` | THEN LLMService 使用加速端点和该模型名创建 OpenAI-compatible client |

## 如何处理废弃或迁移（REMOVED + Reason/Migration）

| REMOVED | Reason | Migration |
| --- | --- | --- |
| 固定 60 秒 LLM client timeout | GLM-5.1 慢推理时交互不可控 | 迁移为 `LLM_REQUEST_TIMEOUT_SECONDS`，默认 18 |
| 前端 40-60 秒等待 | 超出目标 15-20 秒 | 迁移为后端 18 秒、前端 22 秒 |
| async API 内直接等待同步 Router/LLM | 易阻塞请求链路 | 迁移为 `asyncio.to_thread + wait_for` |
| 只在 `vllm` provider 中表达推理加速 | 无法平滑切换 SGLang、LMDeploy 或其他 GLM 加速端点 | 迁移为通用 `accelerated` provider，`vllm` 保持兼容 |
