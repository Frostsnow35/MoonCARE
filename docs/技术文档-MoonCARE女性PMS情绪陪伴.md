# LunaCARE 女性PMS情绪陪伴 - 技术文档

## 项目概述

**聆月 LunaCARE** 是一款专注于女性情绪健康管理的智能应用，通过整合生理数据监测、月经周期追踪、AI对话陪伴和经前状态了解，为女性用户提供全方位的情绪支持服务。

### 核心功能

| 模块 | 功能描述 |
|------|----------|
| 情绪追踪 | 结合HRV、体温、运动数据的多维情绪分析 |
| 周期预测 | 加权移动平均算法预测月经周期 |
| AI对话 | 多Agent系统驱动的智能情绪陪伴 |
| 经前状态了解 | 借鉴PMS相关问题，在自然聊天中非显性了解用户状态 |
| 音乐疗愈 | 基于情绪状态的音乐推荐 |
| 呼吸引导 | 心理疏导呼吸练习 |

---

## 系统架构

```
┌───────────────────────────────────────────────────────────┐
│                        Frontend (Vue 3)                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │  Home   │ │  Chat   │ │ Cycle   │ │  Diary  │  ...     │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘          │
│       └───────────┴───────────┴───────────┘               │
│                       │ Pinia Store                       │
└───────────────────────┼───────────────────────────────────┘
                        │ HTTP / WebSocket
┌───────────────────────┼───────────────────────────────────┐
│                       │     Backend (FastAPI)             │
│  ┌────────────────────▼────────────────────────────┐     │
│  │              API Routes (v1)                     │    │
│  │  emotion │ menstrual │ diary │ chat │ interview │     │
│  └────────────────────┬────────────────────────────┘     │
│                        │                                 │
│  ┌────────────────────▼────────────────────────────┐     │
│  │           Agent System (Multi-Agent)            │     │
│  │  Router │ Support │ Knowledge │ Interview │...  │     │
│  └────────────────────┬────────────────────────────┘     │
│                        │                                 │
│  ┌────────────────────▼────────────────────────────┐     │
│  │           Emotion Services                       │    │
│  │  EmotionEngine │ NLP │ PSST │ CyclePredictor   │     │
│  └────────────────────┬────────────────────────────┘     │
│                        │                                 │
│  ┌────────────────────▼────────────────────────────┐     │
│  │           Data Layer (SQLAlchemy + SQLite)       │    │
│  │  User │ Biometric │ Menstrual │ Mood │ Music   │     │
│  └───────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

---

## 技术亮点

### 1. 多Agent智能路由系统

项目采用**基于风险分级的人工智能路由架构**，根据用户消息内容动态选择最合适的Agent进行处理。

#### Agent架构图

```
                        用户消息
                            │
                            ▼
                ┌───────────────────────┐
                │   PerceptionAgent     │
                │    (风险等级分析)       │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │       Router          │
                │     (智能路由)         │
                └───────────┬───────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
   ┌─────────────┐  ┌─────────────┐     ┌─────────────┐
   │ Intervention│  │  Knowledge  │     │   Support   │
   │   Agent     │  │   Agent     │     │   Agent     │
   │  (危机干预)  │   │   (RAG问答) │     │  (日常陪伴)  │
   └─────────────┘  └─────────────┘     └─────────────┘
          │                 │                   │
          └─────────────────┴───────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │      LLMService       │
                │  (MiniMax / OpenAI)   │
                └───────────────────────┘
```

#### 核心实现

**PerceptionAgent** - 风险感知分析器：
```python
# 危机关键词检测（最高优先级）
crisis_keywords = ["不想活", "想死", "自杀", "结束生命"]

# 高风险关键词
high_keywords = ["没有意义", "撑不住了", "想消失"]

