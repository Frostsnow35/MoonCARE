from pathlib import Path

from app.agents.llm_service import LLMService


class InterventionAgent:
    def __init__(self):
        self.llm = LLMService()
        prompt_path = (
            Path(__file__).resolve().parent.parent
            / "prompts"
            / "intervention_prompt.txt"
        )
        self.system_prompt = prompt_path.read_text(encoding="utf-8")

    def respond(self, message: str, state: dict) -> str:
        risk = state.get("risk_level", "high")
        blob = (
            f"用户原话：{message}\n"
            f"系统感知风险等级：{risk}\n"
            f"周期阶段：{state.get('cycle_phase', '未知')}\n"
            "请按守护宝宝规则回复（2~5 句），优先安全与求助资源。"
        )
        return self.llm.generate_reply(
            blob,
            {"raw_system_prompt": self.system_prompt},
        )