# MoonCARE Agent 工作说明

> 变更日期：2026-05-20  
> 影响范围：后续所有 AI agent、开发、文档和测试任务  
> 当前状态：已完成项目级上下文整理；需要在后续功能变更时同步更新  

## 1. 项目定位

MoonCARE（她语）是一个已经存在的半成品项目，不是从零重写项目。后续工作默认是在现有代码、文档和命名体系上继续开发与优化。

项目目标是成为一个可用、智能的女性经前情绪陪伴与健康护航产品。可见产品叙事应优先围绕：

| 方向 | 说明 |
| --- | --- |
| 月经周期与经前情绪支持 | 帮助用户理解周期阶段、情绪波动和身体感受之间的关系 |
| AI 情绪陪伴 | 通过自然对话承接用户感受，并给出轻量、低压力的照护建议 |
| 健康指导 | 提供经前、经期、痛经、睡眠、饮食、运动等知识解释，但不替代医生 |
| 实用成熟度 | 完善登录、聊天、周期、日记、音乐、呼吸、数据持久化和部署体验 |
| 安全边界 | 危机干预是后台安全底线，不是主要营销叙事；但一旦命中必须最高优先级处理 |

重要边界：PMS 相关能力默认不是正式筛查、测试、诊断或显性问卷。新增体验应使用“经前状态了解”“状态小结”“仅供参考”等表达，把 PMS/PSST 维度嵌入登录后或聊天中的自然对话。

## 2. 当前技术栈

| 层级 | 技术 | 当前说明 |
| --- | --- | --- |
| 后端 | FastAPI、SQLAlchemy、SQLite/PostgreSQL 兼容 URL | 当前主要使用同步 SQLAlchemy Session；FastAPI 路由为 async handler |
| 前端 | Vue 3、Composition API、Pinia、Axios、Vite | 聊天状态集中在 `frontend/src/stores/chat.js` |
| AI | 多 Agent 路由系统、OpenAI-compatible LLM 接口 | 支持 `nvidia`、`openai`、`vllm`、`accelerated`、`zai` 等 provider 配置 |
| 数据 | SQLite 默认用于本地；服务器部署优先使用 PostgreSQL 容器 | 迁移目录在 `backend/migrations/`，`docker-compose.yml` 已包含 Postgres 服务 |
| 记忆 | ProductMemoryService、ChatMemory、可选 Awareness Local | Awareness 在 `localhost:37800`，失败时应回退 |
| 部署 | 本地 uvicorn + Vite；生产/演示主方向为 Docker + 服务器 | 前端最终部署方式暂未定；Railway/Vercel 配置只能作为历史参考，不能作为默认方案 |

### 2.1 部署工程思路

当前部署方向采用 Docker + 服务器。后续 agent 在设计部署、运维、环境变量、接口路径和构建流程时，默认以服务器上的容器化部署为主，不要默认选择 Railway、Vercel 或其他托管平台。

推荐工程形态：

```text
Server
  -> Reverse Proxy / HTTPS (Nginx, Caddy, Traefik, or cloud gateway)
  -> Docker Compose network
      -> mooncare-app: FastAPI + gunicorn + uvicorn worker
      -> mooncare-postgres: PostgreSQL persistent volume
      -> optional redis: semantic cache
      -> optional awareness: only after multi-user isolation review
```

现有容器化基础：

| 文件 | 当前作用 | 注意点 |
| --- | --- | --- |
| `Dockerfile` | 多阶段构建：先构建前端 `dist`，再复制后端并用 gunicorn/uvicorn 运行 | 这是一个可用的一体化镜像雏形，但前端最终是否内嵌同镜像仍待确认 |
| `docker-compose.yml` | 编排 `app` 和 `postgres`，使用 `postgres_data` volume | 生产前必须替换默认密码、密钥和 healthcheck |
| `entrypoint.sh` | 等待 PostgreSQL，并执行 Alembic 迁移 | 需要确保镜像内具备 `pg_isready` 所需客户端工具 |
| `DEPLOY_RAILWAY.md` / `Procfile` | 历史或备选部署文档 | 不作为当前默认部署路线 |

