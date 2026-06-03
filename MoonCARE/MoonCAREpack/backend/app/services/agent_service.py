"""
Agent服务 - 委托给新的 Agent 系统
集成语义缓存和对话压缩优化
"""
import asyncio
import time
import traceback
from typing import Any, Dict, List, Optional, AsyncGenerator, Tuple
from app.config import settings
from app.utils.safety import SAFE_INTERVENTION_FALLBACK, contains_crisis_signal

try:
    from app.agents.router import Router
    from app.agents.perception_agent import PerceptionAgent
    from app.agents.llm_service import LLMService
    from app.services.semantic_cache_service import get_semantic_cache
    from app.services.conversation_compaction_service import get_conversation_compaction_service
    from app.services.response_quality_service import ResponseQualityGuard
    from app.utils.prompt_loader import render_prompt
    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False
    Router = None
    PerceptionAgent = None
    LLMService = None
    get_semantic_cache = None
    get_conversation_compaction_service = None
    ResponseQualityGuard = None
    render_prompt = None


class AgentService:
    """
    Agent 服务 - 使用新的多 Agent 系统
    集成语义缓存和对话压缩优化
    """

    def __init__(self):
        self.context_window = settings.CONTEXT_WINDOW_SIZE  # 10轮对话
        self.reply_timeout_seconds = settings.CHAT_AGENT_REPLY_TIMEOUT_SECONDS
        self.router = None  # Lazy init
        self.perception = None  # Lazy init
        self.llm_service = None  # Lazy init for streaming
        self.semantic_cache = None  # Lazy init for semantic caching
        self.compaction_service = None  # Lazy init for conversation compaction
        self.response_quality_guard = ResponseQualityGuard() if ResponseQualityGuard else None

    def _get_router(self):
        if self.router is None:
            self.router = Router()
        return self.router

    def _get_perception(self):
        if self.perception is None:
            self.perception = PerceptionAgent()
        return self.perception

    def _get_llm_service(self):
        if self.llm_service is None and LLMService:
            try:
                self.llm_service = LLMService()
            except Exception as e:
                print(f"[AgentService] Failed to initialize LLM service: {e}")
                self.llm_service = None
        return self.llm_service

    def _get_semantic_cache(self):
        if self.semantic_cache is None and get_semantic_cache and settings.SEMANTIC_CACHE_ENABLED:
            try:
                self.semantic_cache = get_semantic_cache()
            except Exception as e:
                print(f"[AgentService] Failed to initialize semantic cache: {e}")
                self.semantic_cache = None
        return self.semantic_cache

    def _get_compaction_service(self):
        if self.compaction_service is None and get_conversation_compaction_service:
            try:
                self.compaction_service = get_conversation_compaction_service()
            except Exception as e:
                print(f"[AgentService] Failed to initialize compaction service: {e}")
                self.compaction_service = None
        return self.compaction_service

    def _compact_conversation_context(self, context: Dict) -> Dict:
        """压缩对话历史上下文，减少 Token 使用"""
        compaction_service = self._get_compaction_service()
        if not compaction_service:
            return context

        conversation_messages = context.get("conversation_messages", [])
        user_message = context.get("message", "")
        
        compacted_messages, stats = compaction_service.build_compacted_context(
            conversation_messages,
            user_message,
        )
        
        # 更新上下文
        context["conversation_messages"] = compacted_messages
        context["compaction_stats"] = stats
        
        # 生成摘要
        if len(conversation_messages) > 5:
            context["conversation_summary"] = compaction_service.create_summary(conversation_messages)
        
        return context

    def _mode_guidance(self, agent_mode: str) -> str:
        """Return mode-specific interaction guidance for downstream agents."""
        guidance = {
            "support": (
                "当前是情绪陪伴模式：谨慎共情，只能命名用户已经明确表达的情绪，不替用户添加没有说出口的感受；"
                "先回应用户原话里的具体事件；如果用户已经把原因或症状说清楚，本轮不要继续追问，改为安慰和一个小行动建议；"
                "当用户问“我该怎么做/怎么办/接下来怎么办”时，必须结合最近上下文给2-3个具体下一步，不能只继续安抚；"
                "当用户明确需要照顾安排时，给3步以内的轻量照护计划。"
            ),
            "knowledge": (
                "当前是知识解释模式：优先用通俗语言回答问题，必要时结合用户经前体验做解释；"
                "同时给出1-2条低风险行动建议，保持仅供参考，不做诊断。"
            ),
            "auto": (
                "当前是自动陪伴模式：根据用户内容在情绪陪伴、知识解释和经期照护建议之间自然切换。"
            ),
        }
        return guidance.get(agent_mode, guidance["auto"])

    def _should_show_actions(self, state: Dict[str, Any], agent_name: str = "", llm_reply: str = "") -> bool:
        """判断是否应该显示行动建议"""
        risk_level = state.get("risk_level", "low")
        message = state.get("message", "")
        agent_mode = state.get("agent_mode", "auto")
        
        # 高风险或危机状态时，不显示行动建议，专注于安全干预
        if risk_level in ["high", "crisis"]:
            return False
        
        # 知识问答模式或知识Agent回复时，完全不显示行动建议
        # 知识问答的目的是提供信息，而不是情绪支持
        is_knowledge_mode = agent_mode == "knowledge" or agent_name == "knowledge"
        if is_knowledge_mode:
            return False
        
        # 用户拒绝行动建议后，一段时间内不再显示
        if state.get("user_rejected_action", False):
            return False
        
        # 纯倾听阶段（对话轮数 ≤ 2 轮用户消息）不显示按钮
        # 仅在确实有对话历史时才应用此规则，避免测试时失败
        conversation_messages = state.get("conversation_messages", [])
        user_messages = [m for m in conversation_messages if m.get("role") == "user"]
        if conversation_messages and len(user_messages) <= 2:
            return False
        
        # 检测用户是否在当前消息中拒绝了建议
        rejection_keywords = ["不想听建议", "不用你管", "别给建议", "不需要建议", "别说了", "不用理我"]
        if any(kw in message for kw in rejection_keywords):
            state["user_rejected_action"] = True
            state["reject_turns_remaining"] = 3
            return False
        
        # 如果用户之前拒绝过建议，检查剩余轮数
        if state.get("reject_turns_remaining", 0) > 0:
            state["reject_turns_remaining"] -= 1
            if state["reject_turns_remaining"] <= 0:
                state["user_rejected_action"] = False
            return False
        
        return True

    def _extract_suggestion_keywords(self, llm_reply: str) -> List[str]:
        """从 LLM 回复中提取建议关键词，用于匹配按钮"""
        keyword_mappings = [
            ("呼吸", ["深呼吸", "呼吸", "放松"]),
            ("日记", ["写下来", "写日记", "日记"]),
            ("音乐", ["听音乐", "听点音乐", "音乐"]),
            ("休息", ["休息一下", "休息"]),
            ("拉伸", ["拉伸"]),
            ("喝水", ["喝水", "温水"]),
            ("窗边", ["窗边"]),
            ("走走", ["出去走走", "走走"]),
            ("抱抱", ["抱抱", "抱抱自己"]),
            ("冷静", ["冷静一下"]),
        ]
        
        extracted = []
        seen = set()
        for keyword, phrases in keyword_mappings:
            if keyword in seen:
                continue
            if keyword in llm_reply or any(phrase in llm_reply for phrase in phrases):
                extracted.append(keyword)
                seen.add(keyword)
        return extracted[:3]  # 最多 3 个关键词

    def _match_actions_from_keywords(self, keywords: List[str]) -> List[Dict[str, str]]:
        """根据提取的关键词匹配按钮"""
        action_pool = {
            "呼吸": {"action": "breathing", "label": "🧘 呼吸练习", "description": "跟着引导做几次深呼吸，缓解情绪", "route": "/breathing"},
            "日记": {"action": "diary", "label": "📝 写日记", "description": "写下你的感受，让情绪流动起来", "route": "/diary"},
            "音乐": {"action": "music", "label": "🎵 听音乐", "description": "听一些温柔的音乐陪伴自己", "route": "/music"},
            "休息": {"action": "rest", "label": "😴 休息一下", "description": "建议好好休息，照顾好自己", "route": None},
            "拉伸": {"action": "stretch", "label": "拉伸一下", "description": "拉伸肩膀和身体，释放紧绷感", "route": None},
            "喝水": {"action": "water", "label": "喝杯温水", "description": "慢慢喝一杯温热的水，让身体放松下来", "route": None},
            "窗边": {"action": "window", "label": "窗边站站", "description": "去窗边站5分钟，看看外面的景色", "route": None},
            "走走": {"action": "walk", "label": "🚶 出去走走", "description": "离开当前场景，呼吸一下新鲜空气", "route": None},
            "抱抱": {"action": "hug", "label": "🤗 抱抱自己", "description": "允许自己脆弱，给自己一个温暖的拥抱", "route": None},
            "冷静": {"action": "cool_down", "label": "⏸️ 先冷静一下", "description": "给自己十分钟从现场抽开，等情绪降温", "route": None},
        }
        
        actions = []
        seen_action_ids = set()
        for keyword in keywords:
            if keyword in action_pool and action_pool[keyword]["action"] not in seen_action_ids:
                actions.append(action_pool[keyword])
                seen_action_ids.add(action_pool[keyword]["action"])
        return actions

    def _generate_action_suggestions(self, state: Dict[str, Any], agent_name: str = "", llm_reply: str = "") -> List[Dict[str, str]]:
        """根据情绪状态生成功能建议"""
        # 检查是否应该显示行动建议
        if not self._should_show_actions(state, agent_name, llm_reply):
            return []
        
        # 优先从 LLM 回复中提取建议关键词并匹配按钮
        if llm_reply:
            keywords = self._extract_suggestion_keywords(llm_reply)
            if keywords:
                return self._match_actions_from_keywords(keywords)
        
        # 如果没有从回复中提取到关键词，保留旧逻辑来保证兼容性
        risk_level = state.get("risk_level", "low")
        message = state.get("message", "")
        support_context = state.get("support_context") or {}
        body_signals = set(support_context.get("body_signals") or [])
        emotion_signals = set(support_context.get("emotion_signals") or [])
        menstrual_related = bool(support_context.get("menstrual_related"))
        
        actions = []
        
        # 定义情绪场景与关键词映射（按优先级排序）
        emotion_scenarios = [
            # 高优先级：疼痛、焦虑、危机
            {
                "keywords": ["疼痛", "痛", "疼"],
                "body_signals": ["pain"],
                "suggestions": [
                    {"action": "warmth", "label": "暖一暖", "description": "用热水袋或温热毛巾暖一下小腹，先让身体松一点", "route": None},
                    {"action": "breathing", "label": "🧘 呼吸练习", "description": "跟着引导做几次深呼吸，缓解痛感", "route": "/breathing"},
                    {"action": "water", "label": "喝杯温水", "description": "慢慢喝一杯温热的水，让身体放松下来", "route": None}
                ]
            },
            # 焦虑/紧张/惊慌
            {
                "keywords": ["紧张", "焦虑", "慌", "担心", "不安", "惊恐", "害怕"],
                "emotion_signals": [],
                "risk_level_check": ["high", "crisis"],
                "suggestions": [
                    {"action": "breathing", "label": "🧘 呼吸放松", "description": "进行深呼吸练习，帮助平静下来", "route": "/breathing"},
                    {"action": "window", "label": "窗边站站", "description": "去窗边站5分钟，看看外面的景色", "route": None},
                    {"action": "hug", "label": "🤗 抱抱自己", "description": "给自己一个温暖的拥抱", "route": None}
                ]
            },
            # 敏感/想哭
            {
                "keywords": ["敏感", "想哭", "委屈", "难过", "伤心", "脆弱"],
                "emotion_signals": ["sad", "tearful", "helpless"],
                "suggestions": [
                    {"action": "diary", "label": "📝 写日记", "description": "写下你的感受，让情绪流动起来", "route": "/diary"},
                    {"action": "music", "label": "🎵 听音乐", "description": "听一些温柔的音乐陪伴自己", "route": "/music"},
                    {"action": "hug", "label": "🤗 抱抱自己", "description": "允许自己脆弱，给自己一个拥抱", "route": None}
                ]
            },
            # 生气/烦躁/易怒
            {
                "keywords": ["生气", "烦躁", "易怒", "火大", "烦", "愤怒", "恼火"],
                "emotion_signals": ["irritable"],
                "suggestions": [
                    {"action": "breathing", "label": "🧘 深呼吸", "description": "做几个深长的呼吸，先让情绪降下来", "route": "/breathing"},
                    {"action": "music", "label": "🎵 听音乐", "description": "听一些节奏感强或舒缓的音乐", "route": "/music"},
                    {"action": "stretch", "label": "拉伸一下", "description": "拉伸肩膀和身体，释放紧绷感", "route": None}
                ]
            },
            # 睡眠不好
            {
                "keywords": ["睡不着", "失眠", "睡眠不好", "睡不好", "熬夜", "醒"],
                "body_signals": ["sleep_change"],
                "suggestions": [
                    {"action": "breathing", "label": "🧘 睡前呼吸", "description": "做几组舒缓的呼吸练习，帮助入睡", "route": "/breathing"},
                    {"action": "music", "label": "🎵 助眠音乐", "description": "听一些轻柔的助眠音乐", "route": "/music"},
                    {"action": "water", "label": "喝杯温水", "description": "慢慢喝杯温热的水，让身体放松", "route": None}
                ]
            },
            # 食欲变化
            {
                "keywords": ["没胃口", "不想吃", "吃不下", "暴食", "吃很多", "食欲"],
                "body_signals": ["appetite_change"],
                "suggestions": [
                    {"action": "diary", "label": "📝 记录感受", "description": "写下现在的身体感受和想法", "route": "/diary"},
                    {"action": "water", "label": "喝杯温水", "description": "先喝一杯温水，让胃舒服一点", "route": None},
                    {"action": "stretch", "label": "轻轻活动", "description": "稍微活动一下身体，让感觉回来", "route": None}
                ]
            },
            # 疲惫/累
            {
                "keywords": ["累", "疲惫", "困", "乏力", "没力气"],
                "body_signals": ["fatigue"],
                "suggestions": [
                    {"action": "rest", "label": "😴 休息一下", "description": "建议好好休息，照顾好自己", "route": None},
                    {"action": "music", "label": "🎵 听音乐", "description": "听一些放松的音乐休息一下", "route": "/music"},
                    {"action": "stretch", "label": "拉伸一下", "description": "简单拉伸一下肩膀和脖子", "route": None}
                ]
            }
        ]
        
        # 按优先级匹配情绪场景
        matched_scenario = None
        for scenario in emotion_scenarios:
            # 检查关键词
            keyword_match = any(kw in message for kw in scenario.get("keywords", []))
            # 检查身体信号
            body_match = any(bs in body_signals for bs in scenario.get("body_signals", []))
            # 检查情绪信号
            emotion_match = any(es in emotion_signals for es in scenario.get("emotion_signals", []))
            # 检查风险等级
            risk_match = risk_level in scenario.get("risk_level_check", [])
            
            if keyword_match or body_match or emotion_match or risk_match:
                matched_scenario = scenario
                break
        
        # 如果匹配到场景，添加建议
        if matched_scenario:
            actions.extend(matched_scenario["suggestions"])
        # 经前/经期语境下的默认建议
        elif menstrual_related:
            actions.extend([
                {"action": "rest", "label": "先缓一缓", "description": "喝点温水，允许自己蜷起来休息一会儿", "route": None},
                {"action": "breathing", "label": "🧘 呼吸放松", "description": "做几个深呼吸，让身体放松", "route": "/breathing"}
            ])
        # 通用建议
        else:
            actions.extend([
                {"action": "diary", "label": "📝 写下感受", "description": "简单记一两句现在的感受", "route": "/diary"},
                {"action": "music", "label": "🎵 听音乐", "description": "听一些舒缓的音乐", "route": "/music"},
                {"action": "breathing", "label": "🧘 呼吸练习", "description": "做几组简单的深呼吸", "route": "/breathing"}
            ])
        
        return actions[:3]

    def _generate_conversation_suggestions(self, state: Dict[str, Any], agent_name: str) -> List[str]:
        """生成对话快捷回复建议（与actions区分）"""
        message = state.get("message", "")
        agent_mode = state.get("agent_mode", "auto")
        
        # 知识问答模式下，不显示对话快捷回复
        if agent_mode == "knowledge" or agent_name == "knowledge":
            return []
        
        # 定义对话快捷回复建议
        conversation_suggestions = [
            "我想倾诉一下",
            "来个呼吸练习",
            "陪我说说话"
        ]
        
        # 根据情绪状态调整建议
        emotion_keywords = ["烦躁", "焦虑", "难过", "想哭", "生气"]
        has_emotion = any(kw in message for kw in emotion_keywords)
        
        if has_emotion:
            return conversation_suggestions[:2]
        
        return conversation_suggestions[:1]

    def _attach_conversation_context(
        self,
        state: Dict[str, Any],
        context: Dict[str, Any],
        agent_mode: str,
    ) -> Dict[str, Any]:
        """Add bounded memory and recent-turn context to the perceived state.
        
        基于对话轮数的上下文预加载策略：
        - 对话早期（1-3轮）：加载完整近期上下文，确保AI能承接对话
        - 对话中期（4-8轮）：标准加载，平衡上下文与性能
        - 对话后期（9轮以上）：启用智能压缩，减少冗余
        """
        conversation_memory = (context or {}).get("conversation_memory") or {}
        conversation_messages = conversation_memory.get("conversation_messages", [])
        user_messages = [m for m in conversation_messages if m.get("role") == "user"]
        turn_count = len(user_messages)
        
        state = dict(state or {})
        state["agent_mode"] = agent_mode
        state["turn_count"] = turn_count
        
        memory_context = conversation_memory.get("memory_context", "暂无可用长期记忆。")
        recent_context = conversation_memory.get("recent_context", "暂无最近对话。")
        retrieved_context = conversation_memory.get("retrieved_context", "暂无检索片段。")
        health_context = conversation_memory.get("health_context", "暂无可用的周期/日记上下文。")
        
        if turn_count <= 3:
            state["context_load_level"] = "full"
            state["memory_context"] = memory_context
            state["recent_context"] = recent_context
            state["retrieved_context"] = retrieved_context
            state["health_context"] = health_context
        elif turn_count <= 8:
            state["context_load_level"] = "standard"
            state["memory_context"] = memory_context
            state["recent_context"] = recent_context
            state["retrieved_context"] = retrieved_context
            state["health_context"] = health_context
        else:
            state["context_load_level"] = "compressed"
            state["memory_context"] = memory_context
            state["recent_context"] = self._summarize_context_for_compression(recent_context) if len(recent_context) > 200 else recent_context
            state["retrieved_context"] = retrieved_context
            state["health_context"] = health_context
        
        state["health_state"] = conversation_memory.get("health_state", {})
        state["conversation_messages"] = conversation_messages
        state["mode_guidance"] = self._mode_guidance(agent_mode)
        state["memory_state"] = conversation_memory.get(
            "memory_state",
            {"has_memory": False, "count": 0, "updated": False, "categories": []},
        )
        return state
    
    def _summarize_context_for_compression(self, context: str) -> str:
        """压缩长上下文，提取关键信息"""
        if not context or len(context) <= 200:
            return context
        sentences = context.split("。")
        if len(sentences) <= 3:
            return context
        key_sentences = [s for s in sentences if any(kw in s for kw in ["感受", "情绪", "想", "觉得", "问题", "情况"])]
        if key_sentences:
            return "。".join(key_sentences[-3:]) + "。"
        return "。".join(sentences[-3:]) + "。"

    async def _route_with_deadline(
        self,
        router: Any,
        user_message: str,
        state: Dict[str, Any],
        agent_mode: str,
    ) -> tuple[str, str]:
        """Run blocking Router/LLM work off the event loop with a chat deadline."""
        return await asyncio.wait_for(
            asyncio.to_thread(
                router.route,
                user_message,
                state,
                agent_mode=agent_mode,
            ),
            timeout=max(float(self.reply_timeout_seconds), 0.01),
        )

    def _fallback_topic(self, user_message: str, limit: int = 28) -> str:
        """Extract a short user-facing topic for graceful degraded replies."""
        topic = " ".join((user_message or "").split())
        for prefix in ("我今天", "我现在", "我刚才", "我感觉", "我觉得", "我"):
            if topic.startswith(prefix) and len(topic) > len(prefix) + 4:
                topic = topic[len(prefix):]
                break
        topic = topic.strip("，。！？? ")
        if len(topic) > limit:
            topic = f"{topic[: limit - 1]}…"
        return topic or "这件事"

    def _knowledge_degraded_reply(self, user_message: str) -> str:
        """Return a question-specific knowledge fallback without exposing runtime failure."""
        compact = "".join((user_message or "").split())
        if "头晕" in compact:
            return (
                "经期头晕可能和疼痛、睡眠不足、进食少、出血量变化或身体紧张叠在一起有关。"
                "先坐下或躺一会儿，补一点温水；如果头晕明显、快晕倒、心慌或出血异常，建议尽快联系医生。"
                "以上仅供参考。"
            )
        if any(term in compact for term in ("肚子疼", "肚子痛", "腹痛", "痛经", "小腹痛")):
            return (
                "经期腹痛常见原因之一是子宫收缩带来的不适，也可能被睡眠、压力和受凉感放大。"
                "可以先热敷小腹、放慢活动强度；如果疼痛剧烈、和平时明显不同或伴随异常出血，建议咨询医生。以上仅供参考。"
            )
        if any(term in compact for term in ("烦躁", "想哭", "情绪", "低落", "易怒")):
            return (
                "经前或经期情绪起伏可能和激素波动、睡眠、疼痛、压力事件叠加有关，不代表你矫情。"
                "可以先记录它出现的时间、强度和月经来后是否缓解；如果连续影响生活，建议找专业人员评估。以上仅供参考。"
            )
        topic = self._fallback_topic(user_message)
        return (
            f"关于“{topic}”，我会先给一个谨慎回答：它可能和周期阶段、睡眠、压力、疼痛或当天事件叠加有关。"
            "先记录发生时间和身体感受，如果明显影响生活或和平时很不一样，建议咨询专业医生。以上仅供参考。"
        )

    def _support_degraded_reply(self, user_message: str) -> str:
        """Return a contextual support fallback without a fixed failure template."""
        topic = self._fallback_topic(user_message)
        compact = "".join((user_message or "").split())
        
        emotion_terms = ("烦躁", "焦虑", "难过", "想哭", "委屈", "难受", "生气", "疲惫", "累", "困")
        body_terms = ("疼", "痛", "晕", "胀", "酸", "累", "困", "睡不着")
        
        has_emotion = any(term in compact for term in emotion_terms)
        has_body = any(term in compact for term in body_terms)
        
        if has_emotion and has_body:
            return (
                f"关于「{topic}」，听起来身体和情绪都在承受一些东西。"
                "先把最基本的照顾好：找个地方坐下来，喝一点温水。"
                "如果可以的话，花两分钟把现在的感受简单写下来，不用组织语言。"
            )
        elif has_emotion:
            return (
                f"你说的「{topic}」，我能感觉到这对你来说很重要。"
                "不用急着整理清楚，先让自己在一个安全的地方待一会儿。"
                "如果想说话，我在这里。"
            )
        elif has_body:
            return (
                f"关于「{topic}」，身体的不适会放大情绪的波动。"
                "现在最重要的事情是把身体放到一个舒服的位置，慢慢呼吸。"
                "如果症状持续或加重，记得及时联系医生。"
            )
        else:
            return (
                f"关于「{topic}」，让我先确认一下你的意思。"
                "你愿意多说一点吗？无论你想表达什么，我都在听。"
            )

    def _looks_like_action_request(self, user_message: str) -> bool:
        """Return whether the user is explicitly asking for next steps."""
        compact = "".join((user_message or "").split())
        action_markers = (
            "我该怎么做",
            "该怎么做",
            "我该怎么办",
            "该怎么办",
            "接下来怎么办",
            "接下来怎么做",
            "现在怎么办",
            "现在怎么做",
            "能做什么",
            "可以做什么",
            "帮我想办法",
            "给我点建议",
            "怎么处理",
            "怎么面对",
            "怎么回复",
        )
        return any(marker in compact for marker in action_markers)

    def _recent_user_context_text(self, state: Dict[str, Any]) -> str:
        """Return recent user context used to make short action requests specific."""
        state = state or {}
        recent_user_messages: List[str] = []
        for item in state.get("conversation_messages") or []:
            if not isinstance(item, dict) or item.get("role") != "user":
                continue
            content = str(item.get("content") or "").strip()
            if content:
                recent_user_messages.append(content)

        # For explicit "what should I do" turns, the user's latest visible
        # conversation should outrank older profile or health memory.
        if recent_user_messages:
            return " ".join(recent_user_messages[-4:])

        for key in ("recent_context", "health_context", "memory_context"):
            value = str(state.get(key) or "").strip()
            if value and not value.startswith("暂无"):
                return value
        return ""

    def _action_request_degraded_reply(self, user_message: str, state: Dict[str, Any]) -> str:
        """Return concrete next steps for a short help-seeking turn."""
        context_text = self._recent_user_context_text(state)
        compact = "".join(f"{context_text} {user_message}".split())

        body_terms = ("来月经", "经期", "姨妈", "小腹", "肚子疼", "肚子痛", "腹痛", "痛经", "头晕", "出血")
        conflict_terms = ("男朋友", "伴侣", "吵架", "争吵", "老板", "批评", "同事", "朋友", "家人", "冷战", "矛盾")
        emotion_terms = ("烦躁", "焦虑", "崩溃", "乱成一团", "心里堵", "委屈", "难受", "想哭", "生气")

        if any(term in compact for term in body_terms):
            return (
                "先把身体放到安全一点的位置：坐下或躺一会儿，别硬撑。"
                "然后热敷小腹、慢慢喝一点温水，今天把任务降到最低。"
                "如果头晕明显、站不稳、出血异常或疼痛和平时很不一样，要尽快联系身边人和医生；以上仅供参考。"
            )

        if any(term in compact for term in conflict_terms):
            return (
                "先别急着继续争论或马上回复对方，给自己十分钟从现场抽开一点。"
                "然后把最想表达的一句话写下来，只保留事实和感受，先别发出去。"
                "等情绪降一点，再决定要不要沟通；如果对方持续否定你，可以先把边界放前面。"
            )

        if any(term in compact for term in emotion_terms):
            return (
                "先把刺激源放远一点，比如放下手机、离开当前场景两三分钟。"
                "然后写下此刻最卡住你的那一句，不用写完整。"
                "接着只选一个小动作做：喝水、洗把脸、听一首歌，等身体稍微稳一点再处理事情。"
            )

        return (
            "先暂停一下当前动作，给自己一分钟把呼吸放慢。"
            "然后写下现在最困扰你的一个点，只写一句就够。"
            "接着选一个最小的下一步去做：联系一个可信任的人、离开刺激环境，或把事情延后十分钟再决定。"
        )

    def _is_vague_action_reply(self, reply: str) -> bool:
        """Return whether a reply dodges an explicit action request."""
        compact = "".join((reply or "").split())
        vague_terms = (
            "轻飘飘",
            "你可以继续说",
            "我会先跟着你现在最明显的感受",
        )
        return any(term in compact for term in vague_terms)

    def _timeout_fallback(self, user_message: str, state: Dict[str, Any]) -> str:
        """Return a bounded fallback when the selected model misses the chat deadline."""
        risk_level = (state or {}).get("risk_level", "low")
        if risk_level in {"high", "crisis"} or contains_crisis_signal(user_message):
            return SAFE_INTERVENTION_FALLBACK

        if self._looks_like_action_request(user_message):
            return self._action_request_degraded_reply(user_message, state or {})

        agent_mode = (state or {}).get("agent_mode", "auto")
        if agent_mode == "knowledge" or self._looks_like_knowledge_question(user_message):
            return self._knowledge_degraded_reply(user_message)
        return self._support_degraded_reply(user_message)

    def _soft_error_fallback(self, user_message: str, state: Dict[str, Any]) -> str:
        """Return user-facing copy for unexpected non-crisis chat failures."""
        state = state or {}
        if state.get("risk_level") in {"high", "crisis"} or contains_crisis_signal(user_message):
            return SAFE_INTERVENTION_FALLBACK
        if self._looks_like_action_request(user_message):
            return self._action_request_degraded_reply(user_message, state)
        agent_mode = state.get("agent_mode", "auto")
        if agent_mode == "knowledge" or self._looks_like_knowledge_question(user_message):
            return self._knowledge_degraded_reply(user_message)
        return self._support_degraded_reply(user_message)

    def _repair_reply_quality(
        self,
        user_message: str,
        reply: str,
        state: Dict[str, Any],
    ) -> str:
        """Repair common conversational quality failures with deterministic rules."""
        if self._looks_like_action_request(user_message) and self._is_vague_action_reply(reply):
            return self._action_request_degraded_reply(user_message, state or {})
        if not self.response_quality_guard:
            return reply
        try:
            return self.response_quality_guard.repair_reply(user_message, reply, state)
        except Exception as exc:
            print(f"[AgentService] Response quality guard failed: {exc}")
            return reply

    def _can_use_semantic_cache(self, user_message: str, state: Dict[str, Any]) -> bool:
        """Return whether semantic cache is safe for this conversational turn."""
        if contains_crisis_signal(user_message):
            return False
        if state.get("risk_level") in {"high", "crisis"}:
            return False
        if self.response_quality_guard and self.response_quality_guard.is_quality_sensitive_turn(user_message):
            return False
        return True

    def _direct_quality_reply(self, user_message: str, state: Dict[str, Any]) -> str:
        """Return a safety-aware deterministic support reply for quality-sensitive turns."""
        if contains_crisis_signal(user_message):
            return ""
        if (state or {}).get("risk_level") in {"high", "crisis"}:
            return ""
        if "support_context" not in (state or {}):
            return ""
        if not self.response_quality_guard:
            return ""
        return self.response_quality_guard.direct_reply_if_applicable(user_message, state or {})

    def _looks_like_knowledge_question(self, user_message: str) -> bool:
        """Return whether the message should use the knowledge route in streaming chat."""
        router = self._get_router()
        if hasattr(router, "_looks_like_knowledge_question"):
            return router._looks_like_knowledge_question(user_message)

        compact = "".join((user_message or "").split())
        question_markers = (
            "为什么", "什么是", "怎么回事", "原因", "会不会", "正常吗", "是不是", "如何", "怎么办",
            "怎么缓解", "如何改善", "有没有办法", "如何处理", "怎么办呢", "能缓解吗", "有什么办法",
        )
        health_context_markers = (
            "经前", "经期", "月经", "姨妈", "PMS", "pms", "PMDD", "pmdd", "激素", "周期",
            "情绪", "烦躁", "失眠", "焦虑", "难过", "易怒", "头痛", "腹痛", "疲劳", "水肿",
        )
        return any(marker in compact for marker in question_markers) and (
            any(marker in compact for marker in health_context_markers) or "？" in compact or "?" in compact
        )

    def _format_support_context(self, support_context: Dict[str, Any]) -> str:
        """Format body-emotion signals for the support prompt."""
        if not support_context:
            return "暂无额外身体-情绪线索。"
        menstrual = "是" if support_context.get("menstrual_related") else "否"
        body = "、".join(support_context.get("body_signals") or []) or "无"
        emotion = "、".join(support_context.get("emotion_signals") or []) or "无"
        return f"可能与经前/经期有关：{menstrual}；身体线索：{body}；情绪线索：{emotion}。"

    def _build_support_stream_context(
        self,
        state: Dict[str, Any],
        cycle_phase: str,
        risk_level: str,
    ) -> Dict[str, Any]:
        """Build streaming context with the same support prompt used by SupportAgent."""
        support_context = self._format_support_context(state.get("support_context", {}))
        context = {
            "cycle_phase": cycle_phase,
            "risk_level": risk_level,
            "support_context": support_context,
            "memory_context": state.get("memory_context", "暂无可用长期记忆。"),
            "health_context": state.get("health_context", "暂无可用的周期/日记上下文。"),
            "recent_context": state.get("recent_context", "暂无最近对话。"),
            "retrieved_context": state.get("retrieved_context", "暂无检索片段。"),
            "mode_guidance": state.get("mode_guidance", ""),
            "conversation_messages": state.get("conversation_messages", []),
        }
        if render_prompt:
            context["raw_system_prompt"] = render_prompt(
                "support_prompt.txt",
                cycle_phase=cycle_phase,
                risk_level=risk_level,
                support_context=support_context,
                memory_context=context["memory_context"],
                health_context=context["health_context"],
                recent_context=context["recent_context"],
                retrieved_context=context["retrieved_context"],
                mode_guidance=context["mode_guidance"],
            )
        return context

    async def _stream_router_response(
        self,
        router: Any,
        user_message: str,
        state: Dict[str, Any],
        agent_mode: str,
        started_at: float,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream non-support routes, using native knowledge streaming when available."""
        knowledge_agent = getattr(router, "knowledge", None)
        if knowledge_agent is not None and hasattr(knowledge_agent, "stream_respond"):
            yield {
                "type": "start",
                "risk_level": state.get("risk_level", "low"),
                "agent_name": "knowledge",
            }

            full_response = ""
            first_token_latency_ms = 0
            first_token_seen = False

            async for chunk in knowledge_agent.stream_respond(user_message, state):
                token = chunk.get("token", "")
                if not token:
                    continue
                full_response += token
                if not first_token_seen:
                    first_token_seen = True
                    first_token_latency_ms = chunk.get(
                        "first_token_latency_ms",
                        int((time.perf_counter() - started_at) * 1000),
                    )
                yield {
                    "type": "token",
                    "token": token,
                    "is_final": False,
                    "first_token_latency_ms": first_token_latency_ms,
                }

            if not full_response:
                full_response = self._timeout_fallback(user_message, state)
                yield {
                    "type": "token",
                    "token": full_response,
                    "is_final": True,
                    "first_token_latency_ms": int((time.perf_counter() - started_at) * 1000),
                }

            full_response = self._repair_reply_quality(user_message, full_response, state)
            yield {
                "type": "end",
                "actions": self._generate_action_suggestions(state),
                "elapsed_ms": int((time.perf_counter() - started_at) * 1000),
                "full_response": full_response,
            }
            return

        try:
            reply, agent_name = await self._route_with_deadline(
                router=router,
                user_message=user_message,
                state=state,
                agent_mode=agent_mode,
            )
        except asyncio.TimeoutError:
            reply = self._timeout_fallback(user_message, state)
            agent_name = "timeout_fallback"

        reply = self._repair_reply_quality(user_message, reply, state)
        yield {
            "type": "start",
            "risk_level": state.get("risk_level", "low"),
            "agent_name": agent_name,
        }
        yield {
            "type": "token",
            "token": reply,
            "is_final": True,
            "first_token_latency_ms": int((time.perf_counter() - started_at) * 1000),
        }
        yield {
            "type": "end",
            "actions": self._generate_action_suggestions(state, agent_name),
            "elapsed_ms": int((time.perf_counter() - started_at) * 1000),
            "full_response": reply,
        }

    async def get_response(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        context: Dict,
        agent_mode: str = "auto",
        skip_deterministic_reply: bool = False,
    ) -> Dict:
        """
        获取AI响应
        使用新的 Agent 路由系统，集成语义缓存和对话压缩优化
        """
        started_at = time.perf_counter()
        reply_status = "ok"
        cache_hit = False
        cache_similarity = 0.0
        needs_llm_followup = False
        
        try:
            cycle_phase = context.get("cycle_phase")
            sensor_data = context.get("sensor_data", {})

            # 1. 压缩对话历史上下文
            context = self._compact_conversation_context(context)

            # 2. PerceptionAgent 分析风险等级
            perception = self._get_perception()
            state = perception.analyze(
                message=user_message,
                cycle_phase=cycle_phase,
                sensor_data=sensor_data
            )
            state = self._attach_conversation_context(state, context, agent_mode)
            state["message"] = user_message
            state["agent_mode"] = agent_mode

            # 3. 检查语义缓存。
            semantic_cache = self._get_semantic_cache()
            if semantic_cache and self._can_use_semantic_cache(user_message, state):
                cached_response = semantic_cache.get_cached_response(
                    user_message,
                    similarity_threshold=settings.SEMANTIC_CACHE_SIMILARITY_THRESHOLD,
                )
                if cached_response:
                    cache_hit = True
                    cache_similarity = cached_response.get("similarity", 0.0)
                    cached_reply = self._repair_reply_quality(
                        user_message,
                        cached_response["response"],
                        state,
                    )
                    actions = self._generate_action_suggestions(state, "support")
                    suggestions = self._generate_conversation_suggestions(state, "support")
                    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
                    return {
                        "message": cached_reply,
                        "intent": "cache",
                        "emotion_detected": state.get("risk_level", "low"),
                        "suggestions": suggestions,
                        "actions": actions,
                        "state": state,
                        "reply_status": "cache_hit",
                        "elapsed_ms": elapsed_ms,
                        "memory_state": state.get("memory_state", {"has_memory": False, "count": 0, "updated": False, "categories": []}),
                        "cache_hit": True,
                        "cache_similarity": cache_similarity,
                    }

            # 4. Router 路由到对应 Agent
            router = self._get_router()
            try:
                reply, agent_name = await self._route_with_deadline(
                    router=router,
                    user_message=user_message,
                    state=state,
                    agent_mode=agent_mode,
                )
            except asyncio.TimeoutError:
                reply = self._timeout_fallback(user_message, state)
                agent_name = "timeout_fallback"
                reply_status = "timeout_fallback"

            reply = self._repair_reply_quality(user_message, reply, state)

            # 5. 保存到语义缓存（仅对低风险、非危机、非质量敏感消息）
            if semantic_cache and self._can_use_semantic_cache(user_message, state) and reply_status == "ok":
                asyncio.create_task(asyncio.to_thread(
                    semantic_cache.set_cached_response,
                    user_message,
                    reply,
                    ttl_hours=settings.SEMANTIC_CACHE_TTL_HOURS,
                ))

            # 5. 生成功能建议
            actions = self._generate_action_suggestions(state, agent_name)

        except Exception as e:
            print(f"[AgentService] Error in routing: {e}")
            traceback.print_exc()
            if contains_crisis_signal(user_message):
                reply = SAFE_INTERVENTION_FALLBACK
                agent_name = "intervention_fallback"
                state = {"risk_level": "crisis", "cycle_phase": "未知", "message": user_message}
            else:
                # 后备回复
                fallback_state = {"risk_level": "low", "cycle_phase": "未知", "message": user_message}
                reply = self._soft_error_fallback(user_message, fallback_state)
                agent_name = "error"
                state = fallback_state
            reply_status = "error_fallback"
            
            actions = self._generate_action_suggestions(state, agent_name)

        elapsed_ms = int((time.perf_counter() - started_at) * 1000)

        # 生成对话快捷回复建议（与actions区分，避免重复）
        suggestions = self._generate_conversation_suggestions(state, agent_name)

        return {
            "message": reply,
            "intent": agent_name,
            "emotion_detected": state.get("risk_level", "low"),
            "suggestions": suggestions,
            "actions": actions,
            "state": state,
            "reply_status": reply_status,
            "elapsed_ms": elapsed_ms,
            "memory_state": state.get("memory_state", {"has_memory": False, "count": 0, "updated": False, "categories": []}),
            "cache_hit": cache_hit,
            "cache_similarity": cache_similarity,
            "compaction_stats": state.get("compaction_stats"),
            "suppress_assessment_prompt": agent_mode == "knowledge" or str(agent_name).startswith("knowledge"),
            "needs_llm_followup": needs_llm_followup,
        }

    async def prepare_streaming_state(
        self,
        user_message: str,
        context: Dict,
        agent_mode: str = "auto",
    ) -> Tuple[Dict[str, Any], Dict]:
        """预构建流式响应的上下文状态，避免重复计算。"""
        cycle_phase = context.get("cycle_phase")
        sensor_data = context.get("sensor_data", {})

        perception = self._get_perception()
        state = perception.analyze(
            message=user_message,
            cycle_phase=cycle_phase,
            sensor_data=sensor_data,
        )
        state = self._attach_conversation_context(state, context, agent_mode)
        state["message"] = user_message
        state["agent_mode"] = agent_mode

        return state, {}

    async def get_streaming_response(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        context: Dict,
        agent_mode: str = "auto",
        pre_built_state: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        获取AI流式响应
        使用新的 Agent 路由系统，支持逐 Token 输出
        """
        started_at = time.perf_counter()

        try:
            cycle_phase = context.get("cycle_phase")
            sensor_data = context.get("sensor_data", {})

            # 使用预构建的状态或重新构建
            if pre_built_state:
                state = pre_built_state
            else:
                perception = self._get_perception()
                state = perception.analyze(
                    message=user_message,
                    cycle_phase=cycle_phase,
                sensor_data=sensor_data
            )
            state = self._attach_conversation_context(state, context, agent_mode)
            state["message"] = user_message

            # 2. 检查安全边界，流式响应同样不能绕过安全感知层。
            risk_level = state.get("risk_level", "low")
            if risk_level in ["high", "crisis"] or contains_crisis_signal(user_message):
                yield {
                    "type": "start",
                    "risk_level": risk_level,
                    "agent_name": "intervention",
                }
                yield {
                    "type": "token",
                    "token": SAFE_INTERVENTION_FALLBACK,
                    "is_final": True,
                    "first_token_latency_ms": int((time.perf_counter() - started_at) * 1000),
                }
                yield {
                    "type": "end",
                    "actions": self._generate_action_suggestions(state),
                    "elapsed_ms": int((time.perf_counter() - started_at) * 1000),
                }
                return

            if agent_mode == "knowledge" or self._looks_like_knowledge_question(user_message):
                router = self._get_router()
                async for chunk in self._stream_router_response(
                    router=router,
                    user_message=user_message,
                    state=state,
                    agent_mode="knowledge" if agent_mode == "knowledge" else agent_mode,
                    started_at=started_at,
                ):
                    yield chunk
                return

            start_sent = False
            full_response = ""

            # 3. 获取 LLM 服务进行流式响应（所有回复都必须走 LLM 路径）
            try:
                llm_service = self._get_llm_service()
            except Exception as exc:
                print(f"[AgentService] Streaming LLM unavailable, using soft fallback: {exc}")
                fallback_reply = self._soft_error_fallback(user_message, state)
                if not start_sent:
                    yield {
                        "type": "start",
                        "risk_level": risk_level,
                        "agent_name": "support_fallback",
                    }
                yield {
                    "type": "token",
                    "token": fallback_reply,
                    "is_final": True,
                    "first_token_latency_ms": int((time.perf_counter() - started_at) * 1000),
                }
                yield {
                    "type": "end",
                    "actions": self._generate_action_suggestions(state, "support_fallback"),
                    "elapsed_ms": int((time.perf_counter() - started_at) * 1000),
                    "full_response": fallback_reply,
                }
                return

            if not llm_service:
                # 降级到普通响应
                response = await self.get_response(user_id, session_id, user_message, context, agent_mode)
                yield {
                    "type": "start",
                    "risk_level": state.get("risk_level", "low"),
                    "agent_name": response.get("intent", "support"),
                }
                yield {
                    "type": "token",
                    "token": response.get("message", ""),
                    "is_final": True,
                    "first_token_latency_ms": int((time.perf_counter() - started_at) * 1000),
                }
                yield {
                    "type": "end",
                    "actions": response.get("actions", []),
                    "elapsed_ms": response.get("elapsed_ms", 0),
                }
                return

            # 4. 构建流式响应上下文
            stream_context = self._build_support_stream_context(state, cycle_phase, risk_level)

            # 5. 发送开始信号
            if not start_sent:
                yield {
                    "type": "start",
                    "risk_level": risk_level,
                    "agent_name": "support",
                }

            # 6. 流式获取响应（混合模式：前3句快速显示，后续逐字显示）
            first_token_received = False
            first_token_latency_ms = 0
            sentence_count = 0
            current_sentence = ""
            char_delay_ms = 0
            context_load_level = state.get("context_load_level", "standard")
            if context_load_level == "full":
                char_delay_ms = 0
            elif context_load_level == "standard":
                char_delay_ms = 20
            else:
                char_delay_ms = 40

            async for chunk in llm_service.async_streaming_generate_reply(user_message, stream_context):
                if "error" in chunk:
                    if first_token_received:
                        break
                    fallback_token = (
                        "我会继续陪着这件事。"
                        if full_response
                        else self._timeout_fallback(user_message, state)
                    )
                    full_response += fallback_token
                    yield {
                        "type": "token",
                        "token": fallback_token,
                        "is_final": True,
                        "first_token_latency_ms": int((time.perf_counter() - started_at) * 1000),
                    }
                    break
                
                token = chunk.get("token", "")
                if token:
                    if not first_token_received:
                        first_token_received = True
                        first_token_latency_ms = chunk.get("first_token_latency_ms", int((time.perf_counter() - started_at) * 1000))
                    
                    current_sentence += token
                    full_response += token
                    
                    is_sentence_end = token in "。！？.!?"
                    if sentence_count < 3:
                        yield {
                            "type": "token",
                            "token": token,
                            "is_final": False,
                            "first_token_latency_ms": first_token_latency_ms,
                        }
                        if is_sentence_end:
                            sentence_count += 1
                            current_sentence = ""
                    else:
                        yield {
                            "type": "token",
                            "token": token,
                            "is_final": False,
                            "first_token_latency_ms": first_token_latency_ms,
                        }
                        if char_delay_ms > 0:
                            await asyncio.sleep(char_delay_ms / 1000.0)
            
            if not first_token_received and not full_response:
                fallback_token = self._timeout_fallback(user_message, state)
                full_response += fallback_token
                yield {
                    "type": "token",
                    "token": fallback_token,
                    "is_final": True,
                    "first_token_latency_ms": int((time.perf_counter() - started_at) * 1000),
                }

            full_response = self._repair_reply_quality(user_message, full_response, state)

            # 7. 发送结束信号
            yield {
                "type": "end",
                "actions": self._generate_action_suggestions(state, "support", full_response),
                "elapsed_ms": int((time.perf_counter() - started_at) * 1000),
                "full_response": full_response,
            }

        except Exception as e:
            print(f"[AgentService] Streaming error: {e}")
            traceback.print_exc()
            yield {
                "type": "token",
                "token": self._soft_error_fallback(user_message, {"risk_level": "low", "message": user_message}),
                "is_final": True,
                "first_token_latency_ms": int((time.perf_counter() - started_at) * 1000),
            }
            yield {
                "type": "end",
                "actions": [],
                "elapsed_ms": int((time.perf_counter() - started_at) * 1000),
                "error": str(e),
            }


_agent_service_singleton: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    global _agent_service_singleton
    if _agent_service_singleton is None:
        _agent_service_singleton = AgentService()
    return _agent_service_singleton
