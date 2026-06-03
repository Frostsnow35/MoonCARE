# MoonCARE Chat Agent 优化 Codex 提示词

> 版本：1.0
> 日期：2026-05-26
> 目的：指导 AI Agent 完成聊天 Agent 的流式输出、缓存加速、回复质量、上下文机制和记忆优化

---

## 系统角色

你是一个专业的 Python 后端工程师，负责优化 MoonCARE 项目的聊天 Agent 系统。
MoonCARE 是一个面向女性的月经前情绪陪伴应用。

**核心约束：**
- 所有修改必须保留现有安全 fallback 和危机干预机制
- 不削弱 PerceptionAgent → Router → Agent 安全路由
- 不绕过危机检测关键词（自杀、自残、轻生等）
- 修改后必须运行现有测试确保不破坏功能

---

## 项目结构参考

```
backend/
├── app/
│   ├── agents/
│   │   ├── router.py           # 路由判断
│   │   ├── perception_agent.py # 情绪感知
│   │   ├── support_agent.py    # 情绪陪伴
│   │   ├── knowledge_agent.py  # 知识问答
│   │   ├── intervention_agent.py# 危机干预
│   │   └── llm_service.py      # LLM 调用
│   ├── api/v1/
│   │   └── chat.py            # 聊天 API 入口
│   ├── services/
│   │   ├── agent_service.py   # Agent 编排服务
│   │   ├── semantic_cache_service.py  # 语义缓存
│   │   ├── chat_memory_service.py    # 聊天记忆
│   │   ├── product_memory_service.py # 产品记忆
│   │   └── response_quality_service.py # 回复质量
│   ├── prompts/               # Prompt 模板（优先修改这里）
│   │   ├── support_prompt.txt
│   │   └── default_chat_prompt.txt
│   └── utils/
│       └── safety.py          # 安全干预
frontend/src/views/Chat.vue    # 前端聊天页面
```

---

## 一、流式输出优化

### 1.1 目标
- 用户发送消息后 3 秒内开始看到输出
- 20 秒内完成完整响应
- 保持危机检测优先

### 1.2 实现指导

#### 后端 SSE 端点 (`chat.py`)

```python
# 重构 /chat/stream 端点，实现真正的 chunked transfer
@router.post("/stream")
async def chat_stream(
    message: str = Form(...),
    user_id: int = Depends(get_current_user_id),
    session_id: Optional[str] = Form(None),
    agent_mode: str = Form("auto"),
    db: Session = Depends(get_db)
):
    """SSE 流式聊天端点"""
    # 1. 危机预检（必须先完成）
    risk_level = await check_crisis_risk(message)
    if risk_level in ["high", "crisis"]:
        # 危机情况不走流式，直接返回安全响应
        return await handle_crisis_fallback(message, risk_level)

    # 2. 初始化流式响应
    async def event_generator():
        # 使用 yield 逐块发送
        async for chunk in agent_service.stream_response(...):
            yield f"data: {json.dumps({'token': chunk})}\n\n"
            # 添加合理的 chunk 间隔，让前端有时间渲染
            await asyncio.sleep(0.05)

        # 发送结束标记
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

#### AgentService 流式方法 (`agent_service.py`)

```python
async def stream_response(self, user_id, session_id, user_message, context, agent_mode):
    """流式响应生成器"""
    # 1. 快速路径：检查缓存
    cache_result = await self._check_semantic_cache(user_message, context)
    if cache_result:
        # 缓存命中也用流式返回，提升体验
        for chunk in self._chunk_text(cache_result["response"]):
            yield chunk
            await asyncio.sleep(0.05)
        return

    # 2. 路由决策
    router = self._get_router()
    agent_name, routing_confidence = await router.route(
        user_message, context, agent_mode
    )

    # 3. 获取 Agent
    agent = self._get_agent(agent_name)

    # 4. 流式生成
    async for token in agent.stream_generate(user_message, context):
        yield token