# 中风险关键词
medium_keywords = ["烦躁", "难受", "想哭", "崩溃", "焦虑"]
```

**Router** - 智能路由：
- 危机/高风险 → InterventionAgent（守护宝宝）
- 知识性问题 → KnowledgeAgent（RAG增强问答）
- 默认 → SupportAgent（情绪宝宝）

---

### 2. 多维度情绪分析算法

#### EmotionEngine 核心架构

```python
async def analyze(self, user_id: int, days: int = 7) -> Dict:
    # 从5个维度收集数据
    # 1. HRV指标（过去72小时）
    hrv_data = self._get_hrv_metrics(...)
    # 2. 皮肤温度趋势
    temp_trend = self._get_temperature_trend(...)
    # 3. 情绪日记关键词密度
    keyword_density = self._get_keyword_density(...)
    # 4. 对话中负面情绪比例
    negative_ratio = self._get_negative_emotion_ratio(...)
    # 5. 聊天式经前状态画像信号
    assessment_signal = self._get_assessment_signal_score(...)

    return {
        "phase": phase,           # follicular/ovulation/luteal/menstrual
        "pms_risk": pms_risk,    # 0.0-1.0
        "mood_level": mood_level, # 1-10
        "confidence": confidence  # 0-1
    }
```

#### PMS风险计算

| 因素 | 贡献值 | 条件 |
|------|--------|------|
| HRV基础 | +0.2 | HRV < 30ms |
| HRV趋势 | +0.15 | 负趋势 < -5 |
| 体温上升 | +0.15 | 体温 > 0.5℃ |
| 关键词密度 | +0.2 | 高密度负面词 |
| 负面情绪比 | +0.15 | 来自用户对话 `sentiment_score`，比值 > 0.5 |
| 经前状态画像 | +0.20 | 聊天式状态观察至少覆盖情绪/身体/功能影响中的2类 |

> 变更日期：2026-05-12  
> 影响范围：`EmotionEngine` 情绪融合权重、聊天式经前状态画像输入。  
> 状态：已完成基础接入，仍需要结合更多真实样本验证权重合理性。

---

### 3. NLP情感分析引擎

#### 情绪关键词体系

```python
EMOTION_KEYWORDS = {
    "anxious": ["焦虑", "紧张", "不安", "担心", "害怕", "慌张"],
    "sad": ["低落", "沮丧", "伤心", "难过", "抑郁"],
    "angry": ["愤怒", "生气", "易怒", "烦躁", "恼火"],
    "happy": ["开心", "高兴", "快乐", "愉悦", "愉快"],
    "calm": ["平静", "宁静", "放松", "舒缓", "安宁"],
    "stressed": ["压力", "压力山大", "紧张", "紧绷"],
    "tired": ["疲劳", "疲惫", "累", "困倦"],
    "fear": ["恐惧", "害怕", "惊恐"]
}
```

#### 敏感内容检测

```python
SENSITIVE_KEYWORDS = [
    "不想活了", "想死", "自杀", "自残", "轻生",
    "kill myself", "suicide", "end it all"
]
```

---

### 4. 经前状态非显性评估

采用**自然聊天式渐进了解**，借鉴PMS相关维度观察经前情绪、身体感受与生活影响。该能力不等同于正式筛查、检验或诊断，仅用于生成参考小结和陪伴建议。

当前实现将该能力接入聊天主流程：系统在 `/api/v1/chat` 中维护隐藏评估状态，必要时由情绪宝宝自然追问，并把用户回答结构化为经前状态画像。该画像仅用于陪伴建议和 `EmotionEngine` 参考分析，不作为正式筛查、检验或诊断依据。

#### 参考维度（18个信号）

| 类别 | 数量 | 内容 |
|------|------|------|
| 核心情绪 | 4 | 易怒、焦虑、爱哭、抑郁 |
| 躯体症状 | 10 | 兴趣减退、疲劳、睡眠障碍、食欲变化等 |
| 功能损害 | 5 | 工作、社交、家庭功能影响 |
| 危机信号 | - | 自杀/自残关键词 |

#### 评分逻辑

```python
intensity_words = {
    3: ["特别", "非常", "完全", "每天都", "严重"],
    2: ["明显", "经常", "挺", "比较", "反复"],
    1: ["有点", "偶尔", "轻微", "一点点"],
}
```

#### 风险等级判定

| 等级 | 条件 |
|------|------|
| high_risk | 危机分≥2，或(核心症状≥1 + 躯体症状≥4 + 功能损害≥1) |
| moderate_to_severe_pms | 核心≥1 + 躯体症状≥4 + 功能损害≥1 |
| mild_or_none | 默认 |

---

### 5. 周期预测算法

#### 加权移动平均

```python
def predict(self, user_id: int) -> Dict:
    # 需要至少2条周期记录
    cycle_lengths = self._calculate_cycle_lengths(records)

    # 近期周期权重更高: weights = [1, 2, 3, ..., n]
    predicted_length = self._weighted_average(cycle_lengths)

    # 基于方差的置信度计算
    if variance <= 4: confidence = 0.9
    elif variance <= 9: confidence = 0.75
