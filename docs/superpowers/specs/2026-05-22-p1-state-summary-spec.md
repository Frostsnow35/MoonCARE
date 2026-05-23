# MoonCARE P1 状态小结闭环 SPEC

> 变更日期：2026-05-22  
> 影响范围：`backend/app/services/`、`backend/app/api/v1/`、`frontend/src/stores/chat.js`、`frontend/src/views/Chat.vue`、`frontend/src/views/Home.vue`、`docs/superpowers/plans/2026-05-22-p1-state-summary-plan.md`  
> 状态：计划中，等待用户确认后执行  

## 为什么做（Why）

根据当前代码，MoonCARE 已经具备登录、聊天、隐藏式经前状态了解、周期记录、日记和情绪分析基础能力；上一轮已补上“周期 + 日记 + 聊天”的后端上下文注入。但 P1 闭环还缺一个用户可感知的结果：用户聊过、记过周期和日记之后，产品需要能给出一份温柔、可解释、仅供参考的状态小结，而不是只把数据藏在 Agent prompt 里。

这个小结不应是正式筛查、诊断或报告，也不应把女性情绪简单病理化。它的目标是帮助用户看见“最近哪些体验反复出现、可能和周期有什么温和关联、还缺什么数据、可以怎么轻量照顾自己”，并继续回到聊天陪伴中。

## 要改变什么（What Changes / BREAKING）

| 编号 | 变更 | 类型 | 状态 |
| --- | --- | --- | --- |
| C-001 | 新增状态小结服务，汇总当前用户周期、日记、聊天隐藏 assessment、情绪分析信号 | 新功能 | 计划中 |
| C-002 | 新增只读状态小结 API，使用 JWT 当前用户，不接受前端 `user_id` | 新接口 | 计划中 |
| C-003 | 聊天页支持查看“状态小结”，展示来源、置信度、缺失数据和仅供参考提示 | 前端体验 | 计划中 |
| C-004 | 首页“经前状态聊聊”入口迁移到 `/chat`，不再默认启动旧显性 `/interview/*` 流程 | 行为迁移 | 计划中 |
| C-005 | Emotion 分析结果增加可解释字段，前端不只展示数字风险 | 兼容增强 | 计划中 |
| C-006 | 保留旧 `/interview/*` 兼容入口，但不作为用户主路径 | 兼容保留 | 计划中 |

BREAKING：无对外 breaking change。新增 API 为只读接口；现有 `/api/v1/chat/message`、`/api/v1/emotion/predict`、`/api/v1/interview/*` 保持兼容。若扩展 `EmotionPredictResponse`，新增字段为可选或默认字段，避免破坏现有前端调用。

## 会影响什么（Impact）

| 影响面 | 正向影响 | 风险 | 规避 |
| --- | --- | --- | --- |
| 用户体验 | 用户能看到聊天、日记和周期记录产生了可理解结果 | 小结像医学诊断或筛查报告 | 固定文案使用“状态小结”“仅供参考”“自我观察”，不使用诊断结论 |
| 心理安全 | 小结可提醒用户照顾自己和寻求支持 | 危机信号被普通小结稀释 | 危机信号最高优先级，命中时返回安全提示而不是普通小结 |
| 隐私 | 只展示摘要和来源，不暴露完整日记/聊天原文 | 泄露敏感原文或跨用户数据 | 所有查询按 JWT 用户过滤；只使用关键词、计数、时间和短摘要 |
| 性能 | 首版使用规则汇总，响应稳定 | 复杂 LLM 总结导致超时 | 首版不依赖 LLM 生成正文；后续可加异步 LLM 优化 |
| 产品叙事 | PMS 维度自然嵌入聊天闭环 | 重新变成显性测评流程 | 首页入口直达聊天；旧 interview 仅保留兼容/调试 |

## 具体怎么做、怎样算完成（SHALL + WHEN/THEN）

