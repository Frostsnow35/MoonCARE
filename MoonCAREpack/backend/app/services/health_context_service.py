"""Build bounded cycle and diary context for chat prompts."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.models.menstrual import MenstrualRecord
from app.models.mood import MoodDiary


logger = logging.getLogger(__name__)


class HealthContextService:
    """Create a minimal, same-user health context for the chat agent."""

    max_diary_text_length = 48

    def __init__(self, db: Session, today: date | None = None) -> None:
        self.db = db
        self.today = today or date.today()

    def build_prompt_context(
        self,
        user_id: int,
        diary_days: int = 14,
        diary_limit: int = 3,
    ) -> dict[str, Any]:
        """Return prompt text and metadata from the user's own cycle and diary data."""
        latest_record = self._latest_menstrual_record(user_id)
        recent_diaries = self._recent_diaries(user_id, diary_days, diary_limit)

        cycle_context, cycle_state = self._format_cycle_context(latest_record)
        diary_context = self._format_diary_context(recent_diaries)

        lines = []
        if cycle_context:
            lines.append(f"- 周期：{cycle_context}")
        if diary_context:
            lines.append(f"- 近日情绪日记：{diary_context}")

        available = bool(lines)
        health_context = "\n".join(lines) if available else "暂无可用的周期/日记上下文。"
        return {
            "health_context": health_context,
            "health_state": {
                "available": available,
                "has_cycle": bool(cycle_context),
                "has_diary": bool(diary_context),
                "cycle_phase": cycle_state.get("phase"),
                "cycle_day": cycle_state.get("cycle_day"),
                "diary_count": len(recent_diaries),
            },
        }

    def _latest_menstrual_record(self, user_id: int) -> MenstrualRecord | None:
        """Load the latest menstrual record owned by this user."""
        return (
            self.db.query(MenstrualRecord)
            .filter(MenstrualRecord.user_id == user_id)
            .order_by(MenstrualRecord.start_date.desc(), MenstrualRecord.id.desc())
            .first()
        )

    def _recent_diaries(self, user_id: int, diary_days: int, diary_limit: int) -> list[MoodDiary]:
        """Load recent diary rows owned by this user."""
        start_at = datetime.combine(self.today - timedelta(days=diary_days), datetime.min.time())
        return (
            self.db.query(MoodDiary)
            .filter(
                MoodDiary.user_id == user_id,
                MoodDiary.date >= start_at,
            )
            .order_by(MoodDiary.date.desc(), MoodDiary.id.desc())
            .limit(diary_limit)
            .all()
        )

    def _format_cycle_context(self, record: MenstrualRecord | None) -> tuple[str, dict[str, Any]]:
        """Format a concise, non-diagnostic cycle summary."""
        if not record or not record.start_date:
            return "", {"phase": None, "cycle_day": None}

        cycle_day = max((self.today - record.start_date).days + 1, 1)
        phase = self._infer_phase(record, cycle_day)
        phase_label = self._phase_label(phase)

        parts = [f"最近一次月经开始：{record.start_date.isoformat()}"]
        if record.end_date:
            parts.append(f"结束：{record.end_date.isoformat()}")
        if cycle_day <= 45:
            parts.append(f"当前约第{cycle_day}天")
        if phase_label:
            parts.append(f"可能处于{phase_label}")
        if record.flow_intensity:
            parts.append(f"经量记录：{record.flow_intensity}/5")

        symptoms = self._safe_list(record.symptoms)
        if symptoms:
            parts.append(f"身体记录：{'、'.join(symptoms[:4])}")
        if record.predicted_next_start:
            parts.append(f"预测下次开始：{record.predicted_next_start.isoformat()}")
        if record.prediction_confidence is not None:
            parts.append(f"预测置信度：{float(record.prediction_confidence):.2f}")

        parts.append("这些只作为陪伴参考，不代表诊断")
        return "；".join(parts), {"phase": phase, "cycle_day": cycle_day}

    def _infer_phase(self, record: MenstrualRecord, cycle_day: int) -> str:
        """Infer a lightweight phase label without changing prediction algorithms."""
        if record.end_date and record.start_date <= self.today <= record.end_date:
            return "menstrual"
        if 1 <= cycle_day <= 5:
            return "menstrual"
        if 6 <= cycle_day <= 12:
            return "follicular"
        if 13 <= cycle_day <= 16:
            return "ovulation"
        if 17 <= cycle_day <= 45:
            return "luteal"
        return "unknown"

    def _phase_label(self, phase: str) -> str:
        """Return a user-facing Chinese phase label."""
        return {
            "menstrual": "经期",
            "follicular": "卵泡期",
            "ovulation": "排卵期",
            "luteal": "黄体期/经前阶段",
        }.get(phase, "")

    def _format_diary_context(self, diaries: Iterable[MoodDiary]) -> str:
        """Format recent diary signals with bounded snippets."""
        lines = []
        for diary in diaries:
            parts = []
            if diary.date:
                parts.append(diary.date.date().isoformat())
            if diary.mood_level is not None:
                parts.append(f"心情{float(diary.mood_level):.1f}/10")

            tags = self._safe_list(diary.emotion_tags)
            keywords = self._safe_list(diary.keywords)
            if tags:
                parts.append(f"情绪：{'、'.join(tags[:4])}")
            if keywords:
                parts.append(f"关键词：{'、'.join(keywords[:5])}")

            snippet = self._diary_snippet(diary)
            if snippet and not keywords:
                parts.append(f"摘要：{snippet}")

            if parts:
                lines.append("；".join(parts))

        return " | ".join(lines)

    def _diary_snippet(self, diary: MoodDiary) -> str:
        """Return a short diary snippet only when structured keywords are absent."""
        text = diary.processed_text or diary.original_text or ""
        normalized = " ".join(str(text).split())
        if len(normalized) <= self.max_diary_text_length:
            return normalized
        return f"{normalized[: self.max_diary_text_length - 1]}…"

    def _safe_list(self, value: Any) -> list[str]:
        """Decode list-like model fields stored as JSON or plain text."""
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, tuple):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            try:
                decoded = json.loads(text)
                if isinstance(decoded, list):
                    return [str(item) for item in decoded if str(item).strip()]
            except json.JSONDecodeError:
                logger.debug("Health context field is not JSON; using plain value.")
            return [text]
        return [str(value)]
