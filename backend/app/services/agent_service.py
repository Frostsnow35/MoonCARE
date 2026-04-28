"""
Agent服务 - 委托给新的 Agent 系统
"""
import traceback
from typing import Dict, Optional
from app.config import settings

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

    async def get_response(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        context: Dict
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

            # 2. Router 路由到对应 Agent
            router = self._get_router()
            reply, agent_name = router.route(user_message, state)

        except Exception as e:
            print(f"[AgentService] Error in routing: {e}")
            traceback.print_exc()
            # 后备回复
            reply = "我现在有点状况，可能需要稍后再试~"
            agent_name = "error"
            state = {"risk_level": "low", "cycle_phase": "未知"}

        return {
            "message": reply,
            "intent": agent_name,
            "emotion_detected": state.get("risk_level", "low"),
            "suggestions": [],
            "state": state
        }


_agent_service_singleton: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    global _agent_service_singleton
    if _agent_service_singleton is None:
        _agent_service_singleton = AgentService()
    return _agent_service_singleton
