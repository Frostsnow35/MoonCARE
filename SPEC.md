# MoonCARE P1 SPEC - AI 聊天式非显性经前状态评估闭环

> 文档版本：v1.4  
> 变更日期：2026-05-12  
> 影响范围：`frontend/src/stores/chat.js`、`backend/app/api/v1/chat.py`、`backend/app/services/agent_service.py`、`backend/app/agents/router.py`、`backend/app/models/conversation.py`、`backend/app/services/emotion_engine.py`、`backend/app/prompts/`  
> 当前状态：待确认，确认后执行开发  

---

## 1. Why

MoonCARE 的核心产品意图不是让用户完成一个显性的 PMS 问卷，而是在登录/注册后的自然聊天中，由情绪宝宝逐步理解用户经前阶段的情绪、身体感受、生活影响和安全风险，并把这些信息沉淀为状态画像。

当前项目已经具备聊天入口、Agent 路由、`Conversation` 落库、`InterviewAgent`、`PerceptionAgent` 和 `EmotionEngine`，但闭环仍未完成：

| 当前问题 | 为什么必须处理 |
|----------|----------------|
| 经前状态了解仍偏显性 | `/interview/start` 更像单独流程，弱化“自然聊天理解状态”的产品差异化 |
| `chatStore` 仍有显性 `isInterviewMode` | 前端状态语义会把能力导向“访谈/筛查模式”，不符合非显性体验 |
| 聊天回答未形成可复用画像 | 用户表达只能停留在对话记录里，无法支撑后续陪伴个性化 |
| `EmotionEngine._get_negative_emotion_ratio()` 仍是占位值 | 对话负向情绪没有真实进入情绪分析，风险结果不可信 |
| 危机优先需要贯穿新流程 | 经前状态了解不能吞掉自杀、自残、轻生等高风险表达 |

本任务的目标是完成从“自然聊天收集信号”到“结构化状态画像”再到“EmotionEngine 分析”的 P1 闭环，同时保持非诊断、仅供参考和危机优先。

---

## 2. What Changes / BREAKING

### 2.1 功能变化

| 编号 | 变化 | 类型 | 状态 |
|------|------|------|------|
| C-001 | `/api/v1/chat/message` 和 `WS /api/v1/chat/ws/{user_id}` SHALL 成为经前状态了解的主入口 | 新增行为 | 计划中 |
| C-002 | 系统 SHALL 新增隐藏评估状态机，用于判断是否自然追问、等待回答、提取信号、冷却和完成 | 新增行为 | 计划中 |
| C-003 | `chatStore` SHALL 保存后端返回的隐藏 `assessmentState`，但 SHALL NOT 渲染为筛查进度 | 前端状态变化 | 计划中 |
| C-004 | 后端 SHALL 新增经前状态画像数据结构，保存情绪核心、身体感受、功能影响、危机信号和提取置信度 | 数据变化 | 计划中 |
| C-005 | `EmotionEngine` SHALL 使用真实对话负向比例和经前状态信号替代占位值 | 算法变化 | 计划中 |
| C-006 | Agent prompt SHALL 新增自然追问和结构化提取模板，并从 `backend/app/prompts/` 加载 | Prompt 变化 | 计划中 |

### 2.2 BREAKING

| 编号 | BREAKING 变更 | 影响 | 迁移要求 |
|------|---------------|------|----------|
| B-001 | 新开发不再以 `isInterviewMode` / `interviewPhase` 作为主聊天评估状态 | 依赖显性 interview 状态的前端逻辑需要调整 | 迁移到 `assessmentState.status` |
| B-002 | 新开发不再把 `/interview/start` 作为 P1 主入口 | 手动从显性入口启动的流程不代表主闭环 | 保留 `/interview/*` 兼容，但主链路接入 `/chat` |
| B-003 | `EmotionEngine` 风险结果会因真实聊天信号而变化 | 既有测试中假设 `negative_ratio = 0.0` 的结果会失效 | 更新测试数据和预期值 |
| B-004 | 新增状态画像表后，情绪分析依赖更多用户维度 | 空数据场景下置信度和风险解释可能变化 | 增加无画像、低置信度、部分画像测试 |

---

## 3. Impact

