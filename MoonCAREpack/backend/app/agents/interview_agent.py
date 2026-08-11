import json
from pathlib import Path
from typing import Any

from app.utils.safety import contains_crisis_signal


class InterviewAgent:
    """Natural three-phase PSST-style interview agent."""

    MAX_ASSISTANT_TURNS = 6

    def __init__(self) -> None:
        self._flow = self._load_flow()

    def start(self) -> str:
        """Start the natural interview without exposing scale language."""
        return self.phase_plan()[0]["opening"]

    def next_turn(self, messages: list[Any]) -> str:
        """Return the next natural interview turn based on assistant turn count."""
        assistant_count = sum(1 for m in messages if m.role == "assistant")

        if assistant_count == 1:
            return self._with_ack(self.phase_plan()[0]["followups"][0])
        if assistant_count == 2:
            return self._with_ack(self.phase_plan()[0]["followups"][1])
        if assistant_count == 3:
            return self._with_ack(self.phase_plan()[1]["opening"])
        if assistant_count == 4:
            return self._with_ack(self.phase_plan()[1]["followups"][1])
        if assistant_count == 5:
            return self._with_ack(self.phase_plan()[2]["opening"])
        if assistant_count == 6:
            return self._with_ack(self.phase_plan()[2]["followups"][1])
        return self._flow["closing"]

    def phase_plan(self) -> list[dict[str, Any]]:
        """Return the configured three-phase interview plan."""
        return list(self._flow.get("phases", []))

    def detect_crisis(self, messages: list[Any]) -> bool:
        """Detect whether any user message crosses the safety boundary."""
        for m in messages:
            if m.role == "user":
                if contains_crisis_signal(m.content):
                    return True
        return False

    def _load_flow(self) -> dict[str, Any]:
        """Load the PSST interview flow from data configuration."""
        path = Path(__file__).resolve().parents[1] / "data" / "psst_interview_flow.json"
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _with_ack(self, question: str) -> str:
        """Prefix a follow-up with brief companionship copy."""
        return f"我听到了，我们慢慢看这一段就好。\n\n{question}"
