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

class Router:
    def __init__(self):
        self._support = None
        self._knowledge = None
        self._intervention = None

    def _safe_intervention_fallback(self):
        return SAFE_INTERVENTION_FALLBACK

    @property
    def support(self):
        if self._support is None:
            self._support = SupportAgent()
        return self._support

    @property
    def knowledge(self):
        if self._knowledge is None:
            try:
                self._knowledge = KnowledgeAgent()
            except Exception as e:
                print(f"[Router] Failed to initialize KnowledgeAgent: {e}")
                self._knowledge = None
        return self._knowledge

    @property
    def intervention(self):
        if self._intervention is None:
            try:
                self._intervention = InterventionAgent()
            except Exception as e:
                print(f"[Router] Failed to initialize InterventionAgent: {e}")
                self._intervention = None
        return self._intervention

    def route(self, message: str, state: dict, agent_mode: str = "auto"):
        message = message or ""
        risk_level = state.get("risk_level", "low")
        agent_mode = agent_mode if agent_mode in {"auto", "support", "knowledge"} else "auto"

        # 1. 高风险 / 危机优先
        if risk_level in ["high", "crisis"]:
            if self.intervention is None:
                return self._safe_intervention_fallback(), "intervention_fallback"
            try:
                reply = self.intervention.respond(message, state)
                return reply, "intervention"
            except Exception as e:
                print(f"[Router] InterventionAgent error: {e}")
                return self._safe_intervention_fallback(), "intervention_fallback"

        # 2. 用户可见角色只是低风险路由偏好，不能覆盖上面的安全优先级。
        if agent_mode == "support":
            try:
                reply = self.support.respond(message, state)
                return reply, "support"
            except Exception as e:
                print(f"[Router] SupportAgent error: {e}")
                return "我现在有点状况，可能需要稍后再试~", "error"

        if agent_mode == "knowledge" and self.knowledge is not None:
            try:
                reply = self.knowledge.respond(message, state)
                return reply, "knowledge"
            except Exception as e:
                print(f"[Router] KnowledgeAgent error: {e}")

        # 3. 科普问题走 knowledge
        knowledge_keywords = [
            "什么是", "为什么", "正常吗", "是不是", "会不会",
            "PMS", "pms", "经前综合征", "月经前", "经期前"
        ]
        if any(k in message for k in knowledge_keywords):
            if self.knowledge is not None:
                try:
                    reply = self.knowledge.respond(message, state)
                    return reply, "knowledge"
                except Exception as e:
                    print(f"[Router] KnowledgeAgent error: {e}")

            # Knowledge agent not available or failed, fall back to support
            pass

        # 4. 默认走陪伴
        try:
            reply = self.support.respond(message, state)
            return reply, "support"
        except Exception as e:
            print(f"[Router] SupportAgent error: {e}")
            return "我现在有点状况，可能需要稍后再试~", "error"