前端部署仍未定。后续设计不得假设最终一定走 Vercel、Nginx 静态托管或后端一体化镜像；应在方案中保留以下分支：

| 方案 | 适用性 | 待确认点 |
| --- | --- | --- |
| 前端构建进后端镜像 | 当前 `Dockerfile` 已支持，部署最简单 | FastAPI 静态挂载路径、缓存策略、前端路由 fallback |
| 前端独立容器 + Nginx/Caddy | 更清晰，便于独立扩缩容 | API/WS 反代、CORS、HTTPS、静态缓存 |
| 前端独立托管平台 | 可能适合快速发布 | 用户尚未决定；不要作为默认实现 |

服务器部署必须同步考虑：

| 事项 | 要求 |
| --- | --- |
| 反向代理 | 统一处理 HTTPS、域名、压缩、静态资源缓存、WebSocket upgrade |
| 环境变量 | `SECRET_KEY`、数据库密码、LLM API Key、provider 配置必须通过服务器环境注入 |
| 数据持久化 | PostgreSQL 使用 volume；备份和恢复流程需要单独记录 |
| 健康检查 | Compose、反代和监控必须打真实存在的健康接口 |
| 日志 | 容器日志不得输出完整敏感聊天、token、密钥或健康隐私 |
| 数据库迁移 | 容器启动前后要有可重复、可回滚的迁移策略 |
| AI 依赖 | LLM 端点、超时、fallback、代理网络连通性需要部署前验证 |
| 安全 | 生产 CORS、JWT、Cookie/Authorization、限流和敏感接口保护必须重新审核 |

## 3. 目录导航

| 路径 | 用途 |
| --- | --- |
| `backend/app/main.py` | FastAPI 应用入口，注册 `/api/v1` 路由和启动服务 |
| `backend/app/api/v1/` | REST/WebSocket API 路由，新增后端接口必须融入这里 |
| `backend/app/agents/` | Agent 实现：`PerceptionAgent`、`Router`、`SupportAgent`、`KnowledgeAgent`、`InterventionAgent`、`LLMService` |
| `backend/app/services/` | 业务编排服务：聊天、评估、情绪引擎、周期预测、记忆、缓存、质量修复 |
| `backend/app/models/` | SQLAlchemy 模型 |
| `backend/app/schemas/` | Pydantic schema |
| `backend/app/prompts/` | Agent prompt 文件。禁止把长 prompt 硬编码进 Python 类 |
| `backend/app/data/` | 知识库、嵌入数据、访谈流等静态数据 |
| `backend/tests/` | 后端回归测试 |
| `Dockerfile` | 当前一体化容器镜像雏形，包含前端 build 和后端运行 |
| `docker-compose.yml` | 当前 Docker + 服务器部署编排雏形，包含 app 和 Postgres |
| `entrypoint.sh` | 容器启动脚本，负责等待数据库和执行迁移 |
| `frontend/src/views/` | Vue 页面：Chat、Home、Cycle、Diary、Breathing、Music、Profile 等 |
| `frontend/src/stores/` | Pinia store，聊天/访谈状态必须优先用 `chatStore` |
| `frontend/src/api/index.js` | Axios API 封装和统一错误处理 |
| `docs/` | 技术文档、优化方案、SPEC 和计划 |
| `docs/superpowers/specs/` | 已确认或阶段性 SPEC |
| `docs/superpowers/plans/` | 对应执行计划 |
| `MoonCARE/` | 当前为未跟踪的嵌套目录，除非用户明确指定，否则不要默认把它当主工程 |

## 4. 后端架构

后端主链路：

```text
FastAPI /api/v1
  -> api/v1/chat.py
  -> NLPService + ProductMemoryService + AssessmentOrchestrator
  -> AgentService
  -> PerceptionAgent
  -> Router
  -> InterventionAgent | KnowledgeAgent | SupportAgent
  -> LLMService / fallback
  -> Conversation + ChatMemory + AssessmentSession/Observation
```

新增后端能力必须遵守：

