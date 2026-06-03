# P1 State Summary Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 MoonCARE 增加“仅供参考”的状态小结闭环，让周期、日记、聊天隐藏 assessment 和情绪分析结果能被用户安全地看见和回看。

**Architecture:** 新增后端状态小结服务，首版使用规则汇总，不依赖 LLM 生成，避免超时和诊断化表述。API 只读、JWT 用户隔离；前端通过 `chatStore` 拉取和展示小结，并把首页“经前状态聊聊”迁移到聊天主入口。

**Tech Stack:** FastAPI, SQLAlchemy, unittest, Vue 3 Composition API, Pinia, Axios, Vite.

---

## File Map

| File | Responsibility |
| --- | --- |
| `backend/app/services/state_summary_service.py` | 汇总当前用户周期、日记、聊天、assessment 和 emotion 信号，生成非诊断状态小结。 |
| `backend/app/schemas/state_summary.py` | 定义状态小结 API 响应结构，包含来源、缺失数据、置信度和建议。 |
| `backend/app/api/v1/state_summary.py` | 新增 `/api/v1/state-summary/current` 只读接口，使用 JWT 当前用户。 |
| `backend/app/main.py` | 注册状态小结 router。 |
| `backend/app/api/v1/emotion.py` | 兼容增强情绪预测解释字段，或由状态小结服务内部引用 `EmotionEngine`。 |
| `frontend/src/api/index.js` | 新增 `stateSummaryAPI.current()`。 |
| `frontend/src/stores/chat.js` | 新增 `stateSummary`、`summaryLoading`、`summaryError` 和 `loadStateSummary()`。 |
| `frontend/src/views/Chat.vue` | 增加“状态小结”入口、加载态、空状态和错误态。 |
| `frontend/src/views/Home.vue` | 将“经前状态聊聊”入口迁移到 `/chat`，不再启动旧 `interviewAPI.start()`。 |
| `backend/tests/test_p1_state_summary.py` | 覆盖小结服务、API 用户隔离、危机优先和空状态。 |
| `MoonCAREpack/...` | 验证通过后同步部署包。 |

## Task 1: Backend State Summary Contract

**Files:**
- Create: `backend/app/schemas/state_summary.py`
- Create: `backend/tests/test_p1_state_summary.py`

- [ ] Add response schemas with these fields:
  - `summary_available: bool`
  - `title: str`
  - `level: str`
  - `confidence: float`
  - `summary_text: str`
  - `observations: list[dict]`
  - `sources: list[dict]`
  - `missing_data: list[str]`
  - `suggestions: list[dict]`
  - `disclaimer: str`
  - `generated_at: datetime`

- [ ] Write red tests:
  - no data returns `summary_available=false`;
  - current user data appears in summary;
  - another user's diary/cycle data never appears;
  - crisis conversation returns safety boundary level.

- [ ] Run:
  - `python -m unittest backend.tests.test_p1_state_summary -v`
  - Expected before implementation: import or assertion failures.

## Task 2: StateSummaryService

**Files:**
- Create: `backend/app/services/state_summary_service.py`
- Test: `backend/tests/test_p1_state_summary.py`

- [ ] Implement `StateSummaryService(db).build_current_summary(user_id: int)`.
- [ ] Query only current user data:
  - latest 1-3 `MenstrualRecord`;
  - recent 7-14 day `MoodDiary`;
  - recent `Conversation` rows for risk and context, excluding sensitive raw transcript from output;
  - active/latest `AssessmentSession` and `AssessmentObservation`;
  - `EmotionEngine.analyze(user_id)` with exception fallback.
- [ ] Generate deterministic summary:
  - data insufficient: explain missing data;
  - ordinary signal: summarize cycle phase, diary keywords, mood trend, assessment dimensions;
  - crisis signal: use safety text and no ordinary PMS interpretation.
- [ ] Bound all user text:
  - output keywords and short snippets only;
  - do not include full diary or full chat messages.
- [ ] Run red tests until green.

## Task 3: API Route

**Files:**
- Create: `backend/app/api/v1/state_summary.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_p1_state_summary.py`

- [ ] Add `GET /api/v1/state-summary/current`.
- [ ] Use `user_id: int = Depends(get_current_user_id)`.
- [ ] Return the schema from `StateSummaryService`.
- [ ] Add API tests:
  - authenticated request succeeds;
  - unauthenticated request returns 401;
  - `?user_id=<other>` is ignored if sent.

## Task 4: Frontend Store And API

**Files:**
- Modify: `frontend/src/api/index.js`
- Modify: `frontend/src/stores/chat.js`

- [ ] Add `stateSummaryAPI.current()`.
- [ ] Add chat store state:
  - `stateSummary`
  - `summaryLoading`
  - `summaryError`
- [ ] Add `loadStateSummary()` with existing Axios error handling.
- [ ] Keep all state centralized in `chatStore`.

## Task 5: Chat And Home UX

**Files:**
- Modify: `frontend/src/views/Chat.vue`
- Modify: `frontend/src/views/Home.vue`

- [ ] In Chat page:
  - add a compact “状态小结” action near existing mode/options controls;
  - show modal or inline panel with title, summary, sources, missing data, suggestions and disclaimer;
  - show empty state when `summary_available=false`;
  - show soft error state when API fails.

- [ ] In Home page:
  - change “经前状态聊聊” click behavior to route to `/chat`;
  - remove default `interviewAPI.start()` from the visible main path;
  - avoid visible “筛查/测评/诊断” wording.

## Task 6: Verification And Package Sync

**Files:**
- Sync changed backend files into `MoonCAREpack/backend/app/...`
- Rebuild and sync `frontend/dist` into `MoonCAREpack/frontend/dist`

- [ ] Run focused backend tests:
  - `python -m unittest backend.tests.test_p1_state_summary -v`
  - `python -m unittest backend.tests.test_p0_user_isolation backend.tests.test_p0_safety_and_prompts backend.tests.test_p1_assessment_loop backend.tests.test_p1_health_context -v`
- [ ] Run `python -m compileall backend`.
- [ ] Run `npm run build` in `frontend`.
- [ ] Start backend and frontend locally on `8000` and `5180`.
- [ ] Browser/manual test:
  - empty login;
  - add cycle record;
  - add diary;
  - chat once;
  - open 状态小结;
  - verify no diagnosis wording and no raw private transcript.

## Risk Notes

| Risk | Handling |
| --- | --- |
| 小结变成诊断/筛查 | 固定免责声明和非诊断用词，测试禁止 `诊断结果`、`你得了`、`正式筛查`。 |
| 跨用户数据泄露 | 服务和 API 全部使用 JWT `user_id` 过滤，测试创建双用户数据。 |
| 敏感原文泄露 | 输出关键词、计数、短摘要，不输出完整日记或聊天原文。 |
| LLM 超时 | 首版规则生成，不依赖 LLM。 |
| 危机风险被普通总结覆盖 | 危机信号优先返回安全边界文案和求助建议。 |
| 首页旧 interview 破坏主线 | 保留 `/interview/*` 兼容，但首页主入口只去 `/chat`。 |
