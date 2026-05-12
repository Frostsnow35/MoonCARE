# MoonCARE 聊天 Agent 经期语义承接修复 SPEC

> 变更日期：2026-05-13  
> 影响范围：`backend/app/prompts/support_prompt.txt`、`backend/app/agents/perception_agent.py`、`backend/app/services/agent_service.py`、`backend/app/agents/llm_service.py`、`backend/tests/test_p0_safety_and_prompts.py`  
> 状态：已完成后端修复；需要在真实对话样本中继续验证语气自然度

## 为什么做（Why）

MoonCARE 的聊天入口服务于女性经前与经期情绪健康。根据当前代码，SupportAgent 已能做普通情绪陪伴，但对“难过”“想哭”“不适”“肚子痛”等表达的身体语境理解不足，容易把经前、经期、痛经或激素波动相关的复合型体验压扁成普通情绪波动。

当前回复还存在两个体验风险：一是回答节奏可能从“难过”直接跳到深呼吸或专业求助，缺少承接和具体化；二是 LLM 输出可能残留 `_chatting_`、角色标签或格式化前缀，暴露模型拼接感。修复目标是让普通陪伴更像“先懂她正在经历什么”，同时保持危机干预最高优先级。

## 要改变什么（What Changes / BREAKING）

| 编号 | 变更 | 类型 | 状态 |
| --- | --- | --- | --- |
| C-001 | Support prompt 增加经前/经期身体与情绪复合承接规则 | 行为优化 | 已完成 |
| C-002 | PerceptionAgent 输出低风险经期语义线索，用于下游 prompt 和建议 | 兼容新增 | 已完成 |
| C-003 | Action 建议从“默认深呼吸”调整为按用户表达匹配具象支持 | 行为优化 | 已完成 |
| C-004 | LLM 输出清洗移除 `_chatting_`、角色标签、Markdown 前缀和 think 标签残留 | 质量修复 | 已完成 |
| C-005 | 补充 P0 测试覆盖普通难过、经期痛感、危机优先和输出清洗 | 测试补强 | 已完成 |

BREAKING：无对外 API breaking change。`/api/v1/chat/message` 和 WebSocket 请求体不新增必填字段。新增 state 字段仅供内部调试和后续前端可选使用。

## 会影响什么（Impact）

| 影响面 | 正向影响 | 风险 | 规避 |
| --- | --- | --- | --- |
| 用户心理安全 | 普通难过先被承接，再获得支持 | 过度归因为经期/PMS | 使用“可能、是不是、如果正好在经前/经期”表达，不诊断 |
| 危机干预 | 自杀/自残仍直接走 Intervention | 放松普通陪伴后漏掉危机 | 危机关键词检测和 high/crisis 路由不降级 |
| LLM 质量 | 减少标签残留和拼接感 | 清洗误删用户需要的内容 | 仅清洗常见模型元标签和行首角色前缀 |
| 前端体验 | 行动按钮更贴合身体不适 | 现有 UI 对新 action 不识别 | 暂不新增前端必需路由，无法跳转的建议保留 `route: None` |
| 性能 | 规则层为本地字符串匹配，成本低 | prompt 变长影响延迟 | 控制 prompt 长度，保留 90-140 字回复约束 |

## 具体怎么做、怎样算完成（SHALL + WHEN/THEN）

### SHALL 需求

| 编号 | 需求 |
| --- | --- |
| R-001 | SupportAgent SHALL 在普通低/中风险情绪表达中先承接感受，再确认身体状态，再给一个具象支持。 |
| R-002 | SupportAgent SHALL 把“难过、想哭、委屈、烦躁、无助、身体难受、肚子痛、痛经、例假、姨妈”等作为可能的经前/经期复合线索，而不是直接归因为普通情绪波动。 |
| R-003 | SupportAgent SHALL 使用开放式措辞，不得说“你就是 PMS/PMDD”或作医疗诊断。 |
| R-004 | AgentService SHALL 在非危机普通难过场景避免默认推“专业帮助”或“深呼吸急救”。 |
| R-005 | AgentService SHALL 在身体痛感场景优先提供热敷、温水、休息、蜷起来缓一缓等低压力具象支持。 |
| R-006 | Router SHALL 继续在 `risk_level in {"high", "crisis"}` 时优先 InterventionAgent，不受经期语义线索或 `agent_mode` 覆盖。 |
| R-007 | LLMService SHALL 清理 `_chatting_`、`<think>`、`assistant:`、`情绪宝宝：`、序号/项目符号等常见生成残留。 |
| R-008 | 测试 SHALL 证明普通“我很难过”不会被当作危机处理；“例假肚子绞痛想哭”会产生身体化支持；危机表达仍进入 Intervention。 |

### WHEN/THEN 验收场景

| 编号 | WHEN | THEN |
| --- | --- | --- |
| A-001 | WHEN 用户说“我今天很难过，莫名其妙想哭” | THEN 回复先命名和承接难过/想哭，并轻问是否和经前或经期身体状态有关 |
| A-002 | WHEN 用户说“例假来了，肚子绞痛，特别无助” | THEN 回复承认疼痛带来的无助，优先给热水袋/温水/休息等具象支持 |
| A-003 | WHEN 用户只是表达“难过” | THEN 不直接要求专业求助，不立刻进入危机干预文案 |
| A-004 | WHEN 用户说“我想自残” | THEN Router 忽略普通陪伴规则，返回 Intervention 或安全兜底 |
| A-005 | WHEN LLM 返回 `_chatting_ 情绪宝宝：<think>x</think>我在这里` | THEN 最终用户可见文本不包含 `_chatting_`、角色标签或 think 内容 |

## 如何处理废弃或迁移（REMOVED + Reason/Migration）

| REMOVED | Reason | Migration |
| --- | --- | --- |
| 普通场景默认深呼吸急救感 | 容易让刚表达难过的用户感到被流程化处理 | 改为按焦虑/惊慌/高风险才优先呼吸；普通低落给日记或身体照护 |
| Support prompt 中“只轻提经前背景”的弱规则 | 无法支撑经期语义承接 | 迁移为“先承接、再身体确认、再具象支持”的顺序规则 |
| 仅清理 `<think>` 的输出清洗 | 无法覆盖 `_chatting_` 和角色标签残留 | 扩展为常见元标签和行首标签清洗 |

## 测试建议

- 后端单元测试：`python -m unittest backend.tests.test_p0_safety_and_prompts -v`
- 相关回归测试：`python -m unittest backend.tests.test_p0_safety_and_prompts backend.tests.test_p1_assessment_loop -v`
- 编译检查：`python -m compileall backend`