```

---

### 6. 实时生理信号分类

#### EmotionClassifier 实时分析

```python
@dataclass
class EmotionScores:
    depression: float = 20.0   # 抑郁/低落
    anxiety: float = 20.0       # 焦虑/紧张
    anger: float = 15.0         # 愤怒/烦躁
    calm: float = 45.0          # 平静/放松
```

#### HRV特征提取

| 特征 | 描述 | 用途 |
|------|------|------|
| RMSSD | 相邻RR间期差值的均方根 | 评估副交感神经活性 |
| SDNN | RR间期标准差 | 评估整体心率变异性 |
| pNN50 | 相邻RR差>50ms的比例 | 高频心率变异性指标 |
| LF/HF | 低频/高频功率比 | 交感/副交感平衡 |

---

## 技术难点

### 1. 多模态数据融合

**难点描述**：如何将HRV、体温、运动数据、文本日记等多源异构数据有效融合，形成准确的综合情绪评估。

**解决方案**：
- 时间窗口对齐（统一使用过去7天数据）
- 特征标准化（HRV、体温归一化到0-1区间）
- 加权融合（HRV权重最高，文本数据作为补充验证）

### 2. 危机检测与及时干预

**难点描述**：在对话中及时发现用户的自杀/自残倾向，并进行适当的危机干预。

**挑战**：
- 用户表达隐晦，难以直接识别
- 过度敏感会导致误报，过度保守会漏报
- 干预时需要保持同理心，不能让用户感到被审问

**解决方案**：
- 三级风险分层（crisis → high → medium → low）
- 关键词 + 语义分析双重验证
- 渐进式干预（从确认安全开始，到建议寻求专业帮助）

### 3. Agent人格一致性

**难点描述**：多个Agent（Screenshotport、Knowledge、Interview）需要保持一致的角色设定，同时每个Agent又要有独特的对话风格。

**挑战**：
- 统一的系统提示词难以覆盖所有场景
- LLM生成的回复存在不确定性
- 需要在专业性和亲和力之间取得平衡

**解决方案**：
- 精心设计的prompt模板，包含角色定义、响应规则、示例
- DBT、ACT等心理学框架指导的回复策略
- 输出长度限制（90-140字符）确保简洁

### 4. RAG知识库检索

**难点描述**：KnowledgeAgent需要从知识库中准确检索相关信息，并生成自然的回答。

**技术实现**：
```python
# 语义检索 + 关键词匹配混合策略
retrieval_results = []

# 1. 语义相似度检索（使用all-MiniLM-L6-v2）
if embeddings_available:
    query_embedding = self.embedding_service.get_embedding(query)
    semantic_results = self.knowledge_base.search(query_embedding, top_k=3)

# 2. 关键词匹配兜底
keyword_results = self._keyword_search(query, top_k=3)