| 范围 | 影响 | 风险 | 规避 |
|------|------|------|------|
| 用户体验 | 用户在聊天中被自然了解状态，不进入显性问卷 | 追问过密会让用户感觉被测试 | 每轮最多一个问题；拒绝后冷却 |
| 心理安全 | 任意评估状态都必须先处理危机表达 | 危机表达被当作普通经前信号 | `contains_crisis_signal` 和 `PerceptionAgent` 必须先于评估编排器执行 |
| 后端路由 | `/api/v1/chat` 返回新增 `assessment_state` | 旧前端忽略新增字段应保持兼容 | 只新增字段，不删除旧字段 |
| 前端状态 | `chatStore` 增加隐藏状态 | 误渲染成筛查进度 | 默认不展示；如展示只能用“状态小结”等非筛查文案 |
| 数据库 | 新增状态画像持久化数据 | 敏感心理信息存储增加 | 只保存最小证据片段；日志脱敏 |
| Agent | SupportAgent 可能融合自然追问 | 追问覆盖安抚或干预 | InterventionAgent 优先级不可被覆盖 |
| EmotionEngine | `pms_risk`、`mood_level`、`confidence` 会受聊天信号影响 | 文本误判放大风险 | 初始低权重；保存 `confidence`；低置信度不生成强结论 |
| 安全合规 | 健康与心理文本更敏感 | XSS、越权、敏感信息泄露 | 纯文本渲染；参数化查询；限制 `user_id`；真实部署前接入 JWT |

---

## 4. SHALL Requirements + WHEN/THEN Acceptance

### 4.1 非显性聊天主入口

| ID | SHALL 需求 |
|----|------------|
| R-001 | 系统 SHALL 通过 `/api/v1/chat/message` 和 `WS /api/v1/chat/ws/{user_id}` 承载 P1 经前状态了解主流程。 |
| R-002 | 系统 SHALL NOT 要求用户点击 `/interview/start` 才能进入 P1 经前状态了解闭环。 |
| R-003 | 前端 SHALL NOT 向用户展示“PMS筛查”“正式筛查”“检验”“诊断”“量表测评”“测评进度”等显性文案。 |

| 场景 | WHEN | THEN |
|------|------|------|
| A-001 | WHEN 用户首次进入聊天并发送真实消息 | THEN 后端可创建或更新隐藏 `assessment_state`，但前端不展示筛查入口或进度 |
| A-002 | WHEN 用户未调用 `/interview/start` 但通过聊天表达经前不适 | THEN 系统仍可自然进入经前状态了解流程 |
| A-003 | WHEN 前端收到 `assessment_state` | THEN `chatStore` 保存该状态，但默认不渲染任何筛查 UI |

### 4.2 隐藏状态机

| ID | SHALL 需求 |
|----|------------|
| R-010 | 后端 SHALL 持久化评估状态机，状态至少包含 `idle`、`eligible`、`probing`、`awaiting_answer`、`extracting`、`summarizing`、`cooldown`、`completed`、`crisis_handoff`。 |
| R-011 | 前端 SHALL 只保存服务端返回的状态摘要，SHALL NOT 自行推进可信状态。 |
| R-012 | 用户拒绝、跳过、转移话题或追问过密时，系统 SHALL 进入 `cooldown`。 |

| 场景 | WHEN | THEN |
|------|------|------|
| A-010 | WHEN 用户满足首次聊天、经前期、低情绪或主动提及条件 | THEN 状态可从 `idle` 进入 `eligible` |
| A-011 | WHEN 系统在一次回复中已经插入自然追问 | THEN 状态 SHALL 进入 `awaiting_answer`，等待用户下一轮回答 |
| A-012 | WHEN 用户表达“不想聊”“别问了”或明显转移话题 | THEN 状态 SHALL 进入 `cooldown`，默认 24 小时内不继续追问 |
| A-013 | WHEN 服务重启后再次处理同一用户同一评估周期 | THEN 后端 SHALL 能读取持久化状态，不从前端猜测状态 |

### 4.3 危机优先

| ID | SHALL 需求 |
|----|------------|
| R-020 | 系统 SHALL 在评估编排前执行危机检测。 |
| R-021 | 任意状态下检测到自杀、自残、轻生、极端绝望表达时，系统 SHALL 进入 `crisis_handoff`。 |
| R-022 | 危机回复 SHALL 由 InterventionAgent 或安全兜底生成，SHALL NOT 继续普通经前追问。 |

| 场景 | WHEN | THEN |
|------|------|------|
| A-020 | WHEN 用户消息包含“想死”“不想活”“自杀”“自残”等危机表达 | THEN 系统 SHALL 路由到 InterventionAgent 或安全兜底 |
| A-021 | WHEN 危机表达同时包含经前问题或知识问题 | THEN 危机优先，SHALL NOT 路由到 KnowledgeAgent 或普通 SupportAgent |
| A-022 | WHEN 危机处理完成 | THEN 当前经前状态了解流程 SHALL 暂停，而不是生成状态小结 |

### 4.4 自然追问

| ID | SHALL 需求 |
|----|------------|
| R-030 | 系统 SHALL 每轮最多插入一个自然追问。 |
| R-031 | 追问 SHALL 覆盖情绪核心、身体感受、功能影响三类信息，但 SHALL NOT 以问卷或量表方式呈现。 |
| R-032 | 追问 prompt SHALL 从 `backend/app/prompts/assessment_probe_prompt.txt` 加载。 |

