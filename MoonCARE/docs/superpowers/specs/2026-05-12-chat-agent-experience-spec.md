# MoonCARE Chat Agent Experience SPEC

> 变更日期：2026-05-12  
> 影响范围：`frontend/src/views/Chat.vue`、`frontend/src/stores/chat.js`、`frontend/src/api/index.js`、`backend/app/api/v1/chat.py`、`backend/app/services/agent_service.py`、`backend/app/agents/router.py`  
> 状态：已确认，进入实现

## 为什么做（Why）

MoonCARE 的聊天页是女性 PMS 情绪陪伴的核心入口。根据当前技术文档，后端已有 PerceptionAgent、Router、SupportAgent、KnowledgeAgent、InterventionAgent 等多 Agent 架构，但前端聊天体验仍偏基础：用户进入聊天后需要先开口，角色能力不可见，交互状态、错误恢复和温度感不足。

本任务要把聊天页完善为“Agent 主动陪伴 + 安全受控角色切换 + 高质量移动端聊天界面”。所有健康与心理相关回复仍只作参考，不替代专业诊断；任何自杀、自残、轻生等表达必须优先进入安全干预。

## 要改变什么（What Changes / BREAKING）

| 编号 | 变化 | 类型 | 状态 |
|------|------|------|------|
| C-001 | 用户进入 `/chat` 后 SHALL 先看到 Agent 主动发出的第一句话 | 新增行为 | 已确认 |
| C-002 | 前端 SHALL 提供 `自动陪伴`、`情绪宝宝`、`知识宝宝` 三种安全受控角色模式 | 新增行为 | 已确认 |
| C-003 | `/api/v1/chat/message` 和 WebSocket 消息 SHALL 接受 `agent_mode` 偏好 | API 兼容新增 | 已确认 |
| C-004 | 后端 Router SHALL 将 `agent_mode` 只作为低风险路由偏好，危机/高风险仍强制 InterventionAgent | 安全行为 | 已确认 |
| C-005 | 聊天 UI SHALL 增加连接状态、回复中、错误恢复、建议按钮和可访问交互状态 | 前端体验 | 已确认 |

### BREAKING

无删除性 breaking change。新增 `agent_mode` 为可选参数，旧调用保持兼容。

## 会影响什么（Impact）

| 范围 | 影响 | 风险 | 规避 |
|------|------|------|------|
| 用户体验 | 聊天更主动、更有温度，并能理解当前角色 | 角色切换被误解为绕过安全系统 | UI 文案说明“危机时会自动切换为安全支持” |
| 后端路由 | 支持用户偏好的 Support/Knowledge 路由 | Knowledge 模式误接管危机表达 | `risk_level in high/crisis` 优先于 `agent_mode` |
| 心理安全 | 危机优先继续贯穿主聊天 | 前端直连某 Agent 绕过 PerceptionAgent | 前端只传偏好，后端统一感知和路由 |
| 隐私安全 | 聊天内容继续纯文本渲染 | XSS 或敏感日志泄露 | 不使用 `v-html`，不新增完整聊天日志输出 |
| 性能稳定 | LLM 超时和网络失败更可恢复 | 长等待造成焦虑 | 前端显示回复中、失败提示和重试入口 |

## 具体怎么做、怎样算完成

### SHALL 需求

| ID | SHALL |
|----|-------|
| R-001 | `chatStore` SHALL 保存 `agentMode`，默认值为 `auto`。 |
| R-002 | `chatStore` SHALL 在首次进入普通聊天时插入一条 assistant 欢迎语，而不是等待用户先发送。 |
| R-003 | `Chat.vue` SHALL 渲染三段式角色切换控件：`auto`、`support`、`knowledge`。 |
| R-004 | `chatAPI.sendMessage()` SHALL 传递可选 `agent_mode` 参数。 |
| R-005 | WebSocket `sendMessage()` SHALL 在 JSON payload 中传递 `agent_mode`。 |
| R-006 | `AgentService.get_response()` SHALL 接受可选 `agent_mode` 并传给 Router。 |
| R-007 | `Router.route()` SHALL 在 low/medium 风险下尊重 `support` 或 `knowledge` 偏好。 |
| R-008 | `Router.route()` SHALL 在 high/crisis 风险下忽略 `agent_mode` 并优先 InterventionAgent 或安全兜底。 |
| R-009 | 聊天消息 SHALL 使用 Vue 文本插值渲染，禁止使用 `v-html`。 |
| R-010 | 错误提示 SHALL 温和、可恢复，不暗示用户责任。 |

### WHEN/THEN 验收场景

| 场景 | WHEN | THEN |
|------|------|------|
| A-001 | WHEN 用户首次进入普通聊天页 | THEN 页面出现 assistant 首句欢迎语 |
| A-002 | WHEN 用户选择 `知识宝宝` 并询问 PMS 知识 | THEN 后端优先路由到 KnowledgeAgent |
| A-003 | WHEN 用户选择 `知识宝宝` 但输入“我想自残” | THEN 后端仍路由到 InterventionAgent 或安全兜底 |
| A-004 | WHEN WebSocket 已连接并发送消息 | THEN payload 包含当前 `agent_mode` |
| A-005 | WHEN REST fallback 发送消息 | THEN query 参数包含当前 `agent_mode` |
| A-006 | WHEN LLM/API 失败 | THEN 前端保留用户消息，显示温和失败提示，并允许继续输入 |

## 如何处理废弃或迁移

| REMOVED / Deprecated | Reason | Migration |
|----------------------|--------|-----------|
| 将角色切换实现为前端假状态 | 会造成用户以为切换 Agent 但后端未感知 | 迁移为 `agent_mode` 后端偏好参数 |
| 向用户暴露 `InterventionAgent` 普通入口 | 容易把危机干预娱乐化或误导用户 | 危机干预只由安全路由自动接管 |
| 进入聊天后等待用户先说第一句 | 降低陪伴感，不符合本次需求 | 首次进入由 Agent 主动欢迎 |
