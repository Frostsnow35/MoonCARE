"""
Agent服务 - 委托给新的 Agent 系统
集成语义缓存和对话压缩优化
"""
import asyncio
import time
import traceback
from typing import Any, Dict, List, Optional, AsyncGenerator
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
            self.llm_service = LLMService()
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
                "先回应用户原话里的具体事件，每次只给一个小问题或一个小行动建议；"
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

    def _should_show_actions(self, state: Dict[str, Any], agent_name: str = "") -> bool:
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
        
        return True

    def _generate_action_suggestions(self, state: Dict[str, Any], agent_name: str = "") -> List[Dict[str, str]]:
        """根据情绪状态生成功能建议"""
        # 检查是否应该显示行动建议
        if not self._should_show_actions(state, agent_name):
            return []
        
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
        """Add bounded memory and recent-turn context to the perceived state."""
        conversation_memory = (context or {}).get("conversation_memory") or {}
        state = dict(state or {})
        state["agent_mode"] = agent_mode
        state["memory_context"] = conversation_memory.get("memory_context", "暂无可用长期记忆。")
        state["recent_context"] = conversation_memory.get("recent_context", "暂无最近对话。")
        state["retrieved_context"] = conversation_memory.get("retrieved_context", "暂无检索片段。")
        state["conversation_messages"] = conversation_memory.get("conversation_messages", [])
        state["mode_guidance"] = self._mode_guidance(agent_mode)
        state["memory_state"] = conversation_memory.get(
            "memory_state",
            {"has_memory": False, "count": 0, "updated": False, "categories": []},
        )
        return state

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

    def _timeout_fallback(self, user_message: str, state: Dict[str, Any]) -> str:
        """Return a bounded fallback when the selected model misses the chat deadline."""
        risk_level = (state or {}).get("risk_level", "low")
        if risk_level in {"high", "crisis"} or contains_crisis_signal(user_message):
            return SAFE_INTERVENTION_FALLBACK

        if self.response_quality_guard:
            direct_reply = self.response_quality_guard.direct_reply_if_applicable(user_message, state or {})
            if direct_reply:
                return direct_reply

        return "我在听。你刚说的这件事值得被认真对待，不需要先整理成很完整的话。我们可以先从此刻最明显的那一点开始说。"

    def _soft_error_fallback(self, user_message: str, state: Dict[str, Any]) -> str:
        """Return user-facing copy for unexpected non-crisis chat failures."""
        state = state or {}
        if state.get("risk_level") in {"high", "crisis"} or contains_crisis_signal(user_message):
            return SAFE_INTERVENTION_FALLBACK
        if self.response_quality_guard:
            direct_reply = self.response_quality_guard.direct_reply_if_applicable(user_message, state)
            if direct_reply:
                return direct_reply
        return "我在。刚才没有顺利接上完整回复，但你说的内容我已经接住了。你可以继续说下一句，我会跟着你。"

    def _repair_reply_quality(
        self,
        user_message: str,
        reply: str,
        state: Dict[str, Any],
    ) -> str:
        """Repair common conversational quality failures with deterministic rules."""
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
    ) -> Dict:
        """
        获取AI响应
        使用新的 Agent 路由系统，集成语义缓存和对话压缩优化
        """
        started_at = time.perf_counter()
        reply_status = "ok"
        cache_hit = False
        cache_similarity = 0.0
        
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

            direct_reply = self._direct_quality_reply(user_message, state)
            if direct_reply:
                actions = self._generate_action_suggestions(state, "support")
                suggestions = self._generate_conversation_suggestions(state, "support")
                elapsed_ms = int((time.perf_counter() - started_at) * 1000)
                return {
                    "message": direct_reply,
                    "intent": "support_quality_guard",
                    "emotion_detected": state.get("risk_level", "low"),
                    "suggestions": suggestions,
                    "actions": actions,
                    "state": state,
                    "reply_status": "ok",
                    "elapsed_ms": elapsed_ms,
                    "memory_state": state.get("memory_state", {"has_memory": False, "count": 0, "updated": False, "categories": []}),
                    "cache_hit": False,
                    "cache_similarity": 0.0,
                    "compaction_stats": state.get("compaction_stats"),
                    "suppress_assessment_prompt": True,
                }
            state["agent_mode"] = agent_mode  # 保存 agent_mode 到 state

            # 3. 检查语义缓存。必须在风险感知之后执行，避免缓存绕过安全层。
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
        }

    async def get_streaming_response(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        context: Dict,
        agent_mode: str = "auto",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        获取AI流式响应
        使用新的 Agent 路由系统，支持逐 Token 输出
        """
        started_at = time.perf_counter()
        
        try:
            cycle_phase = context.get("cycle_phase")
            sensor_data = context.get("sensor_data", {})

            # 1. PerceptionAgent 分析风险等级
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
            if self.response_quality_guard:
                fast_ack = self.response_quality_guard.fast_ack_if_applicable(user_message, state)
                if fast_ack:
                    yield {
                        "type": "start",
                        "risk_level": risk_level,
                        "agent_name": "support",
                    }
                    start_sent = True
                    full_response += fast_ack
                    yield {
                        "type": "token",
                        "token": fast_ack,
                        "is_final": False,
                        "first_token_latency_ms": int((time.perf_counter() - started_at) * 1000),
                    }
                else:
                    direct_reply = self.response_quality_guard.direct_reply_if_applicable(user_message, state)
                    if direct_reply:
                        yield {
                            "type": "start",
                            "risk_level": risk_level,
                            "agent_name": "support",
                        }
                        yield {
                            "type": "token",
                            "token": direct_reply,
                            "is_final": True,
                            "first_token_latency_ms": int((time.perf_counter() - started_at) * 1000),
                        }
                        yield {
                            "type": "end",
                            "actions": self._generate_action_suggestions(state),
                            "elapsed_ms": int((time.perf_counter() - started_at) * 1000),
                            "full_response": direct_reply,
                        }
                        return

            # 3. 获取 LLM 服务进行流式响应
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

            # 6. 流式获取响应
            first_token_received = False
            first_token_latency_ms = 0

            async for chunk in llm_service.async_streaming_generate_reply(user_message, stream_context):
                if "error" in chunk:
                    if first_token_received:
                        break
                    fallback_token = (
                        "你可以接着说，我会跟着你。"
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
                    
                    full_response += token
                    yield {
                        "type": "token",
                        "token": token,
                        "is_final": False,
                        "first_token_latency_ms": first_token_latency_ms,
                    }
            
            full_response = self._repair_reply_quality(user_message, full_response, state)

            # 7. 发送结束信号
            yield {
                "type": "end",
                "actions": self._generate_action_suggestions(state),
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
