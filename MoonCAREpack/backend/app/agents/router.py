import logging
from typing import Any, Dict, Optional, Tuple

try:
    from app.agents.support_agent import SupportAgent
    from app.agents.knowledge_agent import KnowledgeAgent
    from app.agents.intervention_agent import InterventionAgent
    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False
    SupportAgent = None
    KnowledgeAgent = None
    InterventionAgent = None

from app.utils.safety import SAFE_INTERVENTION_FALLBACK


logger = logging.getLogger(__name__)

SUPPORT_HANDOFF_FALLBACK = "我在。你可以继续说，我会先跟着你现在最明显的感受。"
LIGHT_COMFORT_FALLBACK = "好的，那我们不做了。允许自己在这几分钟里摆烂和发呆。我可以就这么陪你安静地待一会。你想吐槽什么，我都在听。"
KNOWLEDGE_FALLBACK_REPLY = (
    "这个问题我先给一个谨慎答复：经前/经期情绪突然变化，可能和激素水平变化、睡眠、疼痛、压力"
    "以及当天事件叠加有关，个体差异会很大。这里仅供参考，不代表诊断；如果波动明显影响生活，"
    "可以记录周期、情绪和身体症状，并咨询专业医生。你也可以告诉我它通常发生在经前几天，"
    "我帮你一起梳理规律。"
)


