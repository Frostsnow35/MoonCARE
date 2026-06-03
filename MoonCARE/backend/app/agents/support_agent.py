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

    def _prompt_name(self, state: dict) -> str:
        """Choose a support prompt variant without changing the external API."""
        if (state or {}).get("support_intent") == "action_support":
            return "support_action_prompt.txt"
        return "support_prompt.txt"

    def _nickname_prompt_hint(self, state: dict) -> str:
        """Tell the model when a one-time nickname address is appropriate."""
        state = state or {}
        nickname = str(state.get("user_nickname") or "").strip()
        if not nickname or not state.get("is_first_assistant_turn"):
            return ""
        return (
            f"\n\n当前用户昵称：{nickname}。"
            "如果这是当前会话的第一句支持性回复，可以自然称呼一次；"
            "之后不要每轮重复称呼，也不要显得刻意。"
        )

    def respond(self, message: str, state: dict) -> str:
        cycle_phase = state.get("cycle_phase", "未知")
        risk_level = state.get("risk_level", "low")
        support_context = self._format_support_context(state.get("support_context", {}))
        formatted_conversation_history = self._format_conversation_messages(
            state.get("conversation_messages", [])
        )
        prompt_name = self._prompt_name(state)

        raw_system_prompt = render_prompt(
            prompt_name,
            cycle_phase=cycle_phase,
            risk_level=risk_level,
            support_context=support_context,
            memory_context=state.get("memory_context", "暂无可用长期记忆。"),
            health_context=state.get("health_context", "暂无可用的周期/日记上下文。"),
            recent_context=state.get("recent_context", "暂无最近对话。"),
            retrieved_context=state.get("retrieved_context", "暂无检索片段。"),
            formatted_conversation_history=formatted_conversation_history,
            mode_guidance=state.get("mode_guidance", ""),
            support_intent=state.get("support_intent", "support"),
        )
        raw_system_prompt = f"{raw_system_prompt}{self._nickname_prompt_hint(state)}"

        context = {
            "cycle_phase": cycle_phase,
            "risk_level": risk_level,
            "support_context": support_context,
            "memory_context": state.get("memory_context", "暂无可用长期记忆。"),
            "health_context": state.get("health_context", "暂无可用的周期/日记上下文。"),
            "recent_context": state.get("recent_context", "暂无最近对话。"),
            "retrieved_context": state.get("retrieved_context", "暂无检索片段。"),
            "formatted_conversation_history": formatted_conversation_history,
            "conversation_messages": state.get("conversation_messages", []),
            "mode_guidance": state.get("mode_guidance", ""),
            "support_intent": state.get("support_intent", "support"),
            "raw_system_prompt": raw_system_prompt,
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

    def _format_conversation_messages(self, conversation_messages: list) -> str:
        """Format conversation history into a readable string for LLM."""
        if not conversation_messages:
            return "暂无历史对话。"
        
        formatted = []
        for idx, msg in enumerate(conversation_messages, 1):
            role = msg.get("role", "")
            content = msg.get("content", "").strip()
            if not content:
                continue
            
            role_label = "用户" if role == "user" else "你"
            formatted.append(f"{idx}. {role_label}：{content}")
        
        if not formatted:
            return "暂无历史对话。"
        
        return "\n".join(formatted)