# 3. 混合评分
final_results = self._hybrid_merge(semantic_results, keyword_results)
```

### 5. 前端状态管理

**难点描述**：Chat、Interview等场景涉及复杂的状态流转，需要管理WebSocket连接、会话历史、Typing状态等。

**解决方案（Pinia Store）**：
```javascript
// chat store 状态管理
const chatStore = {
  state: {
    messages: [],        // 消息历史
    sessionId: null,    // 会话ID
    isConnected: false,  // WebSocket连接状态
    isInterviewMode: false,  // 访谈模式
    interviewPhase: 0    // 访谈阶段
  },
  actions: {
    connectWebSocket(),  // 建立WebSocket连接
    sendMessage(),       // 发送消息
    setInterviewMode(), // 进入访谈模式
    endInterview()      // 结束访谈
  }
}
```

---

## 数据库设计

### 核心数据模型

```
┌─────────────────┐     ┌─────────────────┐
│      User       │────│  BiometricData  │
│  用户信息        │     │   生理数据       │
├─────────────────┤     ├─────────────────┤
│ id, email,     │     │ id, user_id,   │
│ nickname,      │     │ hrv, temperature│
│ device_id      │     │ motion, timestamp│
└────────┬────────┘     └─────────────────┘
         │
         ├──────────────┬──────────────────┐
         │              │                  │
         ▼              ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ MenstrualRecord │ │    MoodDiary    │ │   Conversation  │
│    月经记录      │  │    情绪日记      │ │     对话记录     │
├─────────────────┤ ├─────────────────┤ ├─────────────────┤
│ id, user_id,    │ │ id, user_id,    │ │ id, session_id, │
│ start_date,     │ │ mood_level,     │ │ role, content,  │
│ cycle_length,   │ │ emotion_tags,   │ │ intent,         │
│ symptoms        │ │ keywords        │ │ sentiment_score │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## API设计

### 情绪分析API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/emotion/predict` | GET | 综合情绪分析（相位、PMS风险、情绪等级） |
| `/emotion/classify` | GET | 实时生理信号情绪分类 |
| `/emotion/phase` | GET | 获取当前月经周期阶段 |
| `/emotion/intervention/recommend` | GET | 获取干预建议 |

### 访谈API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/interview/start` | POST | 开始经前状态了解对话 |
| `/interview/turn` | POST | 继续经前状态了解对话 |
| `/interview/knowledge` | POST | 知识问答 |

---

## 前端架构

### 技术栈

| 层级 | 技术 |
|------|------|
| 框架 | Vue 3 (Composition API) |
| 状态管理 | Pinia |
| 路由 | Vue Router |
| HTTP客户端 | Axios |
| UI构建 | 纯CSS + Tailwind概念 |

### 核心页面

| 页面 | 路由 | 功能 |
|------|------|------|
| 首页 | `/` | 情绪概览、快速入口、状态卡片 |
| 聊天 | `/chat` | AI对话、WebSocket实时通信 |
| 周期 | `/cycle` | 月经记录、周期预测 |
| 音乐 | `/music` | 情绪音乐推荐、播放器 |
| 呼吸 | `/breathing` | 呼吸引导练习 |
| 日记 | `/diary` | 情绪日记记录 |
| 波动 | `/wave` | 生理数据可视化 |

---

## 部署架构

```
                    ┌──────────────────┐
                    │     iOS/Android  │
                    │      Client      │
                    └────────┬─────────┘
                             │ HTTPS
                    ┌────────▼─────────┐
                    │   Nginx/Vite     │
                    │   端口:3000       │
                    └────────┬─────────┘
                             │ Proxy
                    ┌────────▼─────────┐
                    │   FastAPI/Uvicorn│
                    │   端口:8000       │
                    └────────┬─────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   LLM API       │ │   SQLite DB     │ │   Local Music   │
│ (MiniMax/OpenAI)│ │   (healthai.db) │ │   /music        │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## 环境变量配置

```bash
# Backend
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.minimax.chat/v1
MODEL_NAME=MiniMax-M2.7

# Database
DATABASE_URL=sqlite:///./healthai.db

# Security
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

## 关键文件索引

### Backend