### SHALL 需求

| 编号 | 需求 |
| --- | --- |
| R-001 | 状态小结服务 SHALL 只读取当前登录用户的 `MenstrualRecord`、`MoodDiary`、`Conversation`、`AssessmentSession`、`AssessmentObservation` 和 `EmotionEngine` 结果。 |
| R-002 | 状态小结服务 SHALL 输出结构化结果：`summary_available`、`title`、`level`、`confidence`、`summary_text`、`observations`、`sources`、`missing_data`、`suggestions`、`disclaimer`、`generated_at`。 |
| R-003 | 状态小结 SHALL 只在有足够周期、日记、聊天或 assessment 信号时给出；数据不足时返回明确空状态和下一步建议。 |
| R-004 | 状态小结 SHALL 使用非诊断语言，不出现“你得了 PMS/PMDD”“正式筛查结果”“诊断报告”等表达。 |
| R-005 | 若最近聊天或 assessment 命中自伤、自杀、轻生等危机信号，状态小结 SHALL 进入安全边界文案，优先建议联系可信任的人、专业支持或当地紧急服务。 |
| R-006 | API SHALL 放在 `/api/v1/` 下，并使用 `get_current_user_id`，不得信任 query/body 中的 `user_id`。 |
| R-007 | 前端 SHALL 通过 `chatStore` 保存 `stateSummary`、`summaryLoading`、`summaryError`，页面不散落新 axios 实例。 |
| R-008 | 聊天页 SHALL 提供“状态小结”查看入口；展示来源与缺失数据，避免把小结做成医学报告。 |
| R-009 | 首页“经前状态聊聊” SHALL 进入 `/chat`，并以自然聊天方式触发隐藏式 assessment，不再直接启动旧显性访谈。 |
| R-010 | 测试 SHALL 覆盖用户隔离、数据不足、普通小结、危机优先、旧接口兼容、前端构建。 |

### WHEN/THEN 验收场景

| 编号 | WHEN | THEN |
| --- | --- | --- |
| A-001 | WHEN 用户有最近周期记录和日记关键词“小腹痛、烦躁” | THEN 小结提示“最近记录里身体不适和烦躁较明显”，并标注仅供参考。 |
| A-002 | WHEN 用户没有周期、日记或 assessment 数据 | THEN API 返回 `summary_available=false`，前端显示空状态和“可以先记录一次日记或继续聊聊”。 |
| A-003 | WHEN 用户 A 请求状态小结，但用户 B 有丰富日记和周期数据 | THEN 用户 A 的小结不得出现用户 B 的任何内容。 |
| A-004 | WHEN 最近聊天出现“我想自残” | THEN 小结不生成普通 PMS 状态判断，优先返回安全提示和求助建议。 |
| A-005 | WHEN 用户点击首页“经前状态聊聊” | THEN 进入 `/chat`，不出现“筛查/量表/诊断/测评进度”等显性表述。 |
| A-006 | WHEN 前端请求小结接口失败 | THEN 聊天页展示柔和错误态，不清空已有聊天消息。 |

## 如何处理废弃或迁移（REMOVED + Reason/Migration）

| REMOVED | Reason | Migration |
| --- | --- | --- |
| 首页直接启动旧 `/interview/start` 作为主路径 | 旧流程偏显性访谈，且内存 session 重启丢失，不符合 P1 隐藏式自然聊天主线 | 首页入口改为跳转 `/chat`，由聊天中的 assessment 逐步了解状态 |
| 把 `ReportService.build_screening_report()` 作为用户主小结 | 文案仍带筛查/报告感，且绑定旧 PSST summary | 新增状态小结服务；旧 `ReportService` 暂保留给 `/interview/*` 兼容 |
| 只展示 PMS 风险数字 | 用户难以理解来源和可信度 | 增加 `sources`、`missing_data`、`confidence`、`disclaimer` 和自然语言小结 |