| 要求 | 说明 |
| --- | --- |
| 路由前缀 | 新 API 放在 `/api/v1/` 下，复用现有 router 风格 |
| 安全感知 | 不可绕过 `PerceptionAgent`、`contains_crisis_signal()`、`Router` 的危机优先链路 |
| 返回格式 | 新接口尽量使用 `{"code": 200, "data": ..., "message": "..."}`；旧接口存在直接返回 dict 的历史实现，改动时保持兼容 |
| 鉴权 | 需要用户身份的接口使用 `get_current_user_id` 或 `get_current_user`，不要信任前端传入的 `user_id` |
| 数据库 | 使用 SQLAlchemy 查询，保持参数化；涉及列表查询必须考虑分页 |
| 日志 | 关键路径用 logging；不要记录完整敏感聊天原文、token、密钥或健康隐私 |
| Prompt | Agent prompt 从 `backend/app/prompts/` 通过 `prompt_loader` 加载 |
| LLM 超时 | 不要让慢 LLM 阻塞用户体验；保留 timeout fallback 和危机安全兜底 |

## 5. 前端架构

前端主链路：

```text
Vue views
  -> Pinia stores
  -> frontend/src/api/index.js
  -> FastAPI REST / WebSocket
```

新增前端能力必须遵守：

| 要求 | 说明 |
| --- | --- |
| 组件风格 | 使用 Vue 3 `<script setup>` 和 Composition API |
| 状态管理 | 聊天、访谈、隐藏评估、记忆状态统一通过 `chatStore` 或既有 store 管理 |
| API 调用 | 统一放在 `frontend/src/api/index.js`，不要在页面里散落新 axios 实例 |
| WebSocket | 保持指数退避重连、心跳和错误提示，不要让用户无限等待 |
| 渲染安全 | 用户和模型文本按纯文本渲染，不使用 `v-html` 渲染聊天内容 |
| 文案 | 面向用户避免“诊断”“正式筛查”“量表测评”“测评进度”等显性医学/测试表述 |
| 视觉 | 延续现有移动端、底部导航、粉色主色和简洁卡片体系；不要改成营销落地页 |

## 6. Chat 与 Agent 当前状态

| 能力 | 当前状态 | 代码位置 |
| --- | --- | --- |
| REST 聊天 | 已接入 | `backend/app/api/v1/chat.py` 的 `/chat/message` |
| WebSocket 聊天 | 已接入，含 session、assistant、error 消息 | `backend/app/api/v1/chat.py` 的 `/chat/ws/{user_id}` |
| SSE 流式聊天 | 已接入基础流式链路 | `backend/app/api/v1/chat.py` 的 `/chat/stream` |
| Agent 路由 | 已接入 Support/Knowledge/Intervention | `backend/app/agents/router.py` |
| 危机优先 | 已有关键词检测和 Intervention/fallback | `backend/app/utils/safety.py`、`backend/app/agents/router.py` |
| 经期语义承接 | 已完成后端修复，仍需真实样本验证 | `docs/superpowers/specs/2026-05-13-chat-agent-menstrual-support-spec.md` |
| LLM 超时兜底 | 已完成配置和 fallback，仍需真实 GLM-5.1 压测 | `docs/superpowers/specs/2026-05-13-glm-chat-latency-spec.md` |
| 聊天记忆 | 已接入 ProductMemoryService / ChatMemory | `backend/app/services/product_memory_service.py`、`chat_memory_service.py` |
| 语义缓存 | 已有 Redis 语义缓存配置，生产可选 | `backend/app/services/semantic_cache_service.py` |

## 7. 经前状态了解闭环

核心原则：它是隐藏式、自然聊天式状态了解，不是用户可见的正式筛查或诊断。

当前闭环：

```text
用户自然聊天
  -> AssessmentOrchestrator.prepare_turn()
  -> 触发条件：经前/黄体期/负向情绪/中风险等
  -> 从 assessment_probe_prompt.txt 选择自然追问
  -> 下一轮用户回答
  -> record_user_answer()
  -> AssessmentObservation 持久化结构化信号
  -> EmotionEngine 使用对话负向比例和画像信号
```