| 文件路径 | 功能描述 |
|----------|----------|
| `backend/app/main.py` | FastAPI应用入口 |
| `backend/app/agents/router.py` | Agent路由核心 |
| `backend/app/agents/llm_service.py` | LLM服务封装 |
| `backend/app/agents/support_agent.py` | 日常情绪陪伴Agent |
| `backend/app/agents/intervention_agent.py` | 危机干预Agent |
| `backend/app/agents/interview_agent.py` | 经前状态了解Agent |
| `backend/app/agents/knowledge_agent.py` | RAG知识问答Agent |
| `backend/app/agents/perception_agent.py` | 风险感知Agent |
| `backend/app/services/emotion_engine.py` | 综合情绪分析引擎 |
| `backend/app/services/nlp_service.py` | NLP文本分析服务 |
| `backend/app/services/psst_scoring_service.py` | PSST评分服务 |
| `backend/app/services/cycle_predictor.py` | 周期预测服务 |
| `backend/app/services/embedding_service.py` | 向量化嵌入服务 |
| `backend/app/prompts/*.txt` | Agent系统提示词模板 |

### Frontend

| 文件路径 | 功能描述 |
|----------|----------|
| `frontend/src/views/Home.vue` | 首页 |
| `frontend/src/views/Chat.vue` | AI聊天页 |
| `frontend/src/stores/chat.js` | 聊天状态管理 |
| `frontend/src/stores/health.js` | 健康数据状态管理 |
| `frontend/src/api/index.js` | API客户端封装 |
| `frontend/src/router/index.js` | 路由配置 |

---

## 总结

HealthAI项目展示了如何将**多Agent系统**、**多维度情绪分析**和**心理学干预框架**有机结合，为女性用户提供专业的情绪健康管理服务。项目的技术亮点包括：

1. **智能路由系统**：基于风险分级的动态Agent选择
2. **多模态融合**：整合生理信号、文本日记、对话历史
3. **RAG增强问答**：结合向量检索和LLM生成
4. **自然聊天式状态了解**：借鉴PMS相关问题，但不做正式筛查或诊断
5. **危机干预机制**：及时发现并处理高风险情况

项目的技术难点主要集中在多源数据融合、Agent人格一致性保持、以及危机检测的准确性上，通过精心设计的算法和prompt策略有效解决了这些问题。
---

## 聊天长期记忆与 Agent 模式引导

> 变更日期：2026-05-12  
> 影响范围：`/api/v1/chat/message`、`WS /api/v1/chat/ws/{user_id}`、`AgentService`、`SupportAgent`、`KnowledgeAgent`、`chatStore`  
> 状态：已完成基础接入，仍需在真实用户样本中验证记忆抽取质量与提示语边界。

### 设计目标

聊天系统在保持“危机优先、非诊断、仅供参考”的前提下，新增两类上下文：

| 上下文 | 来源 | 用途 | 风险控制 |
|------|------|------|----------|
| 最近上下文 | 当前 `Conversation` session 的最近消息 | 让模型延续多轮对话，不要求用户重复说明 | 限制轮数与单条长度 |
| 检索上下文 | 当前问题触发的历史 `Conversation` 轻量检索 | 处理“这/它/刚才那个”等指代追问 | 过滤敏感/危机文本，限制检索条数 |
| 长期记忆 | `chat_memories` 表中的用户偏好、情绪特点、经前体验摘要 | 让模型自然参考用户偏好与特点 | 只保存摘要；危机/敏感文本不写入普通记忆 |

### 数据结构

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `user_id` | `int` | - | 记忆所属用户 |
| `category` | `str` | - | `preference`、`premenstrual_trait`、`emotional_trait`、`personal_fact` |
| `key` | `str` | - | 稳定记忆键，如 `music_preference`、`guidance_style` |
| `value` | `text` | - | 最小必要摘要，不保存完整聊天原文 |
| `confidence` | `float` | `0.6` | 规则抽取置信度 |
| `source_conversation_id` | `int?` | `null` | 来源消息 ID |
| `last_seen_at` | `datetime` | 当前时间 | 最近一次被用户表达或更新的时间 |

