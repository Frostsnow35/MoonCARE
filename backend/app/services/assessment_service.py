from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.assessment import AssessmentObservation, AssessmentSession
from app.utils.prompt_loader import load_prompt
from app.utils.safety import contains_crisis_signal


ASSESSMENT_STATUS_IDLE = "idle"
ASSESSMENT_STATUS_ELIGIBLE = "eligible"
ASSESSMENT_STATUS_AWAITING = "awaiting_answer"
ASSESSMENT_STATUS_COOLDOWN = "cooldown"
ASSESSMENT_STATUS_COMPLETED = "completed"
ASSESSMENT_STATUS_CRISIS = "crisis_handoff"


@dataclass
class AssessmentTurnResult:
    """Result used by chat routes to keep assessment state hidden from UI."""

    assessment_state: Dict[str, Any]
    assessment_prompt_hint: Optional[str] = None


class AssessmentOrchestrator:
    """Coordinate the hidden premenstrual state assessment loop."""

    banned_copy_terms = ("筛查", "量表", "诊断", "测评")

    def __init__(self, db: Session):
        self.db = db

    def prepare_turn(
        self,
        user_id: int,
        chat_session_id: str,
        user_message: str,
        context: Dict[str, Any],
    ) -> AssessmentTurnResult:
        """Update hidden state before the assistant response is returned."""
        session = self._get_or_create_session(user_id, chat_session_id)
        risk_level = (context or {}).get("risk_level") or "low"

        if risk_level == "crisis" or contains_crisis_signal(user_message):
            session.status = ASSESSMENT_STATUS_CRISIS
            session.current_dimension = None
            self.db.commit()
            return AssessmentTurnResult(self._state(session))

        if session.status == ASSESSMENT_STATUS_AWAITING:
            return AssessmentTurnResult(self._state(session))

        if not self._is_triggered(user_message, context):
            session.status = session.status or ASSESSMENT_STATUS_IDLE
            self.db.commit()
            return AssessmentTurnResult(self._state(session))

        if self._is_in_cooldown(session):
            return AssessmentTurnResult(self._state(session))

        dimension = self._select_dimension(session)
        session.status = ASSESSMENT_STATUS_AWAITING
        session.current_dimension = dimension
        asked = list(session.asked_dimensions or [])
        if dimension not in asked:
            asked.append(dimension)
        session.asked_dimensions = asked
        self.db.commit()

        return AssessmentTurnResult(
            assessment_state=self._state(session),
            assessment_prompt_hint=self._build_probe(dimension),
        )

    def is_awaiting_answer(self, user_id: int, chat_session_id: str) -> bool:
        """Return whether the current user message should be treated as an answer."""
        session = self._get_existing_session(user_id, chat_session_id)
        return bool(session and session.status == ASSESSMENT_STATUS_AWAITING)

    def record_user_answer(
        self,
        user_id: int,
        chat_session_id: str,
        user_message: str,
        conversation_id: Optional[int],
    ) -> Optional[AssessmentObservation]:
        """Persist structured signals from a user answer to a prior natural probe."""
        session = self._get_or_create_session(user_id, chat_session_id)
        if session.status not in {ASSESSMENT_STATUS_AWAITING, ASSESSMENT_STATUS_ELIGIBLE}:
            return None

        signals = self.extract_signals(user_message)
        if contains_crisis_signal(user_message):
            session.status = ASSESSMENT_STATUS_CRISIS
        elif self._is_refusal(user_message):
            session.status = ASSESSMENT_STATUS_COOLDOWN
            session.cooldown_until = datetime.now() + timedelta(hours=24)
            self.db.commit()
            return None
        else:
            session.status = ASSESSMENT_STATUS_COMPLETED if self._has_enough_signal(signals) else ASSESSMENT_STATUS_COOLDOWN
            if session.status == ASSESSMENT_STATUS_COOLDOWN:
                session.cooldown_until = datetime.now() + timedelta(hours=24)

        observation = AssessmentObservation(
            assessment_session_id=session.id,
            conversation_id=conversation_id,
            dimension="mixed",
            value=signals,
            confidence=signals.get("confidence", 0.0),
            evidence_text=self._evidence_text(user_message),
            crisis_signal=bool(signals.get("self_harm") or signals.get("suicidal_ideation")),
        )
        self.db.add(observation)
        self.db.commit()
        self.db.refresh(observation)
        return observation

    def extract_signals(self, text: str) -> Dict[str, Any]:
        """Extract structured PMS-related signals without making a diagnosis."""
        normalized = text or ""
        work_interest = self._score(normalized, ["不想工作", "不想学习", "提不起劲", "不想上班", "不想学", "很难开始"])
        home_interest = self._score(normalized, ["不想做家务", "不想收拾", "不想动", "家里的事不想管"])
        social_interest = self._score(normalized, ["不想社交", "不想回消息", "不想见人", "想一个人待着", "不想出门"])
        concentration = self._score(normalized, ["难集中", "注意力", "专注不了", "脑子乱", "看不进去"])
        insomnia = self._score(normalized, ["睡不好", "失眠", "睡不着", "入睡困难", "老醒"])
        hypersomnia = self._score(normalized, ["嗜睡", "睡不醒", "一直想睡", "困得不行"])
        overwhelmed = self._score(normalized, ["失控", "撑不住", "扛不住", "控制不了", "管不住", "事情太多"])
        physical_symptoms = self._score(
            normalized,
            ["乳房胀痛", "乳房痛", "头痛", "腹痛", "腰酸", "水肿", "胀痛", "肚子胀"],
        )
        work_impairment = self._score(normalized, ["效率下降", "工作受影响", "学习受影响", "做不动", "节奏被打乱"])
        coworker_impairment = self._score(normalized, ["同事冲突", "老师冲突", "工作关系受影响"])
        family_impairment = self._score(normalized, ["家人吵", "父母吵", "对象吵", "伴侣吵", "家庭关系受影响"])
        social_impairment = self._score(normalized, ["社交受影响", "取消约", "不想和朋友见面"])
        home_impairment = self._score(normalized, ["家务顾不上", "家里的事顾不上", "责任扛不动"])
        signals: Dict[str, Any] = {
            "irritability": self._score(normalized, ["烦躁", "易怒", "脾气", "一点就炸", "火大"]),
            "anxiety": self._score(normalized, ["焦虑", "紧张", "慌", "担心", "不安"]),
            "tearful": self._score(normalized, ["想哭", "委屈", "敏感", "容易哭"]),
            "depressed": self._score(normalized, ["低落", "没意思", "无力", "开心不起来", "难过"]),
            "work_interest": work_interest,
            "home_interest": home_interest,
            "social_interest": social_interest,
            "concentration": concentration,
            "fatigue": self._score(normalized, ["累", "疲惫", "乏力", "没精神"]),
            "craving": self._score(normalized, ["想吃", "甜", "暴食", "食欲"]),
            "insomnia": insomnia,
            "hypersomnia": hypersomnia,
            "overwhelmed": overwhelmed,
            "physical_symptoms": physical_symptoms,
            "sleep_change": max(insomnia, hypersomnia),
            "pain_or_bloating": max(physical_symptoms, self._score(normalized, ["胀", "痛", "腹痛", "头痛", "腰酸"])),
            "work_impairment": work_impairment,
            "coworker_impairment": coworker_impairment,
            "family_impairment": family_impairment,
            "social_impairment": social_impairment,
            "home_impairment": home_impairment,
            "study_work": max(
                work_interest,
                work_impairment,
                concentration,
                self._score(normalized, ["学习", "工作", "效率", "上班", "做事"]),
            ),
            "social": max(social_interest, social_impairment, self._score(normalized, ["社交", "朋友", "回消息", "见人"])),
            "family": max(family_impairment, self._score(normalized, ["家人", "父母", "对象", "伴侣", "吵"])),
            "self_care": max(home_interest, home_impairment, self._score(normalized, ["不想动", "洗澡", "吃饭", "照顾自己"])),
            "self_harm": any(term in normalized.lower() for term in ["自残", "伤害自己", "self harm"]),
            "suicidal_ideation": contains_crisis_signal(normalized),
        }
        positive_dimensions = sum(
            1
            for key, value in signals.items()
            if key not in {"self_harm", "suicidal_ideation"} and isinstance(value, int) and value > 0
        )
        signals["confidence"] = min(1.0, 0.2 + positive_dimensions * 0.12)
        return signals

    def _get_or_create_session(self, user_id: int, chat_session_id: str) -> AssessmentSession:
        session = self._get_existing_session(user_id, chat_session_id)
        if session:
            return session

        session = AssessmentSession(
            user_id=user_id,
            chat_session_id=chat_session_id,
            status=ASSESSMENT_STATUS_IDLE,
            trigger_source="chat",
            asked_dimensions=[],
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def _get_existing_session(self, user_id: int, chat_session_id: str) -> Optional[AssessmentSession]:
        return (
            self.db.query(AssessmentSession)
            .filter(
                AssessmentSession.user_id == user_id,
                AssessmentSession.chat_session_id == chat_session_id,
            )
            .order_by(AssessmentSession.id.desc())
            .first()
        )

    def _is_triggered(self, message: str, context: Dict[str, Any]) -> bool:
        text = (message or "").lower()
        trigger_terms = ["经前", "月经前", "姨妈前", "烦躁", "胀痛", "失眠", "想哭", "低落"]
        if any(term in text for term in trigger_terms):
            return True
        if (context or {}).get("cycle_phase") in {"luteal", "经前期", "黄体期"}:
            return True
        if (context or {}).get("sentiment_score", 0.0) < -0.35:
            return True
        if (context or {}).get("risk_level") == "medium":
            return True
        return False

    def _is_in_cooldown(self, session: AssessmentSession) -> bool:
        if session.status != ASSESSMENT_STATUS_COOLDOWN or not session.cooldown_until:
            return False
        return session.cooldown_until > datetime.now()

    def _select_dimension(self, session: AssessmentSession) -> str:
        for dimension in ["mood_core", "physical", "function_impact"]:
            if dimension not in (session.asked_dimensions or []):
                return dimension
        return "context"

    def _build_probe(self, dimension: str) -> str:
        probes = self._load_probe_templates()
        return probes.get(dimension, probes["context"])

    def _load_probe_templates(self) -> Dict[str, str]:
        template = load_prompt("assessment_probe_prompt.txt")
        probes: Dict[str, str] = {}
        for raw_line in template.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            probes[key.strip()] = value.strip()
        probes.setdefault("context", "我想更了解一点：这种变化对你影响最大的是什么？")
        return probes

    def _state(self, session: AssessmentSession) -> Dict[str, Any]:
        return {
            "status": session.status or ASSESSMENT_STATUS_IDLE,
            "current_dimension": session.current_dimension,
            "summary_available": session.status == ASSESSMENT_STATUS_COMPLETED,
            "user_visible_label": "状态小结" if session.status == ASSESSMENT_STATUS_COMPLETED else None,
        }

    def _score(self, text: str, keywords: list[str]) -> int:
        if not any(keyword in text for keyword in keywords):
            return 0
        if any(word in text for word in ["特别", "非常", "完全", "严重", "根本"]):
            return 3
        if any(word in text for word in ["明显", "经常", "反复", "挺", "比较"]):
            return 2
        return 2

    def _has_enough_signal(self, signals: Dict[str, Any]) -> bool:
        categories = [
            ["irritability", "anxiety", "tearful", "depressed"],
            ["fatigue", "sleep_change", "craving", "pain_or_bloating"],
            ["study_work", "social", "family", "self_care"],
        ]
        covered = sum(1 for category in categories if any(signals.get(key, 0) > 0 for key in category))
        return covered >= 2

    def _is_refusal(self, text: str) -> bool:
        return any(term in (text or "") for term in ["不想聊", "别问", "不想说", "跳过"])

    def _evidence_text(self, text: str) -> str:
        return (text or "")[:120]