class Router:
    """Route chat turns through knowledge and emotional support agents."""

    def __init__(self) -> None:
        self._support: Optional[Any] = None
        self._knowledge: Optional[Any] = None
        self._intervention: Optional[Any] = None

    def _safe_intervention_fallback(self) -> str:
        """Return the crisis-safe intervention copy."""
        return SAFE_INTERVENTION_FALLBACK

    def _knowledge_fallback(self) -> str:
        """Return a cautious non-diagnostic answer when knowledge generation is unavailable."""
        return KNOWLEDGE_FALLBACK_REPLY

    @property
    def support(self) -> Optional[Any]:
        """Lazily initialize the support agent."""
        if self._support is None and SupportAgent is not None:
            try:
                self._support = SupportAgent()
            except Exception as exc:
                logger.exception("[Router] Failed to initialize SupportAgent: %s", exc)
                self._support = None
        return self._support

    @property
    def knowledge(self) -> Optional[Any]:
        """Lazily initialize the knowledge agent."""
        if self._knowledge is None and KnowledgeAgent is not None:
            try:
                self._knowledge = KnowledgeAgent()
            except Exception as exc:
                logger.exception("[Router] Failed to initialize KnowledgeAgent: %s", exc)
                self._knowledge = None
        return self._knowledge

    @property
    def intervention(self) -> Optional[Any]:
        """Lazily initialize the intervention agent."""
        if self._intervention is None and InterventionAgent is not None:
            try:
                self._intervention = InterventionAgent()
            except Exception as exc:
                logger.exception("[Router] Failed to initialize InterventionAgent: %s", exc)
                self._intervention = None
        return self._intervention

    def _looks_like_knowledge_question(self, message: str) -> bool:
        """Return whether the turn primarily asks for PMS or menstrual-cycle explanation."""
        compact = "".join((message or "").split())
        
        # 疑问词库：扩展了缓解/改善相关的疑问表达
        question_markers = (
            "为什么", "什么是", "怎么回事", "原因", "会不会", "正常吗", "是不是", "如何", "怎么办",
            "怎么缓解", "怎么改善", "有没有办法", "如何处理", "怎么办呢", "能缓解吗", "有什么办法",
            "可以吗", "能吗", "能做吗", "可不可", "可以", "能"
        )
        
        # 健康/情绪主题词库：扩展了常见的情绪和身体症状词
        health_context_markers = (
            "经前", "经期", "月经", "姨妈", "PMS", "pms", "PMDD", "pmdd", "激素", "周期",
            "情绪", "烦躁", "失眠", "焦虑", "抑郁", "难过", "易怒", "头痛", "腹痛", "疲劳", "乳房", "水肿",
            "运动", "饮食", "睡眠", "休息"
        )
        
        # 特定模式识别：识别"怎么缓解X"、"如何改善X"等常见求助模式
        specific_patterns = ("怎么缓解", "如何改善", "有没有办法", "如何处理", "怎么办呢", "能缓解", "有什么办法")
        has_specific_pattern = any(pattern in compact for pattern in specific_patterns)
        
        # 基础判断：疑问词 + 主题词/问号
        has_question = any(marker in compact for marker in question_markers)
        has_health_context = any(marker in compact for marker in health_context_markers)
        has_question_mark = "？" in compact or "?" in compact
        
        # 组合逻辑：基础模式 或 特定求助模式（即使没有严格的疑问词+主题词组合）
        basic_match = has_question and (has_health_context or has_question_mark)
        
        # 特殊情况："PMS是什么"应该识别为知识问题
        if "是什么" in compact and ("PMS" in compact or "pmdd" in compact.lower()):
            return True
        
        # 特殊情况：单独的健康疑问（如"这正常吗"）
        standalone_health_questions = ("正常吗", "可以吗", "能吗")
        for q in standalone_health_questions:
            if q in compact and len(compact) <= 6:
                return True
        
        # 特殊情况：健康主题词+疑问词组合（如"经期可以运动吗"）
        if has_health_context and has_question:
            return True
        
        return basic_match or has_specific_pattern

    def _looks_like_negative_feedback(self, message: str) -> bool:
        """Return whether the message contains negative feedback about action suggestions."""
        compact = "".join((message or "").split())
        
        # 情绪表达关键词：这些是情绪描述，不是对行动建议的拒绝
        emotion_expression_markers = ("烦躁", "很烦", "烦恼", "心烦")
        
        # 检查是否只是情绪表达（而不是拒绝）
        has_emotion_expression = any(marker in compact for marker in emotion_expression_markers)
        if has_emotion_expression and len(compact) <= 6:  # 简短的情绪表达
            return False
        
        # 负反馈关键词：用户拒绝行动建议的常见表达
        negative_feedback_markers = (
            "不想动", "不想做", "没时间", "没时间做", "做不到", "不行", "不要", "别",
            "你好烦", "太烦了", "够了", "别说了", "停下", "不用了", "不必了"
        )
        
        return any(marker in compact for marker in negative_feedback_markers)

    def _has_contextual_health_signal(self, state: Dict[str, Any]) -> bool:
        """Return whether memory or recent turns contain menstrual or symptom context."""
        context_text = " ".join(
            str((state or {}).get(key) or "")
            for key in ("memory_context", "recent_context", "retrieved_context")
        )
        health_context_markers = (
            "经前", "经期", "月经", "姨妈", "PMS", "pms", "PMDD", "pmdd", "激素", "周期",
            "失眠", "睡不好", "烦躁", "焦虑", "头痛", "腹痛", "疲劳", "水肿", "乳房",
        )
        return any(marker in context_text for marker in health_context_markers)

    def _looks_like_contextual_knowledge_question(self, message: str, state: Dict[str, Any]) -> bool:
        """Route context-dependent explanation questions to knowledge when prior context is health-related."""
        compact = "".join((message or "").split())
        explanation_markers = (
            "怎么回事", "为什么", "原因", "正常吗", "是不是", "会不会", "什么情况", "这是什么",
        )
        if not any(marker in compact for marker in explanation_markers):
            return False
        return self._has_contextual_health_signal(state)

    def _run_knowledge(self, message: str, state: Dict[str, Any]) -> Tuple[str, str]:
        """Run the knowledge agent or return a cautious knowledge fallback."""
        if self.knowledge is None:
            return self._knowledge_fallback(), "knowledge_fallback"
        try:
            return self.knowledge.respond(message, state), "knowledge"
        except Exception as exc:
            logger.exception("[Router] KnowledgeAgent error: %s", exc)
            return self._knowledge_fallback(), "knowledge_fallback"

    def _run_support(self, message: str, state: Dict[str, Any]) -> Tuple[str, str]:
        """Run the support agent or return a brief human handoff copy."""
        if self.support is None:
            return SUPPORT_HANDOFF_FALLBACK, "support_fallback"
        try:
            return self.support.respond(message, state), "support"
        except Exception as exc:
            logger.exception("[Router] SupportAgent error: %s", exc)
            return SUPPORT_HANDOFF_FALLBACK, "support_fallback"

    def route(self, message: str, state: Dict[str, Any], agent_mode: str = "auto") -> Tuple[str, str]:
        """Route one chat message across the existing three-mode system."""
        message = message or ""
        state = state or {}
        risk_level = state.get("risk_level", "low")
        agent_mode = agent_mode if agent_mode in {"auto", "support", "knowledge"} else "auto"

        if risk_level in {"high", "crisis"}:
            if self.intervention is None:
                return self._safe_intervention_fallback(), "intervention_fallback"
            try:
                return self.intervention.respond(message, state), "intervention"
            except Exception as exc:
                logger.exception("[Router] InterventionAgent error: %s", exc)
                return self._safe_intervention_fallback(), "intervention_fallback"

        # 负反馈检测：如果用户拒绝行动建议，切换到轻安抚陪伴模式
        if self._looks_like_negative_feedback(message):
            return LIGHT_COMFORT_FALLBACK, "light_comfort"

        if agent_mode == "knowledge":
            return self._run_knowledge(message, state)

        if agent_mode == "support":
            return self._run_support(message, state)

        if self._looks_like_knowledge_question(message) or self._looks_like_contextual_knowledge_question(message, state):
            return self._run_knowledge(message, state)

        return self._run_support(message, state)