### Agent 模式侧重点

| 模式 | 侧重点 | 安全边界 |
|------|--------|----------|
| `auto` 自动陪伴 | Router 根据风险、问题类型和用户表达在陪伴/知识间切换 | high/crisis 始终覆盖模式偏好 |
| `support` 情绪宝宝 | 先共情，再结合记忆里的偏好或特点，给一个小问题或一个小行动建议 | 不做诊断，不把记忆说成结论 |
| `knowledge` 知识宝宝 | 优先解释 PMS、周期、情绪波动等知识，可用记忆调整解释角度 | 仅供参考；知识库缺失时说明“暂时没有相关信息” |

### API / WebSocket 字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `memory_state` | `object?` | `null` | 服务端返回的轻量记忆状态 |
| `memory_state.updated` | `bool` | `false` | 本轮是否写入或更新安全记忆 |
| `memory_state.count` | `int` | `0` | 当前用户已保存的记忆条数 |
| `memory_state.categories` | `list[str]` | `[]` | 本轮更新的记忆分类 |
| `memory_state.retrieved_turns` | `int` | `0` | 本轮为 RAG 上下文检索到的历史片段数量 |
| `memory_state.needs_context_resolution` | `bool` | `false` | 当前问题是否疑似依赖“这/它/刚才那个”等上下文指代 |

### 安全注意点

- 检测到自杀、自残、轻生等表达时，聊天记忆服务不会写入普通长期记忆，回复仍由安全路由接管。
- 记忆抽取使用保守规则，只保存“少量建议、一步一步来”“经前常睡不好”等短摘要。
- 对话历史 RAG 使用 `user_id + session_id` 范围内的 `Conversation`，不会跨用户检索；带敏感标记或危机信号的用户消息不进入普通检索片段。
- LLM 调用现在按 `system + 最近/检索到的历史 messages + 当前用户问题` 组织，而不是只把历史塞进 system prompt。
- 前端继续使用 Vue 文本插值渲染消息，不使用 `v-html`。
- 当前 `user_id=1` 仍是开发期兼容写法；真实部署前必须接入 JWT 用户上下文，避免越权读取记忆。
- 记忆抽取暂不改变 `EmotionEngine` 权重；若后续把长期记忆纳入情绪融合算法，需要同步更新权重说明与测试样本。

---

## 聊天 Agent 经期语义承接修复

> 变更日期：2026-05-13  
> 影响范围：`SupportAgent`、`PerceptionAgent`、`AgentService`、`LLMService`、`support_prompt.txt`、`backend/tests/test_p0_safety_and_prompts.py`  
> 状态：已完成后端规则与 prompt 修复；需要在真实对话样本中继续验证语气自然度。

### 设计目标

本次修复针对普通聊天中“难过、想哭、不适、痛经、例假来了、肚子绞痛”等表达的承接质量。系统不把这类表达直接归因为普通情绪波动，而是在非危机场景中优先理解为可能的身体-情绪复合体验：先承接，再轻问身体状态，再给一个低压力、具象的小支持。

该能力仍不等同于 PMS 筛查、医学诊断或心理诊断。所有涉及经前、经期、PMS、痛经、激素波动的回复只作为陪伴和自我观察参考。

### 行为变化

| 场景 | 已完成行为 | 安全边界 |
|------|------------|----------|
| 普通难过 / 想哭 | 先命名和承接感受，再轻问是否与经前、经期或身体状态有关 | 不直接建议专业求助，不诊断 |
| 例假 / 痛经 / 肚子绞痛 | 优先提供热敷、温水、蜷起来休息等具象支持 | 如果疼痛严重、持续或异常，提醒线下就医仅作参考 |
| 焦虑 / 惊慌 | 可提供呼吸放松等稳定动作 | 不把所有难过都急救化 |
| 自杀 / 自残 / 轻生 | 仍由 `PerceptionAgent` + `Router` 强制进入 `InterventionAgent` 或安全兜底 | 不受 `agent_mode`、记忆或经期语义线索覆盖 |
| LLM 标签残留 | 清理 `_chatting_`、`<think>`、`assistant:`、`情绪宝宝：` 等元标签 | 只清洗常见生成残留，避免修改用户语义 |