关键文件：

| 文件 | 说明 |
| --- | --- |
| `backend/app/services/assessment_service.py` | 隐藏评估状态机和信号提取 |
| `backend/app/models/assessment.py` | `AssessmentSession`、`AssessmentObservation` |
| `backend/app/prompts/assessment_probe_prompt.txt` | 自然追问模板 |
| `backend/app/prompts/assessment_extract_prompt.txt` | 结构化提取 prompt，后续若接 LLM 提取需使用 |
| `frontend/src/stores/chat.js` | `assessmentState`、`assessmentSummary` |
| `backend/tests/test_p1_assessment_loop.py` | P1 闭环测试 |

状态与产品边界：

| 项 | 规则 |
| --- | --- |
| 用户可见 | 默认不展示筛查入口、进度条、诊断结果 |
| 前端状态 | 可以保存 `assessmentState`，但不要让前端自行推进可信状态 |
| 追问节奏 | 每轮最多一个问题；用户拒绝或转移话题时进入 cooldown |
| 危机表达 | 任意时刻命中自杀、自残、轻生、极端绝望时暂停评估并进入安全通道 |
| 小结 | 只能是“仅供参考”的状态小结，不是医学报告 |

## 8. 情绪与健康安全

任何健康、心理、情绪相关改动必须优先保证安全。

| 场景 | 必须行为 |
| --- | --- |
| 自杀/自残/轻生表达 | 立即触发 InterventionAgent 或 `SAFE_INTERVENTION_FALLBACK` |
| 高风险但模型超时 | 不等待普通模型，返回安全兜底 |
| PMS/PMDD/痛经知识 | 仅供参考，不做诊断，不给处方或确定性医学判断 |
| 未命中知识库 | 明确说明“暂时没有相关信息”，不要编造 |
| 低置信度状态画像 | 保存低置信度，不生成强结论 |
| 用户拒绝继续聊 | 尊重拒绝，进入冷却或轻安抚，不继续追问 |

安全风险检查清单：

| 风险 | 规避 |
| --- | --- |
| XSS | 聊天内容纯文本渲染，避免 `v-html` |
| 注入 | SQLAlchemy 参数化查询，不拼接 SQL |
| 越权 | 后端从 JWT 解析用户身份，不信任 body/query 中的用户 ID |
| 敏感信息泄露 | 日志脱敏，最小化保存 `evidence_text` |
| LLM 幻觉 | 健康知识优先基于知识库或明确“不确定” |
| LLM 超时 | 使用 deadline、fallback、前端等待阈值 |
| 过度耦合 | 新逻辑放入 service / agent / store 的既有边界，不把业务堆进页面或路由 |

## 9. API 与数据契约

重要现有接口：

| 接口 | 说明 |
| --- | --- |
| `POST /api/v1/auth/login` | 登录，返回 token |
| `POST /api/v1/auth/register` | 注册 |
| `POST /api/v1/chat/session` | 创建聊天 session |
| `POST /api/v1/chat/message` | REST 聊天主入口 |
| `WS /api/v1/chat/ws/{user_id}` | WebSocket 聊天入口 |
| `POST /api/v1/chat/stream` | SSE 流式聊天 |
| `GET /api/v1/chat/history/{session_id}` | 获取对话历史 |
| `/api/v1/menstrual/*` | 月经记录与预测 |
| `/api/v1/diary/*` | 情绪日记 |
| `/api/v1/emotion/*` | 情绪分析与推荐 |
| `/api/v1/biometric/*` | 生理数据 |
| `/api/v1/music/*` | 音乐推荐 |
| `/api/v1/interview/*` | 旧显性访谈兼容入口，不作为新 P1 主链路 |

聊天响应关键字段：

| 字段 | 说明 |
| --- | --- |
| `reply` / `message` | AI 回复文本 |
| `intent` | 路由或意图 |
| `risk_level` | 风险等级 |
| `actions` | 站内或轻量行动建议 |
| `suggestions` | 快捷回复建议 |
| `reply_status` | `ok`、`timeout_fallback`、`error_fallback` |
| `elapsed_ms` | 本轮耗时 |
| `assessment_state` | 隐藏经前状态了解摘要 |
| `memory_state` | 聊天记忆更新状态 |

