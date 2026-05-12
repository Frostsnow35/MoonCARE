"""
Agent服务 - 委托给新的 Agent 系统
"""
import traceback
from typing import Any, Dict, List, Optional
from app.config import settings
from app.utils.safety import SAFE_INTERVENTION_FALLBACK, contains_crisis_signal

try:
    from app.agents.router import Router
    from app.agents.perception_agent import PerceptionAgent
    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False
    Router = None
    PerceptionAgent = None


class AgentService:
    """
    Agent 服务 - 使用新的多 Agent 系统
    """

    def __init__(self):
        self.context_window = settings.CONTEXT_WINDOW_SIZE  # 10轮对话
        self.router = None  # Lazy init
        self.perception = None  # Lazy init

    def _get_router(self):
        if self.router is None:
            self.router = Router()
        return self.router

    def _get_perception(self):
        if self.perception is None:
            self.perception = PerceptionAgent()
        return self.perception

    def _mode_guidance(self, agent_mode: str) -> str:
        """Return mode-specific interaction guidance for downstream agents."""
        guidance = {
            "support": (
                "当前是情绪陪伴模式：优先共情和情绪命名，结合用户记忆里的偏好与特点，"
                "每次只给一个小问题或一个小行动建议。"
            ),
            "knowledge": (
                "当前是知识解释模式：优先用通俗语言回答问题，必要时结合用户经前体验做解释；"
                "保持仅供参考，不做诊断。"
            ),
            "auto": (
                "当前是自动陪伴模式：根据用户内容在情绪陪伴和知识解释之间自然切换；"
                "遇到风险表达时安全优先。"
            ),
        }
        return guidance.get(agent_mode, guidance["auto"])

    def _generate_action_suggestions(self, state: Dict[str, Any]) -> List[Dict[str, str]]:
        """根据情绪状态生成功能建议"""
        risk_level = state.get("risk_level", "low")
        message = state.get("message", "")
        support_context = state.get("support_context") or {}
        body_signals = set(support_context.get("body_signals") or [])
        emotion_signals = set(support_context.get("emotion_signals") or [])
        menstrual_related = bool(support_context.get("menstrual_related"))
        
        actions = []

        if "pain" in body_signals:
            actions.append({
                "action": "warmth",
                "label": "暖一暖小腹",
                "description": "用热水袋或温热毛巾暖一下小腹，先让身体松一点",
                "route": None
            })
        
        # 焦虑、惊慌或高风险 -> 呼吸练习 / 安全支持
        anxiety_keywords = ["紧张", "焦虑", "慌", "担心", "不安", "惊恐"]
        if any(keyword in message for keyword in anxiety_keywords) or risk_level in ["high", "crisis"]:
            actions.append({
                "action": "breathing",
                "label": "🧘 呼吸放松",
                "description": "进行深呼吸练习，帮助平静下来",
                "route": "/breathing"
            })
        
        # 烦躁、易怒 -> 听音乐
        anger_keywords = ["烦躁", "易怒", "火大", "烦", "生气"]
        if any(keyword in message for keyword in anger_keywords) or "irritable" in emotion_signals:
            actions.append({
                "action": "music",
                "label": "🎵 听音乐",
                "description": "听一些舒缓的音乐放松心情",
                "route": "/music"
            })
        
        # 低落、难过 -> 写日记
        sad_keywords = ["低落", "难过", "想哭", "委屈", "伤心"]
        if any(keyword in message for keyword in sad_keywords) or emotion_signals.intersection({"sad", "tearful", "helpless"}):
            actions.append({
                "action": "diary",
                "label": "📝 写日记",
                "description": "写下你的感受，释放情绪",
                "route": "/diary"
            })
        
        # 疲惫 -> 休息建议
        tired_keywords = ["累", "疲惫", "困", "乏力"]
        if any(keyword in message for keyword in tired_keywords) or body_signals.intersection({"fatigue", "sleep_change"}):
            actions.append({
                "action": "rest",
                "label": "😴 休息一下",
                "description": "建议好好休息，照顾好自己",
                "route": None
            })
        
        # 经前/经期语境下，默认给低压力身体照护，不制造急救感。
        if not actions and menstrual_related:
            actions.append({
                "action": "rest",
                "label": "先缓一缓",
                "description": "喝点温水，允许自己蜷起来休息一会儿",
                "route": None
            })

        # 如果没有特定情绪，也提供低压力通用建议
        if not actions:
            actions.append({
                "action": "diary",
                "label": "📝 写下感受",
                "description": "简单记一两句现在的感受",
                "route": "/diary"
            })
            actions.append({
                "action": "music",
                "label": "🎵 听音乐",
                "description": "听一些舒缓的音乐",
                "route": "/music"
            })
        
        return actions[:3]  # 最多返回3个建议

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
        使用新的 Agent 路由系统
        """
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

            # 2. Router 路由到对应 Agent
            router = self._get_router()
            reply, agent_name = router.route(user_message, state, agent_mode=agent_mode)

            # 3. 生成功能建议
            state["message"] = user_message
            actions = self._generate_action_suggestions(state)

        except Exception as e:
            print(f"[AgentService] Error in routing: {e}")
            traceback.print_exc()
            if contains_crisis_signal(user_message):
                reply = SAFE_INTERVENTION_FALLBACK
                agent_name = "intervention_fallback"
                state = {"risk_level": "crisis", "cycle_phase": "未知", "message": user_message}
            else:
                # 后备回复
                reply = "我现在有点状况，可能需要稍后再试~"
                agent_name = "error"
                state = {"risk_level": "low", "cycle_phase": "未知", "message": user_message}
            
            actions = self._generate_action_suggestions(state)

        return {
            "message": reply,
            "intent": agent_name,
            "emotion_detected": state.get("risk_level", "low"),
            "suggestions": [],
            "actions": actions,
            "state": state,
            "memory_state": state.get("memory_state", {"has_memory": False, "count": 0, "updated": False, "categories": []}),
        }


_agent_service_singleton: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    global _agent_service_singleton
    if _agent_service_singleton is None:
        _agent_service_singleton = AgentService()
    return _agent_service_singleton