### 内部状态字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `support_context` | `object` | `{}` | PerceptionAgent 输出的轻量陪伴语境 |
| `support_context.menstrual_related` | `bool` | `false` | 是否可能与经前、经期或身体不适有关 |
| `support_context.body_signals` | `list[str]` | `[]` | `pain`、`bloating`、`fatigue`、`sleep_change`、`appetite` |
| `support_context.emotion_signals` | `list[str]` | `[]` | `sad`、`tearful`、`irritable`、`anxious`、`helpless` |

### 需要验证

- 真实用户对“是不是正好在经前或例假这几天？”这类追问的接受度。
- 不同模型对 `support_prompt.txt` 的执行稳定性，尤其是是否仍会提前输出专业求助。
- 具象支持建议是否需要按用户偏好和禁忌继续个性化。

---

## GLM-5.1 聊天响应加速与推理引擎架构

> 变更日期：2026-05-13  
> 影响范围：`LLMService`、`AgentService`、`/api/v1/chat/message`、`WS /api/v1/chat/ws/{user_id}`、`Chat.vue`、`chatStore`、`VLLM_SETUP.md`  
> 状态：已完成后端 deadline、前端等待阈值和通用 OpenAI-compatible 加速 provider；需要用真实 GLM-5.1 端点压测首包与最终回复耗时。

### 设计目标

GLM-5.1 推理较慢时，MoonCARE 不能让用户长时间停留在“正在组织回复”。本次调整保留 GLM-5.1 的完整推理路径和现有安全路由，同时增加两层控制：

| 层级 | 已完成能力 | 默认值 | 说明 |
|------|------------|--------|------|
| 推理引擎层 | `LLM_PROVIDER=accelerated` | 关闭，需配置启用 | 可指向 vLLM、SGLang、LMDeploy 或内网 OpenAI-compatible GLM 服务 |
| 服务端等待层 | `CHAT_AGENT_REPLY_TIMEOUT_SECONDS` | `18.0` 秒 | Router/LLM 超时后返回安全承接 fallback |
| LLM 请求层 | `LLM_REQUEST_TIMEOUT_SECONDS` | `18.0` 秒 | OpenAI-compatible client 的请求超时 |
| 前端等待层 | `CHAT_REPLY_TIMEOUT_MS` | `22000` 毫秒 | 比后端 deadline 多留网络余量 |

### 加速 provider 配置

| 配置项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `LLM_PROVIDER` | `str` | `nvidia` | 可选 `nvidia`、`openai`、`vllm`、`accelerated` |
| `ACCELERATED_LLM_BASE_URL` | `str` | `http://localhost:30000/v1` | 通用 OpenAI-compatible 推理加速端点 |
| `ACCELERATED_LLM_API_KEY` | `str` | `accelerated-local` | 加速端点鉴权 token |
| `ACCELERATED_LLM_MODEL_NAME` | `str` | `glm-5.1` | 加速端点暴露的模型名 |
| `ACCELERATED_LLM_ENGINE` | `str` | `openai-compatible` | 记录底层引擎类型，仅用于日志和排查 |

### API / WebSocket 新增字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `reply_status` | `str` | `ok` | `ok`、`timeout_fallback`、`error_fallback` |
| `elapsed_ms` | `int` | `0` | 后端本轮 Agent 响应耗时 |

### 安全边界

- 加速 provider 只替换模型服务端点，不绕过 `PerceptionAgent` 和 `Router`。
- 普通消息超时后返回温柔承接 fallback，提示用户可重试，不冒充 GLM 完整回复。
- 自杀、自残、轻生等危机表达超时后返回安全兜底，优先确认安全和寻求可信任的人帮助。
- 后续如接入 streaming 或异步“完整回复补发”，仍必须保留危机优先和非诊断边界。