## 10. 文档与 SPEC 规则

当用户要求规划、设计、状态梳理或 SPEC 时，优先先写文档，不要直接跳实现，除非用户明确要求开发。

MoonCARE SPEC 必须包含：

1. 为什么做（Why）
2. 要改变什么（What Changes / BREAKING）
3. 会影响什么（Impact）
4. 具体怎么做、怎样算完成（清晰 SHALL 需求 + WHEN/THEN 验收场景）
5. 如何处理废弃或迁移（REMOVED + Reason/Migration）

文档写作要求：

| 要求 | 说明 |
| --- | --- |
| 状态标注 | 新功能必须注明已完成、计划中、需要验证 |
| 影响范围 | 标注路径、接口、store、模型、prompt 或文档影响 |
| 对外契约 | API、组件 props、store 字段需要写类型、默认值、说明 |
| 技术事实 | 使用“根据当前代码/文档”限定可能变化的事实 |
| 算法变更 | 修改情绪融合权重、PSST 评分、周期预测时必须提醒同步技术文档 |
| 医学事实 | 不确定就标注 TODO 或建议用户确认，不编造 |

## 11. 开发命令

本地准备：

```bash
npm install
cd frontend
npm install
cd ../backend
pip install -r requirements.txt
```

启动服务：

```bash
# 可选：Awareness 本地记忆服务
npm run awareness:start

# 后端，仓库根目录执行
python -m uvicorn app.main:app --app-dir backend --reload --port 8000

# 前端
cd frontend
npm run dev
```

访问地址：

| 服务 | 地址 |
| --- | --- |
| 前端 | `http://localhost:3000` 或 Vite 实际输出端口 |
| 后端 | `http://localhost:8000` |
| API 文档 | `http://localhost:8000/docs` |
| Awareness | `http://localhost:37800` |

常用验证：

```bash
python -m compileall backend
python -m unittest backend.tests.test_p0_safety_and_prompts -v
python -m unittest backend.tests.test_p1_assessment_loop -v
python -m unittest backend.tests.test_vllm_integration -v
cd frontend
npm run build
```

Docker/服务器方向验证：

```bash
docker compose config
docker compose build
docker compose up -d
docker compose logs -f app
```

部署相关验证还应覆盖：

| 检查项 | 验证方式 |
| --- | --- |
| 健康接口 | 访问服务器反代后的 `/healthz` |
| API 文档 | 访问 `/docs`，确认生产环境是否允许暴露 |
| WebSocket | 验证 `/api/v1/chat/ws/{user_id}` 在反向代理后可 upgrade |
| 前端资源 | 若采用一体化镜像，确认 `frontend/dist` 被正确挂载并支持路由刷新 |
| 数据库 | 重启容器后确认用户、聊天和评估数据仍在 volume 中 |
| LLM | 用低风险聊天、知识问答、危机样例分别验证 `ok` 与 fallback 行为 |

## 12. 变更策略

| 类型 | 策略 |
| --- | --- |
| 小修复 | 保持现有命名、目录和接口兼容，补最小测试 |
| 新功能 | 先确认需求和安全边界，再写 SPEC 或任务拆分 |
| 大重构 | 先说明理由、影响范围、迁移方案和回滚方式 |
| 前端体验 | 保持 MoonCARE 的移动端应用体验，不做营销页 |
| Agent 行为 | 不绕过安全路由，不硬编码长 prompt，不用诊断语气 |
| 数据结构 | 明确迁移和兼容旧数据，避免破坏已有会话 |
| 部署变更 | 默认按 Docker + 服务器思路设计；前端部署方式未定时必须保留分支并标注待确认 |

## 13. 默认后续工作计划

后续 agent 接到没有明确优先级的 MoonCARE 开发任务时，默认按下面路线推进。不要因为某个页面视觉上已经存在，就默认它已经完成业务闭环。