```

### 1.3 前端适配 (`Chat.vue`)

```javascript
// SSE 流式处理
async function handleStreamResponse(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    // 解析 SSE 格式: data: {"token": "xxx"}\n\n
    const lines = chunk.split('\n');
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        if (data.token) {
          appendTokenToMessage(data.token);
        }
      }
    }
  }
}
```

---

## 二、缓存加速优化

### 2.1 目标
- 多粒度缓存：整句 > 短语 > 意图
- 相似度阈值可配置（默认 0.85）
- 缓存命中时直接返回，elapsed_ms < 100ms
- 缓存大小上限 1000 条 + LRU 淘汰

### 2.2 实现指导

#### 语义缓存服务 (`semantic_cache_service.py`)

```python
class SemanticCacheService:
    def __init__(self, max_size=1000, similarity_threshold=0.85):
        self.cache = LRUCache(max_size)
        self.similarity_threshold = similarity_threshold

    async def get_cached_response(self, user_message: str, context: dict) -> Optional[dict]:
        """多粒度缓存查询"""
        # 粒度1: 整句精确匹配
        exact_key = self._normalize(user_message)
        if exact_key in self.cache:
            return self.cache[exact_key]

        # 粒度2: 短语相似匹配
        tokens = self._tokenize(user_message)
        for key, value in self.cache.items():
            similarity = self._calculate_similarity(tokens, self._tokenize(key))
            if similarity >= self.similarity_threshold:
                # 更新访问时间（LRU）
                self.cache.move_to_end(key)
                return value

        # 粒度3: 意图匹配（情绪类/知识类）
        intent = context.get("intent")
        if intent:
            intent_cache = self.cache.get(f"intent:{intent}")
            if intent_cache:
                # 检查情境是否相似
                if self._context_similar(context, intent_cache["context"]):
                    return intent_cache

        return None

    async def cache_response(self, user_message: str, response: str, context: dict, intent: str):
        """缓存响应"""
        key = self._normalize(user_message)
        self.cache[key] = {
            "response": response,
            "context": context,
            "intent": intent,
            "timestamp": time.time(),
            "access_count": 0
        }

    def _calculate_similarity(self, tokens1: list, tokens2: list) -> float:
        """基于 token 的 Jaccard 相似度"""
        set1, set2 = set(tokens1), set(tokens2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0

    def _context_similar(self, ctx1: dict, ctx2: dict) -> bool:
        """检查情境相似性（情绪、时间等）"""
        # 简化实现：只比较情绪标签
        emotion1 = ctx1.get("detected_emotion", "")
        emotion2 = ctx2.get("detected_emotion", "")
        return emotion1 == emotion2
```

---

## 三、回复质量优化

### 3.1 目标
- 每轮回复包含共情回应 + 理解表达 + 开放式问题
- action_suggestions 结合用户情绪和场景
- 避免说教式科普，优先共情陪伴
- 回复结构化：分段、emoji 点缀、要点清晰

### 3.2 实现指导

#### SupportAgent Prompt 优化 (`support_prompt.txt`)

```markdown
# 角色
你是一个温柔的女性情绪陪伴助手，名为 MoonCare。

# 回复原则

## 3.1 共情优先
- 先回应用户情绪，不先讲道理或科普
- 使用"我理解"、"我能感受到"、"听起来你..."等共情表达

## 3.2 回复结构
每轮回复必须包含以下部分（按顺序）：
1. **共情回应**（1-2句）：回应用户当前情绪
2. **理解表达**（1-2句）：表达对她情况的理解
3. **温柔引导**（可选1句）：鼓励继续表达
4. **开放式问题**（必须1个）：引导用户深入表达

## 3.3 避免事项
- ❌ 说教式科普（"其实经前综合征是因为..."）
- ❌ 过度安慰（"别难过别难过"）
- ❌ 立即给建议（"你应该..."）
- ❌ 否定情绪（"你不需要难过"）

## 3.4 推荐表达
- ✅ "听起来你最近工作压力很大..."
- ✅ "我能感受到你现在很疲惫..."
- ✅ "这种情况确实会让人感到沮丧..."
- ✅ "想和我多说一点吗？是什么让你有这样的感觉呢？"

## 3.5 结合行动建议
当需要给出行动建议时：
- 先完成共情和理解
- 自然引入站内功能（不要太生硬）
- 同时提供1-2个简单外部行动

## 3.6 回复示例
用户："最近总是心情不好，看什么都不顺眼"

回复：
我能感受到你最近的烦躁和低落情绪 🌸

这种情况确实会让人感到沮丧和无力...

你现在的心情让我想到，也许有些事情一直在累积着。

想和我说说，是什么让你最近特别容易心情不好吗？
```

#### 行动建议优化 (`agent_service.py`)

```python
def _generate_action_suggestions(self, state: dict, agent_mode: str) -> List[dict]:
    """根据情绪和场景生成精准的行动建议"""
    detected_emotion = state.get("detected_emotion", "unknown")
    risk_level = state.get("risk_level", "low")
    cycle_phase = state.get("cycle_phase", "")

    suggestions = []

    # 情绪 → 功能映射
    emotion_action_map = {
        "焦虑": [
            {"type": "internal", "action": "breathing", "label": "试试呼吸练习", "emoji": "🌬️"},
            {"type": "external", "action": "walk", "label": "去窗边站一会儿，透透气", "emoji": "🌳"}
        ],
        "烦躁": [
            {"type": "internal", "action": "music", "label": "听听舒缓的音乐", "emoji": "🎵"},
            {"type": "internal", "action": "diary", "label": "写写日记，把情绪记录下来", "emoji": "📝"}
        ],
        "低落": [
            {"type": "internal", "action": "diary", "label": "记录下现在的感受", "emoji": "💭"},
            {"type": "internal", "action": "cycle", "label": "看看最近的周期状态", "emoji": "🌙"}
        ],
        "疲惫": [
            {"type": "external", "action": "rest", "label": "允许自己休息一会儿", "emoji": "☁️"},
            {"type": "internal", "action": "breathing", "label": "试试深呼吸放松", "emoji": "🌸"}
        ]
    }

    # 根据情绪获取建议
    emotion_suggestions = emotion_action_map.get(detected_emotion, emotion_action_map["疲惫"])

    # 限制数量，优先选择最相关的
    for sug in emotion_suggestions[:2]:
        suggestions.append(sug)

    # 如果是经期/经前，额外添加一个周期相关的建议
    if cycle_phase in ["经前", "经期"]:
        suggestions.append({
            "type": "internal",
            "action": "cycle",
            "label": "记录一下现在的状态",
            "emoji": "📊"
        })

    return suggestions
```

---

## 四、上下文机制优化

### 4.1 目标
- 双窗口：最近 20 轮完整 + 更早轮次摘要
- 关键信息（情绪标签、偏好）置顶
- 上下文总长度不超过 30 轮

### 4.2 实现指导

#### 对话压缩服务 (`chat_memory_service.py`)

```python
class ConversationCompactionService:
    """对话历史压缩服务"""

    FULL_WINDOW_SIZE = 20  # 完整保留最近20轮
    MAX_TOTAL_TURNS = 30   # 总轮次上限

    def build_context(self, conversation_history: list) -> str:
        """构建压缩后的上下文"""
        if len(conversation_history) <= self.FULL_WINDOW_SIZE:
            return self._format_conversation(conversation_history)

        # 保留最近20轮完整
        recent = conversation_history[-self.FULL_WINDOW_SIZE:]

        # 更早的轮次生成摘要
        older = conversation_history[:-self.FULL_WINDOW_SIZE]
        older_summary = self._summarize_older_conversation(older)

        # 构建最终上下文
        context_parts = []

        # 1. 关键信息置顶
        key_info = self._extract_key_information(conversation_history)
        if key_info:
            context_parts.append(f"[关键信息] {key_info}")

        # 2. 历史摘要
        if older_summary:
            context_parts.append(f"[之前对话摘要] {older_summary}")

        # 3. 近期完整对话
        context_parts.append("[最近对话]")
        context_parts.append(self._format_conversation(recent))

        return "\n\n".join(context_parts)

    def _extract_key_information(self, history: list) -> str:
        """提取关键信息：情绪标签、用户偏好、重大事件"""
        key_points = []

        emotions = []
        preferences = []
        events = []

        for conv in history:
            if conv.role == "assistant":
                content = conv.content.lower()
                # 提取情绪标签
                if "焦虑" in content:
                    emotions.append("焦虑")
                if "烦躁" in content:
                    emotions.append("烦躁")
                if "低落" in content:
                    emotions.append("低落")

        if emotions:
            # 统计最常见的情绪
            from collections import Counter
            most_common = Counter(emotions).most_common(1)
            key_points.append(f"用户情绪状态：{most_common[0][0]}")

        return "; ".join(key_points) if key_points else ""

    def _summarize_older_conversation(self, older_turns: list) -> str:
        """生成早期对话摘要"""
        # 简化实现：提取关键主题
        user_messages = [c.content for c in older_turns if c.role == "user"]
        if not user_messages:
            return ""

        # 简单统计：情绪词频
        emotion_keywords = ["焦虑", "烦躁", "低落", "疲惫", "开心", "生气"]
        keyword_count = {}

        for msg in user_messages:
            for kw in emotion_keywords:
                if kw in msg:
                    keyword_count[kw] = keyword_count.get(kw, 0) + 1

        if keyword_count:
            top_emotion = max(keyword_count, key=keyword_count.get)
            return f"之前主要情绪：{top_emotion}（共{keyword_count[top_emotion]}次提及）"

        return ""
```

---

## 五、记忆体系优化

### 5.1 目标
- 短期记忆：会话内情绪和事件
- 中期记忆：跨会话关键信息提取
- 长期记忆：用户偏好和陪伴风格
- 事件卡片：重大事件标记和后续关心
- 遗忘机制：重要性评分 + 时间衰减

### 5.2 实现指导

#### 产品记忆服务扩展 (`product_memory_service.py`)

```python
class ProductMemoryService:
    """产品级记忆服务 - 跨会话记忆"""

    # 记忆层级
    SHORT_TERM_MAX = 10   # 短期记忆条数
    MID_TERM_MAX = 50     # 中期记忆条数
    LONG_TERM_MAX = 20    # 长期记忆条数

    # 遗忘配置
    DECAY_RATE = 0.95    # 时间衰减率
    IMPORTANCE_THRESHOLD = 0.3  # 遗忘阈值

    async def update_memory(self, user_id: int, conversation: list, db: Session):
        """更新用户记忆"""
        # 1. 提取短期记忆（当前会话）
        short_term = self._extract_short_term_memory(conversation)

        # 2. 合并到中期记忆
        mid_term = await self._get_mid_term_memory(user_id, db)
        mid_term = self._merge_short_to_mid(short_term, mid_term)

        # 3. 更新长期记忆（用户偏好）
        long_term = await self._get_long_term_memory(user_id, db)
        long_term = self._update_preferences(conversation, long_term)

        # 4. 应用遗忘机制
        mid_term = self._apply_forgetting(mid_term)
        long_term = self._apply_forgetting(long_term)

        # 5. 保存
        await self._save_mid_term_memory(user_id, mid_term, db)
        await self._save_long_term_memory(user_id, long_term, db)

    def _extract_short_term_memory(self, conversation: list) -> list:
        """从当前会话提取短期记忆"""
        memories = []

        for conv in conversation:
            if conv.role == "user":
                # 提取情绪词
                emotions = self._extract_emotions(conv.content)
                if emotions:
                    memories.append({
                        "type": "emotion",
                        "values": emotions,
                        "timestamp": conv.timestamp
                    })

                # 提取事件
                events = self._extract_events(conv.content)
                for event in events:
                    memories.append({
                        "type": "event",
                        "content": event,
                        "timestamp": conv.timestamp
                    })

                # 提取偏好
                preferences = self._extract_preferences(conv.content)
                for pref in preferences:
                    memories.append({
                        "type": "preference",
                        "value": pref,
                        "timestamp": conv.timestamp
                    })

        return memories

    def _apply_forgetting(self, memories: list) -> list:
        """应用遗忘机制"""
        now = time.time()
        surviving = []

        for mem in memories:
            age = now - mem.get("timestamp", 0)
            days_old = age / (24 * 3600)

            # 计算衰减分数
            importance = mem.get("importance", 1.0)
            decay_score = importance * (self.DECAY_RATE ** days_old)

            if decay_score >= self.IMPORTANCE_THRESHOLD:
                mem["decay_score"] = decay_score
                surviving.append(mem)
            # else: 遗忘

        # 按衰减分数排序，保留最重要的
        surviving.sort(key=lambda x: x.get("decay_score", 0), reverse=True)

        return surviving

    def _extract_events(self, text: str) -> list:
        """提取重大事件"""
        event_keywords = [
            "考试", "面试", "加班", "旅行", "搬家", "分手", "吵架",
            "升职", "加薪", "生日", "纪念日", "亲人", "朋友"
        ]

        events = []
        for kw in event_keywords:
            if kw in text:
                events.append(kw)

        return events
```

---

## 六、安全与危机处理

### 6.1 核心原则
- 危机检测在所有路径优先
- 流式输出前必须完成危机预检
- 缓存命中时仍需检查危机词
- 安全 fallback 不受任何优化影响

### 6.2 实现指导

```python
async def _check_crisis_risk(self, message: str) -> str:
    """危机风险预检 - 所有路径必须先执行"""
    risk_level = await check_crisis_risk(message)
    if risk_level in ["high", "crisis"]:
        return risk_level
    return "low"

async def get_response(self, user_id, session_id, user_message, context, agent_mode):
    """优化后的响应方法"""
    # 1. 危机预检（必须先完成，不能跳过）
    crisis_risk = await self._check_crisis_risk(user_message)
    if crisis_risk in ["high", "crisis"]:
        return await self._handle_crisis_response(user_message, crisis_risk)

    # 2. 缓存检查
    cache_result = await self._check_semantic_cache(user_message, context)
    if cache_result:
        # 缓存命中也再次检查危机词
        if not contains_crisis_signal(cache_result["response"]):
            return cache_result
        # 如果缓存内容包含危机信号，重新生成

    # 3. 正常 Agent 流程
    # ... (后续流程不变)
```

---

## 七、测试验证

### 7.1 必须通过的测试

```bash
# 1. 危机检测测试
pytest backend/tests/test_p0_safety_and_prompts.py -v

# 2. 聊天功能回归测试
pytest backend/tests/test_chat_agent_quality.py -v

# 3. 上下文机制测试
pytest backend/tests/test_chat_context_mechanism.py -v

# 4. 新增流式输出测试
pytest backend/tests/test_chat_streaming.py -v

# 5. 新增缓存测试
pytest backend/tests/test_semantic_cache.py -v
```

### 7.2 验收标准

| 指标 | 目标值 |
|------|--------|
| 首次输出延迟 | < 3 秒 |
| 缓存命中响应时间 | < 100ms |
| 上下文压缩后长度 | < 30 轮 |
| 危机检测召回率 | 100% |
| 行动建议准确率 | > 80% |

---

## 八、文件修改清单

| 文件 | 修改内容 |
|------|----------|
| `backend/app/api/v1/chat.py` | 重构 SSE 流式端点 |
| `backend/app/services/agent_service.py` | 添加流式方法、优化缓存、增强行动建议 |
| `backend/app/services/semantic_cache_service.py` | 多粒度缓存、LRU 淘汰 |
| `backend/app/services/chat_memory_service.py` | 双窗口压缩、上下文构建 |
| `backend/app/services/product_memory_service.py` | 多层记忆、遗忘机制 |
| `backend/app/prompts/support_prompt.txt` | 优化共情回复模板 |
| `frontend/src/views/Chat.vue` | SSE 流式渲染适配 |

---

## 九、注意事项

1. **不要破坏现有安全机制** - 危机检测必须在所有路径优先
2. **Prompt 优先于代码** - 优先修改 prompt 文件，而不是直接改 Python 代码
3. **增量提交** - 每完成一个小功能就提交，不要等全部完成
4. **测试驱动** - 如果添加新功能，先写测试再实现
5. **向后兼容** - 新增字段应该有默认值，不破坏现有调用
