# Chat Agent Full Optimization Next Plan (Streaming/Cache/Quality/Context)

> 变更日期：2026-05-27  
> 对齐 SPEC：`docs/superpowers/specs/2026-05-26-chat-agent-full-optimization-spec.md`  
> 范围：仅覆盖 **流式输出、缓存加速、回复质量、上下文机制**（不在本计划内：M-001..M-005 分层记忆体系）  
> 当前策略：先把“用户主链路可用 + 可观测 + 可回归”做扎实，再做更高阶记忆与模板库扩展。  

## 0. Why (目的与边界)

MoonCARE 聊天主链路已具备 REST/SSE/WS、危机优先、安全兜底、基础上下文压缩与本地语义缓存能力，但 SPEC 里仍标注“待实现”的条目需要补齐为：

1) **可验收**：对外契约一致、关键字段可追踪、前端体验稳定。  
2) **可配置**：阈值/窗口/开关通过 settings + env 生效，且配置错误有安全退化。  
3) **可回归**：有针对性回归测试，覆盖危机优先、缓存命中、上下文压缩与首包/超时行为。  

安全边界：任何优化不得绕过 `PerceptionAgent -> Router -> Agent` 的危机优先链路；健康相关回复保持“仅供参考/不诊断”。

## 1. What Changes (按 SPEC 编号对齐)

本计划覆盖的 SPEC 条目：

- **SSE 流式输出**：S-001/S-002/S-003 + R-S-001..R-S-004  
- **缓存加速**：C-001/C-002/C-003/C-004 + R-C-001..R-C-004  
- **回复质量**：Q-001/Q-002/Q-003/Q-004 + R-Q-001..R-Q-004  
- **上下文机制**：U-001/U-002/U-003 + R-U-001..R-U-003  

不在本计划内（单独立项）：M-001..M-005（分层记忆、事件卡片、遗忘机制）。

## 2. Impact (影响与风险)

主要风险与规避：

- 缓存误命中导致“跑题/不够共情”：对质量敏感 turn 禁用缓存；阈值可配置；cache hit 仍经过质量修复。  
- SSE 在反向代理下被缓冲：服务端 `X-Accel-Buffering: no` + `Cache-Control: no-transform`，并给出 Nginx/Caddy 配置提示。  
- 上下文压缩丢关键事实：把“关键信息置顶”做成可验证输出（system 摘要段），并加测试。  
- 首包慢/超时体验差：fast-ack 只在非危机、首轮倾诉触发；失败时用 soft fallback，不暴露技术错误。  

## 3. Plan (具体怎么做)

### Phase A: SSE 端到端“可观测”与“稳定首包”

目标：

- R-S-001/R-S-003：危机预检通过后，首 token 产生即可 flush；危机则不进入普通流式。  
- R-S-004：chunk 节奏稳定（建议 50-100ms），并且缓存命中也走“逐段输出”。  

工作项：

1) 后端 `/api/v1/chat/stream` 事件格式固化：`start`、`token`、`end` 三种，`end` 必含 `reply_status/elapsed_ms/cache_hit/cache_similarity/assessment_state/memory_state`。  
2) 前端 SSE 解析继续集中在 `frontend/src/api/index.js` 的 `chatAPI.sendMessageStream()`，`Chat.vue` 仅消费事件。  
3) 增加“首包延迟”可观测字段：保持现有 `first_token_latency_ms`，并确保前端可读取并在 message metadata 中保存（不做 UI 展示也要可回放）。  

验收（WHEN/THEN）：

- WHEN 普通低风险消息 -> THEN 先 `start`，很快出现 `token`；最终 `end` 字段齐全。  
- WHEN 危机文本 -> THEN 不走普通流式内容，直接输出安全兜底。  

测试建议：

- 后端：新增/强化 `backend/tests/test_chat_agent_quality.py` 的 SSE 合同测试，验证 end 字段齐全且危机优先。  
- 前端：保留 build 验证；必要时做最小字符串断言（不引入新测试框架）。  