### 13.1 默认排序

| 优先级 | 阶段 | 目标 | 默认处理方式 |
| --- | --- | --- | --- |
| P0 | 工程可运行与安全边界 | 让 Docker + 服务器部署、JWT 用户隔离、危机路由和敏感日志先可信 | 先修阻断真实部署或用户安全的问题 |
| P1 | 核心产品闭环 | 打通登录后自然聊天、经前状态了解、周期/日记数据、情绪分析和状态小结 | 先写 SPEC 或状态映射，再实现最短可验证闭环 |
| P2 | 空壳功能补全 | 把已有页面入口变成可持久化、可回放、可解释的功能 | 每个页面按“数据源、用户动作、后端接口、状态、测试”补齐 |
| P3 | 体验成熟度 | 优化文案、加载态、错误态、历史记录、隐私设置和部署运维体验 | 在 P0/P1 稳定后逐步做 |

### 13.2 P0 工程基线

| 工作项 | 为什么优先 | 完成标准 |
| --- | --- | --- |
| Docker Compose 可启动 | 当前部署方向是 Docker + 服务器，且 compose 已存在但需验证 | `docker compose config/build/up` 可跑；app 健康检查命中真实 `/healthz` |
| 生产环境变量整理 | 默认密钥、数据库密码、LLM Key 不能进入生产 | `.env.example` 或部署文档列清必填项和安全默认值 |
| 反向代理方案确认 | WebSocket、HTTPS、静态资源和 CORS 都依赖它 | 明确 Nginx/Caddy/Traefik 之一，并写出 API/WS 转发规则 |
| 用户隔离审计 | 部分接口仍接受显式 `user_id` 或按 `record_id` 查记录 | 所有健康/情绪/日记/周期/音乐接口以 JWT 用户为准，并补越权测试 |
| 危机优先回归 | 情绪健康产品的安全底线 | 危机样例在 REST、SSE、WebSocket、旧 interview 入口均不走普通回复 |
| 日志脱敏 | 聊天、日记和经前状态属于敏感数据 | 生产日志不输出完整原文、token、LLM Key、数据库 URL |

### 13.3 P1 产品闭环

| 工作项 | 目标效果 | 完成标准 |
| --- | --- | --- |
| 统一聊天主入口 | 用户从首页进入后自然聊天，不被带到显性筛查 | 首页“经前状态聊聊”迁移到 `/chat` 隐藏式 assessment 流程，旧 `/interview/*` 仅保留兼容或调试 |
| 评估提取可信化 | 经前状态画像能被后续分析复用 | `assessment_extract_prompt.txt` 真正接入 LLM 结构化提取；失败时回退规则提取 |
| 情绪分析解释化 | 首页 PMS 风险、心情分数不只是算法数字 | 返回可解释字段：数据来源、置信度、缺失数据、仅供参考提示 |
| 周期 + 日记 + 聊天联动 | 日记和聊天不各自孤立 | 日记关键词、周期阶段、隐藏 assessment 信号共同进入 `EmotionEngine` |
| 状态小结 | 给用户可理解的小结，不做诊断 | 只在足够信号下生成“仅供参考”的状态小结，并可在聊天内回看 |

### 13.4 P2 页面功能补齐

| 页面/模块 | 当前方向 | 完成标准 |
| --- | --- | --- |
| 周期页 | 从“能新增记录”补到完整周期管理 | 前端支持编辑、删除、异常周期提示、预测置信度解释；后端按用户隔离更新/删除 |
| 日记页 | 从“文本日记”补到可管理日记 | 前端支持编辑/删除；语音入口若保留必须接 Web Speech API 或明确标为计划中 |
| 音乐疗愈 | 从“随机播放本地/示例音乐”补到可解释推荐 | 推荐说明来自情绪/周期/用户偏好；本地音乐、示例音乐、版权和播放失败都有处理 |
| 呼吸引导 | 从“本地计时练习”补到可记录干预工具 | 可从 Agent action 打开；记录完成状态；避免危机场景把呼吸当唯一建议 |
| 个人中心/设置 | 从展示页补到真实设置 | 支持昵称、通知、隐私、退出、数据导出/删除入口的设计或实现 |
| 首页 | 从仪表盘补到可信状态概览 | 未有数据时展示明确空状态；铃铛、设置等图标要么接功能，要么移除 |
| 聊天历史 | 从可拉取历史补到完整恢复 | 恢复消息时保留 session、actions、assessment 摘要和错误状态；不丢关键上下文 |