| 场景 | WHEN | THEN |
|------|------|------|
| A-030 | WHEN 用户处于经前期并表达低落或烦躁 | THEN 情绪宝宝可先安抚，再自然追问一个相关维度 |
| A-031 | WHEN 本轮已经追问过一个维度 | THEN 系统 SHALL NOT 在同一回复中继续追加第二个评估问题 |
| A-032 | WHEN 用户回答已覆盖情绪核心但未覆盖身体感受 | THEN 下一次合适追问可优先选择身体感受 |

### 4.5 结构化入库

| ID | SHALL 需求 |
|----|------------|
| R-040 | 系统 SHALL 从用户回答中提取情绪核心、身体感受、功能影响、危机信号和 `confidence`。 |
| R-041 | 结构化提取 SHALL 写入持久化状态画像，不只保存在内存。 |
| R-042 | `evidence_text` SHALL 只保存最小必要证据片段，SHALL NOT 复制整段敏感聊天原文。 |
| R-043 | 结构化提取 prompt SHALL 从 `backend/app/prompts/assessment_extract_prompt.txt` 加载，失败时返回空信号和低置信度。 |

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `irritability` | `int` | `0` | 烦躁/易怒强度，0-3 |
| `anxiety` | `int` | `0` | 焦虑/紧张强度，0-3 |
| `tearful` | `int` | `0` | 想哭/敏感强度，0-3 |
| `depressed` | `int` | `0` | 低落/无力强度，0-3 |
| `fatigue` | `int` | `0` | 疲惫/乏力强度，0-3 |
| `sleep_change` | `int` | `0` | 失眠/嗜睡等睡眠变化，0-3 |
| `craving` | `int` | `0` | 食欲变化，0-3 |
| `pain_or_bloating` | `int` | `0` | 胀痛、腹痛、头痛等身体不适，0-3 |
| `study_work` | `int` | `0` | 学习/工作影响，0-3 |
| `social` | `int` | `0` | 社交影响，0-3 |
| `family` | `int` | `0` | 家庭/亲密关系影响，0-3 |
| `self_care` | `int` | `0` | 自我照顾影响，0-3 |
| `self_harm` | `bool` | `false` | 自残信号 |
| `suicidal_ideation` | `bool` | `false` | 自杀/轻生信号 |
| `confidence` | `float` | `0.0` | 提取置信度，0-1 |

| 场景 | WHEN | THEN |
|------|------|------|
| A-040 | WHEN 用户回答“那几天很烦躁，还睡不好，学习也拖着不想动” | THEN 系统 SHALL 提取情绪、身体和功能影响信号 |
| A-041 | WHEN 提取结果置信度低 | THEN 系统 SHALL 保存低置信度，不生成强结论 |
| A-042 | WHEN 用户回答包含危机信号 | THEN 系统 SHALL 标记危机信号并进入安全通道 |

### 4.6 API / WebSocket / chatStore 契约

| ID | SHALL 需求 |
|----|------------|
| R-050 | `/api/v1/chat/message` SHALL 在现有返回中新增 `assessment_state`，且 SHALL 保持旧字段兼容。 |
| R-051 | `WS /api/v1/chat/ws/{user_id}` 的 assistant 消息 SHALL 新增 `assessment_state`，结构与 REST 保持一致。 |
| R-052 | `chatStore` SHALL 新增 `assessmentState` 和 `assessmentSummary`，并提供设置与清除方法。 |

| 字段/方法 | 类型 | 默认值 | 说明 |
|-----------|------|--------|------|
| `assessment_state` | `object?` | `null` | 隐藏评估状态摘要 |
| `assessment_state.status` | `str` | `idle` | 状态机状态 |
| `assessment_state.current_dimension` | `str?` | `null` | 当前维度，默认不展示 |
| `assessment_state.summary_available` | `bool` | `false` | 是否已有参考小结 |
| `assessment_state.user_visible_label` | `str?` | `null` | 只允许“状态小结”等非筛查文案 |
| `chatStore.assessmentState` | `Ref<object|null>` | `null` | 保存服务端状态摘要 |
| `chatStore.assessmentSummary` | `Ref<object|null>` | `null` | 保存聊天式参考小结 |
| `chatStore.setAssessmentState(state)` | `function` | - | 更新隐藏状态 |
| `chatStore.clearAssessmentState()` | `function` | - | 退出登录或清空聊天时重置 |

| 场景 | WHEN | THEN |
|------|------|------|
| A-050 | WHEN 旧前端收到新增 `assessment_state` | THEN 旧字段仍可用，未处理新字段也不应报错 |
| A-051 | WHEN WebSocket assistant 消息返回 | THEN 消息 SHALL 可携带 `assessment_state` |
| A-052 | WHEN 用户退出登录或清空聊天 | THEN `chatStore` SHALL 清除隐藏评估状态 |