### Phase B: 缓存预热与阈值调优闭环

目标：

- C-003：提供“可控的预热机制”，不引入外部依赖，默认关闭或低风险。  
- C-002：相似度阈值可配置，结合真实日志样本做二次调优。  

工作项：

1) 缓存预热策略（本地语义缓存）：服务启动后只预热极少量“安全、泛化”的短回复模板（不含危机、医疗诊断倾向、强结论）。  
2) 增加 `SEMANTIC_CACHE_WARMUP_ENABLED`（默认 false）与 `SEMANTIC_CACHE_WARMUP_ITEMS`（默认 0/少量）配置。  
3) 缓存统计：暴露 `hits/misses/evictions/size`（已有基础）并在 `/metrics` 或 `/healthz` 的 debug 输出里可见（仅 debug）。  

验收：

- WHEN 开启预热 -> THEN 启动时 cache size 增加但不影响危机链路；命中时 `reply_status=cache_hit` 且 `elapsed_ms` 明显降低。  

测试建议：

- `backend/tests/test_semantic_cache.py`：预热开关、预热条目不含危机关键词、LRU/TTL 不被破坏。  

### Phase C: 回复质量“模板库化”与结构化输出

目标：

- Q-001/Q-003/Q-004：Support 回复更稳定地呈现“共情 + 理解 + 轻量建议/引导 + 1 个温柔开放式问题”，且不说教。  

工作项：

1) “共情响应模板库”落地为 prompt 资产：新增 `backend/app/prompts/empathy_templates.json` 或 `empathy_templates.txt`，由 `ResponseQualityGuard`/`AgentService` 加载（避免硬编码长文案）。  
2) 结构化输出策略：不要求模型输出 JSON；在服务端用规则确保段落/结尾开放式问题存在（仅低风险 support）。  
3) action_suggestions 继续以站内功能为主：`/diary`、`/music`、`/breathing`、`/cycle`，并在高风险/知识模式禁用。  

验收：

- WHEN 低/中风险倾诉 -> THEN 回复末尾包含 1 个开放式问题；整体不出现诊断语气。  
- WHEN 用户明确求“下一步怎么做” -> THEN 给 2-3 个具体下一步，而不是只继续安抚。  

测试建议：

- `backend/tests/test_chat_agent_quality.py`：新增断言“末尾开放式问题存在”“action request 给出具体步骤”。  

### Phase D: 上下文机制“置顶关键信息”与窗口一致性

目标：

- U-001/U-002/U-003：近期 20 轮完整 + 更早摘要；总不超过 30；关键信息置顶。  

工作项：

1) 关键点抽取来源：优先从 `conversation_memory.memory_state`、`ChatMemory`（已有）和最近 user/assistant turns 规则抽取，不依赖 LLM。  
2) 在 compaction 输出里统一注入两段 system：`【关键信息】`、`【历史摘要】`，并确保在最终 context 最前。  

验收：

- WHEN 对话超过 20 轮 -> THEN 最近 20 轮保留，早期变摘要，且置顶关键信息存在。  

测试建议：

- `backend/tests/test_chat_context_mechanism.py`：窗口 20/30 与置顶段落存在性。  

## 4. Next Step (下一步先做什么)

优先级建议（从“直接提升主链路可用性”出发）：

1) **Phase B 缓存预热机制**：最小侵入、可配置、可验证，并把 SPEC 的 C-003 真正闭环。  
2) **Phase C 共情模板库化**：把“质量提升”从代码逻辑里抽离成 prompt 资产，便于迭代与审校。  

## 5. Verification (执行时的固定验证命令)

- 后端：`python -m unittest backend.tests.test_p0_safety_and_prompts backend.tests.test_chat_agent_quality backend.tests.test_chat_context_mechanism backend.tests.test_semantic_cache -v`  
- 前端：`cd frontend; npm run build`  

> 注：若 `compileall` 在本机因权限无法写入 `.pyc`，用 AST 解析替代作为语法门槛验证（不代表运行时行为验证）。

