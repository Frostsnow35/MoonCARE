try:
    from app.agents.llm_service import LLMService
    from app.agents.llm_service import OPENAI_AVAILABLE
    from app.utils.prompt_loader import render_prompt
except ImportError:
    LLMService = None
    OPENAI_AVAILABLE = False
    render_prompt = None


class SupportAgent:
    def __init__(self):
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed. Please install with: pip install openai")
        self.llm = LLMService()

    def respond(self, message: str, state: dict) -> str:
        cycle_phase = state.get("cycle_phase", "未知")
        risk_level = state.get("risk_level", "low")
        support_context = self._format_support_context(state.get("support_context", {}))

        context = {
            "cycle_phase": cycle_phase,
            "risk_level": risk_level,
            "support_context": support_context,
            "memory_context": state.get("memory_context", "暂无可用长期记忆。"),
            "health_context": state.get("health_context", "暂无可用的周期/日记上下文。"),
            "recent_context": state.get("recent_context", "暂无最近对话。"),
            "retrieved_context": state.get("retrieved_context", "暂无检索片段。"),
            "conversation_messages": state.get("conversation_messages", []),
            "mode_guidance": state.get("mode_guidance", ""),
            "raw_system_prompt": render_prompt(
                "support_prompt.txt",
                cycle_phase=cycle_phase,
                risk_level=risk_level,
                support_context=support_context,
                memory_context=state.get("memory_context", "暂无可用长期记忆。"),
                health_context=state.get("health_context", "暂无可用的周期/日记上下文。"),
                recent_context=state.get("recent_context", "暂无最近对话。"),
                retrieved_context=state.get("retrieved_context", "暂无检索片段。"),
                mode_guidance=state.get("mode_guidance", ""),
            ),
        }

        return self.llm.generate_reply(message, context)

    def _format_support_context(self, support_context: dict) -> str:
        """Format lightweight body-emotion signals for the prompt."""
        if not support_context:
            return "暂无额外身体-情绪线索。"
        menstrual = "是" if support_context.get("menstrual_related") else "否"
        body = "、".join(support_context.get("body_signals") or []) or "无"
        emotion = "、".join(support_context.get("emotion_signals") or []) or "无"
        return f"可能与经前/经期有关：{menstrual}；身体线索：{body}；情绪线索：{emotion}。"