### 4.7 EmotionEngine 接入

| ID | SHALL 需求 |
|----|------------|
| R-060 | `EmotionEngine._get_negative_emotion_ratio()` SHALL 查询 `Conversation.sentiment_score`，不再返回固定 `0.0`。 |
| R-061 | `EmotionEngine` SHALL 聚合状态画像中的情绪、身体、功能影响信号。 |
| R-062 | 危机信号 SHALL NOT 作为普通 PMS 风险分数处理，必须走安全通道。 |
| R-063 | 算法权重变更 SHALL 同步更新技术文档。 |

| 信号 | 初始最高贡献 | 说明 |
|------|--------------|------|
| 对话负向比例 | `0.15` | 避免文本误判压过生理/周期数据 |
| 经前状态信号 | `0.20` | 至少覆盖 2 类维度后参与 |

| 场景 | WHEN | THEN |
|------|------|------|
| A-060 | WHEN 最近 7 天存在多条负向用户对话 | THEN `negative_ratio` SHALL 大于 0，并影响 `pms_risk/mood_level` |
| A-061 | WHEN 用户状态画像覆盖情绪和功能影响 | THEN `EmotionEngine` SHALL 将画像信号纳入分析 |
| A-062 | WHEN 只有危机信号 | THEN 系统 SHALL 进入安全通道，而不是只提高 PMS 风险 |

### 4.8 安全、隐私与前端渲染

| ID | SHALL 需求 |
|----|------------|
| R-070 | 用户聊天内容和状态小结 SHALL 使用纯文本渲染，前端 SHALL NOT 对用户内容使用 `v-html`。 |
| R-071 | 数据库查询 SHALL 参数化，并限制 `user_id` 范围。 |
| R-072 | 日志 SHALL 避免输出完整敏感聊天内容。 |
| R-073 | 真实部署前 SHALL 接入 JWT 或等价用户身份上下文，替换默认 `user_id=1`。 |

| 场景 | WHEN | THEN |
|------|------|------|
| A-070 | WHEN 用户发送 HTML 或脚本片段 | THEN 前端 SHALL 按纯文本显示，不执行脚本 |
| A-071 | WHEN 查询状态画像或对话历史 | THEN 后端 SHALL 按当前用户范围过滤 |
| A-072 | WHEN LLM 结构化提取超时 | THEN 主聊天回复 SHALL 不被阻塞，并使用 fallback |

---

## 5. REMOVED + Reason/Migration

| REMOVED / Deprecated | Reason | Migration |
|----------------------|--------|-----------|
| 将 `/interview/start` 作为 P1 主入口 | 显性入口会把核心体验变成访谈/问卷，不符合非显性聊天式评估 | 保留 `/interview/*` 作为兼容或调试入口；主链路迁移到 `/api/v1/chat` |
| 在 `chatStore` 中把 `isInterviewMode` / `interviewPhase` 作为主评估状态 | 前端显性 interview 语义会泄露“筛查流程”心智 | 新增 `assessmentState`；旧字段仅保留兼容，不用于 P1 主流程 |
| 把状态小结包装成医学报告或独立筛查结果页 | 容易造成诊断误解 | 在聊天中生成“仅供参考”的自然小结；不使用诊断语气 |
| 在 `EmotionEngine` 中保留固定 `negative_ratio = 0.0` | 对话信号无法进入分析，结果不可信 | 改为从 `Conversation.sentiment_score` 聚合真实负向比例 |
| 在 Agent 类中硬编码长 prompt | 不符合项目 prompt 文件化规范，难维护 | 新增 `assessment_probe_prompt.txt` 与 `assessment_extract_prompt.txt`，通过 prompt loader 加载 |
| 把危机信号纳入普通 PMS 风险评分后继续聊天评估 | 心理安全风险高，会延误干预 | 危机信号立即进入 `crisis_handoff` 和 InterventionAgent/安全兜底 |

---

## 6. Completion Definition

本 SPEC 只有在以下条件全部满足时才算完成：

| 完成项 | 判定标准 |
|--------|----------|
| 主入口完成 | `/api/v1/chat/message` 和 WebSocket 均可返回 `assessment_state` |
| 非显性完成 | 用户可见 UI 不出现筛查、诊断、量表测评等显性文案 |
| 状态机完成 | 状态可持久化，服务重启后不丢失 |
| 入库完成 | 用户回答可生成结构化观察记录 |
| 安全完成 | 危机样例全部进入 InterventionAgent 或安全兜底 |
| EmotionEngine 完成 | 对话负向比例和经前状态信号真实影响分析结果 |
| 文档完成 | 情绪融合权重和状态画像字段同步更新技术文档 |
| 测试完成 | 状态机、危机优先、REST、WebSocket、结构化提取、EmotionEngine、XSS 文案测试通过 |