### 13.5 默认验收清单

任意功能完成前，至少回答这些问题：

| 问题 | 必须有的证据 |
| --- | --- |
| 用户数据是否只读写当前登录用户？ | 后端查询包含 JWT 用户过滤；有越权测试或代码审查证据 |
| 遇到危机表达会不会绕过安全层？ | REST/SSE/WS 或相关入口测试 |
| 前端是否有真实空状态和错误状态？ | 页面截图或浏览器验证 |
| 是否保存了必要数据，且没有过度保存敏感原文？ | 模型字段、日志和 evidence_text 检查 |
| 是否改变算法或权重？ | 技术文档同步更新 |
| 是否适合 Docker + 服务器部署？ | 环境变量、健康检查、反向代理和持久化说明 |

## 14. 空壳/半空壳功能清单

本节是后续开发的规划指引。这里的“空壳”不包含用户特别说明的硬件接口本身；硬件、蓝牙、USB、脑血流设备接入属于单独的硬件/数据源验证任务。

### 14.1 判断标准

| 等级 | 含义 |
| --- | --- |
| 空壳 | 页面或入口已经出现，但没有真实业务闭环、后端持久化、生产可用数据源或用户动作结果 |
| 半空壳 | 功能能跑一部分，但依赖 mock、随机、内存状态、旧流程、缺少权限隔离或缺少产品解释 |
| 已有闭环但需加固 | 已能完成主要动作，但还有安全、测试、部署或体验成熟度问题 |

### 14.2 当前空壳/半空壳

| 功能 | 等级 | 当前证据 | 后续指引 |
| --- | --- | --- | --- |
| 首页铃铛和设置图标 | 空壳 | `Home.vue` 中按钮只有 SVG，没有点击逻辑或路由 | 接通知/设置功能，或先移除避免误导 |
| 首页“经前状态聊聊” | 半空壳 | 调用旧 `interviewAPI.start()` 并设置 `isInterviewMode` | 迁移到聊天主入口和隐藏 assessment，不再默认启动显性访谈 |
| 个人中心设置 | 空壳 | `Profile.vue` 设置行只有静态容器，无路由或弹窗 | 先设计通知、隐私、数据管理、模型偏好等真实设置 |
| 个人资料管理 | 半空壳 | 只展示 localStorage 中的昵称/邮箱，无编辑接口和页面 | 增加 profile API、编辑昵称、数据导出/删除规划 |
| 日记语音输入 | 空壳 | `Diary.vue` 用 `setTimeout` 写入“（语音转写内容）” | 接 Web Speech API/后端转写，或标成计划中并默认隐藏 |
| 日记管理 UI | 半空壳 | 后端有 get/update/delete，前端列表只展示和新增 | 补编辑、删除、详情、错误态和权限测试 |
| 周期记录管理 UI | 半空壳 | 前端只支持新增和列表；后端 update/delete 当前未按登录用户过滤 | 补前端编辑/删除；修后端越权风险；增加异常周期提示 |
| 波动曲线页面 | 半空壳 | `WaveMonitor.vue` 无数据时自动 seed/mock，并用随机 CBF/情绪 | 明确 demo 状态；真实数据缺失时展示空状态，不 silently mock |
| 音乐疗愈推荐 | 半空壳 | 优先随机本地音乐，否则示例音乐；未记录播放反馈和偏好 | 做推荐解释、版权/来源、播放失败处理、用户偏好闭环 |
| 呼吸引导 | 半空壳 | 本地计时器可用，但不记录完成，不与干预结果闭环 | 记录练习完成；Agent action 可带场景进入；危机状态不得只推呼吸 |
| 旧 `/interview/*` 流程 | 半空壳 | 使用内存 `interview_sessions`，重启丢失；和 P1 隐藏 assessment 主线并存 | 仅保留兼容/调试，或迁移到 DB 状态；用户可见文案避免筛查化 |
| Assessment LLM 提取 | 半空壳 | `assessment_extract_prompt.txt` 存在，但当前 `extract_signals()` 是规则提取 | 接入 LLM 结构化提取 + timeout fallback + 低置信度保存 |
| 状态小结/报告 | 半空壳 | `ReportService` 服务旧 interview；隐藏 assessment 只暴露 summary_available | 统一成聊天内“仅供参考”状态小结，不生成医学报告感 |
| 情绪/音乐 API 用户隔离 | 半空壳 | `emotion.py`、`music.py` 仍显式接收 `user_id` 参数 | 改成 JWT 当前用户；前端移除硬编码/冗余 userId |
| 日记/周期单条更新删除越权 | 半空壳 | 部分接口按 `diary_id`/`record_id` 查，不附加当前用户过滤 | 改为 `id + user_id` 查询，并补越权测试 |
| 聊天历史恢复 | 半空壳 | 前端恢复时主要恢复 role/content，actions/assessment 等上下文不完整 | 后端历史返回必要元数据；前端恢复 session 状态和隐藏摘要 |

