# MoonCARE Chat Memory Agent SPEC

> 变更日期：2026-05-12  
> 影响范围：`backend/app/api/v1/chat.py`、`backend/app/services/agent_service.py`、`backend/app/services/chat_memory_service.py`、`backend/app/models/chat_memory.py`、`backend/app/agents/*`、`backend/app/prompts/*`、`frontend/src/stores/chat.js`、`frontend/src/views/Chat.vue`  
> 状态：已确认，进入实现

## 为什么做（Why）

MoonCARE 的聊天入口是女性经前情绪健康陪伴的核心。根据当前技术文档，项目已经有 PerceptionAgent、Router、SupportAgent、KnowledgeAgent、InterventionAgent 和非显式经前状态了解能力，但现有 LLM 调用只看到当前一条用户消息，缺少最近上下文和可复用用户画像。

本次目标是在不绕过安全感知层的前提下，让 AI 能在多次交互中记住用户明确表达过的偏好、情绪特点、经前常见体验和重要个人事实，并把这些记忆自然用于后续陪伴、疏导和答疑。PMS 相关内容只作为自我观察和陪伴参考，不作为正式筛查、检验或诊断。

## 要改变什么（What Changes / BREAKING）

| 编号 | 变化 | 类型 | 状态 |
|------|------|------|------|
| C-001 | 新增 `chat_memories` 表，持久化用户偏好、个人事实、情绪特点和经前体验摘要 | 新增数据结构 | 计划中 |
| C-002 | 聊天回复前注入最近若干轮上下文和长期记忆摘要 | 新增行为 | 计划中 |
| C-003 | Support/Knowledge/Auto 模式使用不同的 system prompt 引导策略 | 行为优化 | 计划中 |
| C-004 | 用户消息入库后抽取最小必要记忆，危机文本不进入普通记忆 | 安全行为 | 计划中 |
| C-005 | API/WebSocket 返回可选 `memory_state` 摘要，前端默认不把敏感画像暴露成“档案页” | API 兼容新增 | 计划中 |

### BREAKING

无删除性 breaking change。新表和新返回字段均为兼容新增；旧前端忽略 `memory_state` 不会报错。

## 会影响什么（Impact）

| 范围 | 影响 | 风险 | 规避 |
|------|------|------|------|
| 心理安全 | 回答更贴合用户历史状态 | 错把危机表达当普通偏好保存 | 危机/自残/轻生文本只走 Intervention，不写入普通记忆 |
| 隐私 | 新增个人事实与情绪特点存储 | 敏感信息泄露或日志暴露 | 只存摘要，不存完整原文；日志不输出用户全文；后续上线需接入 JWT |
| Agent 模式 | 不同模式侧重点更清晰 | 用户误以为可用模式绕过安全 | Router 始终先做 Perception，high/crisis 覆盖任何模式 |
| LLM 质量 | 有最近上下文和长期偏好 | prompt 过长、超时 | 限制最近轮数、记忆条数和单条长度 |
| 前端体验 | 用户知道系统会温和延续上下文 | 记忆提示过强造成被监视感 | 默认只显示轻量提示，不展示完整记忆列表 |
| 安全渲染 | 前端继续纯文本显示消息 | XSS | 不使用 `v-html`，继续 Vue 文本插值 |

## 具体怎么做、怎样算完成

### SHALL 需求

| ID | SHALL |
|----|-------|
| R-001 | 系统 SHALL 新增 `ChatMemory` 数据模型，字段至少包含 `user_id`、`category`、`key`、`value`、`confidence`、`source`、`last_seen_at`。 |
| R-002 | 系统 SHALL 在生成回复前读取当前 session 最近上下文和用户长期记忆，并注入 Agent prompt。 |
| R-003 | 系统 SHALL 在用户消息入库后抽取记忆候选，只保存最小摘要，不保存完整敏感原文。 |
| R-004 | 系统 SHALL 在 `contains_crisis_signal()` 或 `is_sensitive=True` 时跳过普通记忆写入。 |
| R-005 | Support 模式 SHALL 优先共情、复述用户特点、提供小步疏导；Knowledge 模式 SHALL 优先解释知识，并结合用户偏好调整表述；Auto 模式 SHALL 允许 Router 依据风险和问题类型选择。 |
| R-006 | Intervention 模式 SHALL 不被 `agent_mode` 或长期记忆覆盖。危机回复必须优先安全、安抚和求助资源。 |
| R-007 | prompt 模板 SHALL 从 `backend/app/prompts/` 加载，不在 Agent 类里硬编码长提示词。 |
| R-008 | REST `/api/v1/chat/message` 和 WebSocket SHALL 都使用同一套记忆构建与记忆写入逻辑。 |
| R-009 | 前端 SHALL 继续通过 `chatStore` 管理聊天状态，并保存服务端返回的轻量 `memoryState`。 |
| R-010 | 所有健康/PMS 相关回复 SHALL 包含“仅供参考/不替代专业诊断”类边界，不能扮演医生。 |

### WHEN/THEN 验收场景

| 场景 | WHEN | THEN |
|------|------|------|
| A-001 | WHEN 用户说“我喜欢晚上听轻音乐，别一下子给我很多建议”后再次聊天 | THEN 后续 Support 回复可自然采用更少建议和轻音乐偏好 |
| A-002 | WHEN 用户上一轮说“经前总是睡不好、学习效率低” | THEN 下一轮 AI 可以延续“睡眠和学习受影响”的上下文，不要求用户重复 |
| A-003 | WHEN 用户选择 Knowledge 模式询问“为什么经前烦躁” | THEN 后端优先走 KnowledgeAgent，并用知识解释而不是只做情绪安抚 |
| A-004 | WHEN 用户选择 Knowledge 模式但说“我想自残” | THEN 后端忽略模式偏好，进入 Intervention 或安全兜底 |
| A-005 | WHEN 用户发送 HTML/脚本片段 | THEN 前端按纯文本显示，不执行脚本 |
| A-006 | WHEN LLM 或记忆抽取失败 | THEN 主聊天仍返回安全 fallback，不暴露堆栈和敏感文本 |

## 如何处理废弃或迁移（REMOVED + Reason/Migration）

| REMOVED / Deprecated | Reason | Migration |
|----------------------|--------|-----------|
| 只把当前一条用户消息传给 LLM | AI 无法延续上下文，用户需要反复解释 | 改为注入最近上下文和长期记忆摘要 |
| 把 Agent 模式只当作前端标签 | 用户期望不同模式有不同交互侧重点 | 将模式传入后端 prompt 与 Router，但不覆盖危机优先 |
| 保存完整用户敏感原文作为长期记忆 | 隐私风险过高 | 只保存短摘要、分类和置信度；危机文本不进普通记忆 |
| 在 prompt 中硬编码模式策略 | 不符合 prompt 文件化规范 | 新增/更新 `backend/app/prompts/` 模板 |