### 14.3 不计入本清单的硬件/数据源事项

| 项 | 处理方式 |
| --- | --- |
| USB/蓝牙接收脚本 | 作为硬件接入专项，不在“空壳功能”中评价 |
| `/biometric/raw` | 作为硬件网关输入接口，后续需另写设备协议和鉴权方案 |
| 脑血流接口 | 当前代码标注为预留接口；后续作为硬件/医学数据源验证专项 |
| 生理情绪分类算法 | 当前可用但依赖真实硬件样本校准；不要把随机 demo 数据当真实效果 |

### 14.4 后续 agent 处理规则

| 场景 | 默认动作 |
| --- | --- |
| 用户要求“优化页面” | 先查该页面是否在空壳清单；如果是，优先补业务闭环，而不是只改视觉 |
| 用户要求“部署” | 先走 P0 Docker + 服务器基线，不先做 Vercel/Railway |
| 用户要求“完善聊天/PMS” | 先保护隐藏式自然对话主线，不把旧 interview 流程前台化 |
| 用户要求“接入数据” | 先确认数据来源、用户隔离、缺失数据空状态和日志脱敏 |
| 用户要求“上线前检查” | 重点查 P0、空壳清单、越权、CORS、密钥、healthcheck、WebSocket 反代 |

## 15. 当前需特别注意的 TODO

| TODO | 原因 |
| --- | --- |
| 生产 CORS 需要收敛 | 当前允许 `*`，生产会有安全风险 |
| `SECRET_KEY` 必须生产替换 | 默认值仅适合本地开发 |
| SQLite 并发能力有限 | 高并发或多 worker 部署前需评估 PostgreSQL |
| `docker-compose.yml` healthcheck | 已修正：compose 检查 `/healthz`，FastAPI 也已更新为 `/healthz` |
| `entrypoint.sh` 依赖 `pg_isready` | 最终镜像是否包含 PostgreSQL client 工具需要验证 |
| 前端部署路线未定 | 先保留一体化镜像、独立静态容器、独立托管三种方案，不要提前锁死 |
| 服务器反向代理未定 | 需要确认 Nginx/Caddy/Traefik 或云网关，并同步 WebSocket、HTTPS、CORS 策略 |
| LLM provider 真实压测 | GLM-5.1、accelerated provider、timeout 参数需要真实端点验证 |
| 知识库覆盖率 | 若知识库没有相关内容，必须说明暂无信息 |
| 隐藏评估提取质量 | 当前规则提取已可用，LLM 结构化提取和权重仍需真实样本验证 |
| `MoonCARE/` 嵌套目录归属 | 当前为未跟踪目录，处理文件前先确认是否为副本、打包产物或另一个工作区 |
