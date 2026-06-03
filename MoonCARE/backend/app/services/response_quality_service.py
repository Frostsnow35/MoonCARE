import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


class ResponseQualityGuard:
    """Repair high-risk conversational quality failures before showing replies."""

    default_empathy_templates: Dict[str, Any] = {
        "fast_ack": {
            "light_ack": "嗯，我收到啦。\n\n",
            "body_discomfort": "我听到啦，身体不舒服真的会把人往下拽。先安顿一下，不急。\n\n",
            "emotional_distress": "我在，先陪你稳一下。你不用马上解释清楚，可以慢慢说，我会听着。\n\n",
            "relationship_conflict": "我听到了，和亲近的人起冲突后还卡在情绪里，真的会很消耗。\n\n",
            "action_support": "我先陪你把眼前这一步理一下，我们不一下子想很远。\n\n",
            "fatigue": "收到啦，累的时候什么都不用急着做。\n\n",
            "insomnia": "我收到啦，睡不好的夜晚真的很磨人。\n\n",
        },
        "open_disclosure": {
            "default": "我在，你可以慢慢说，不用急着完整。",
            "cycle": "我在，你可以慢慢说，不用急着完整。如果和经前/经期状态有关，我们也只把它当作自我观察参考，不做诊断。",
        },
        "open_questions": [
            "如果你想多说一点，我就听着。",
            "如果愿意，可以先告诉我最难受的那一点。",
        ],
        "safety_note": "以上只作为自我照护参考，不替代医生或专业心理支持。",
    }

    def __init__(self, template_source: Optional[Path] = None):
        self.template_source = template_source or (
            Path(__file__).resolve().parents[1] / "prompts" / "empathy_templates.json"
        )
        self.empathy_templates = self._load_empathy_templates(self.template_source)

    def _load_empathy_templates(self, source: Path) -> Dict[str, Any]:
        """Load empathy templates from backend/app/prompts with a safe fallback."""
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Failed to load empathy templates from %s", source)
            return dict(self.default_empathy_templates)

        if not isinstance(data, dict):
            logger.warning("Empathy template file %s does not contain an object", source)
            return dict(self.default_empathy_templates)
        return data

    def _template(self, section: str, key: str, fallback: str) -> str:
        """Return a loaded template value when present."""
        section_value = self.empathy_templates.get(section)
        if not isinstance(section_value, dict):
            return fallback
        value = section_value.get(key)
        return str(value) if value else fallback

    def ensure_open_question(self, user_message: str, reply: str, state: Dict) -> str:
        """Append one gentle open question for low-risk support replies when missing."""
        text = (reply or "").strip()
        if not text or not self._should_append_open_question(user_message, text, state or {}):
            return reply

        questions = self.empathy_templates.get("open_questions")
        if not isinstance(questions, list) or not questions:
            question = "此刻最需要被我听见的是哪一部分？"
        else:
            question = str(questions[0])
        return f"{text}\n\n{question}"

    def _should_append_open_question(self, user_message: str, reply: str, state: Dict) -> bool:
        """Return whether an open question improves this support reply."""
        if state.get("risk_level") in {"high", "crisis"}:
            return False
        if state.get("agent_mode") == "knowledge":
            return False
        if "?" in reply or "？" in reply:
            return False
        if self._is_body_discomfort(user_message, state):
            return False
        if self._looks_like_action_request(user_message):
            return False
        return True

    def _looks_like_action_request(self, message: str) -> bool:
        """Return whether the user asks for concrete next steps."""
        compact = "".join((message or "").split())
        markers = (
            "我该怎么做",
            "该怎么做",
            "怎么办",
            "怎么做",
            "怎么处理",
            "接下来怎么做",
            "接下来怎么办",
        )
        return any(marker in compact for marker in markers)

    open_disclosure_markers = ("想倾诉", "想聊聊", "想说说", "想跟你说")
    unsupported_negative_terms = (
        "烦躁",
        "爆发",
        "崩溃",
        "很难受",
        "特别难受",
        "痛苦",
        "委屈",
        "伤心",
        "难过",
        "想哭",
        "焦虑",
        "生气",
    )
    emotional_distress_markers = (
        "不开心",
        "烦躁",
        "烦",
        "焦虑",
        "紧张",
        "低落",
        "难过",
        "难受",
        "想哭",
        "委屈",
        "生气",
        "火大",
        "敏感",
        "崩溃",
        "撑不住",
        "心里堵",
    )
    positive_shift_markers = (
        "开心一点",
        "开心了",
        "好一点",
        "好多了",
        "舒服一点",
        "轻松一点",
        "平静一点",
        "稳一点",
        "缓过来",
        "没那么难受",
        "不那么难受",
        "放松一点",
    )
    body_discomfort_markers = (
        "来月经",
        "经期",
        "例假",
        "姨妈",
        "肚子疼",
        "肚子痛",
        "腹痛",
        "痛经",
        "绞痛",
        "腰酸",
        "头痛",
        "乳房胀",
        "恶心",
        "乏力",
    )
    menstrual_context_markers = (
        "经前",
        "经期",
        "月经",
        "例假",
        "姨妈",
        "大姨妈",
        "黄体期",
        "排卵",
        "痛经",
        "PMS",
        "pms",
        "PMDD",
        "pmdd",
    )
    technical_failure_terms = ("模型", "响应", "重试", "稍后再试", "状况", "连接")
    
    # 女性生理相关的不尊重/玩笑内容检测关键词
    menstrual_disrespect_patterns = (
        # 流量相关的玩笑
        "流量控制",
        "流量模式",
        "流量开关",
        "流量管理",
        "放水",
        "洪水",
        "泄洪",
        "大坝",
        "开闸",
        # 痛苦相关的嘲讽
        "矫情",
        "装的",
        "至于吗",
        "有那么痛吗",
        "忍忍就过去了",
        "每个月都来",
        "习惯就好",
        # 贬低性比喻
        "麻烦",
        "晦气",
        "倒霉",
        "脏",
        "恶心",
        # 性化/不尊重的表述
        "大姨妈来了脾气大",
        "经期女人惹不起",
        "PMS发作",
        "激素作祟",
        "情绪不稳定",
        # 不尊重的提问方式
        "为什么经期",
        "为什么来月经",
        "为什么女人",
        "为什么女性",
    )
    
    # 安全的替换回复
    SAFE_RESPONSE_FOR_DISRESPECT = "我理解你现在的感受。让我陪着你，有什么想聊的都可以告诉我。"

    def _is_menstrual_disrespect(self, reply: str) -> bool:
        """检测回复中是否包含对女性生理的不尊重、玩笑或贬低内容"""
        compact = "".join((reply or "").split())
        return any(pattern in compact for pattern in self.menstrual_disrespect_patterns)

    def repair_reply(self, user_message: str, reply: str, state: Dict) -> str:
        """Return a reply that follows the user's actual conversational cue."""
        message = (user_message or "").strip()
        original_reply = (reply or "").strip()
        state = state or {}

        # 首先检测是否包含不尊重内容，如果有，在最前面加"抱歉，晚了一点点"，然后用安全回复
        if self._is_menstrual_disrespect(original_reply):
            # 或者是直接输出安全回复？需要再明确一下用户的需求
            # 按用户说的"重新推理后输出给用户，并在消息最前面说明'抱歉，晚了一点点'"
            # 这里我们先采用：如果检测到不恰当内容，就只输出安全回复，并且前面加说明
            return f"抱歉，晚了一点点。{self.SAFE_RESPONSE_FOR_DISRESPECT}"

        original_reply = self._dedupe_sentences(original_reply)

        if self._is_emotional_distress(message) and self._overdirects_emotional_distress(message, original_reply):
            return self._emotional_distress_reply(message, state)

        if self._is_open_disclosure(message) and self._overreads_open_disclosure(original_reply):
            return self._open_disclosure_reply(state)

        if self._is_partner_invalidation(message) and not self._addresses_partner_invalidation(original_reply):
            return self._partner_invalidation_reply(state)

        if self._is_positive_shift(message) and (
            self._is_technical_or_thin_reply(original_reply)
            or self._overreads_positive_shift(message, original_reply)
        ):
            return self._positive_shift_reply(message, state)

        stale_support_terms = ("消耗掉一点", "被看见", "愿意说说看", "更像什么感觉")
        if self._is_body_discomfort(message, state) and any(term in original_reply for term in stale_support_terms):
            return self._body_discomfort_reply(message, state)

        if self._is_emotional_distress(message) and any(term in original_reply for term in stale_support_terms):
            return self._emotional_distress_reply(message, state)

        if self._is_body_discomfort(message, state) and self._is_technical_or_thin_reply(original_reply):
            return self._body_discomfort_reply(message, state)

        if self._is_emotional_distress(message) and self._is_technical_or_thin_reply(original_reply):
            return self._emotional_distress_reply(message, state)

        return original_reply

    def is_quality_sensitive_turn(self, user_message: str) -> bool:
        """Return whether deterministic topic following is safer than cache reuse."""
        message = (user_message or "").strip()
        return (
            self._is_open_disclosure(message)
            or self._is_partner_invalidation(message)
            or self._is_positive_shift(message)
            or self._is_body_discomfort(message, {})
            or self._is_emotional_distress(message)
        )

    def direct_reply_if_applicable(self, user_message: str, state: Dict) -> str:
        """Return a deterministic reply for short high-risk-quality turns."""
        message = (user_message or "").strip()
        if self._is_knowledge_question(message):
            return ""

        # Tier 1: 轻承接 — very short disclosures, ack without questions
        if self._is_single_word_disclosure(message):
            return self._light_ack_reply(message, state or {})

        # Tier 3: 共情展开 — complete narratives with specific context
        if self._is_relationship_conflict(message):
            return self._empathy_expansion_reply(message, state or {}, "relationship_conflict")
        if self._is_contextual_irritability(message, state or {}):
            return self._empathy_expansion_reply(message, state or {}, "contextual_irritability")
        if self._is_partner_invalidation(message):
            return self._empathy_expansion_reply(message, state or {}, "partner_invalidation")

        # Tier 2: 开放邀请 — incomplete emotional/physical expressions
        if self._is_open_disclosure(message):
            return self._open_invitation_reply(message, state or {}, "open_disclosure")
        if self._is_positive_shift(message):
            return self._positive_shift_reply(message, state or {})
        if self._is_body_discomfort(message, state or {}):
            return self._open_invitation_reply(message, state or {}, "body_discomfort")
        if self._is_fatigue(message):
            return self._open_invitation_reply(message, state or {}, "fatigue")
        if self._is_insomnia(message):
            return self._open_invitation_reply(message, state or {}, "insomnia")
        if self._is_emotional_distress(message):
            return self._open_invitation_reply(message, state or {}, "emotional_distress")
        return ""

    def fast_ack_if_applicable(self, user_message: str, state: Dict) -> str:
        """Return a short first token for sensitive support turns before model continuation."""
        message = (user_message or "").strip()
        if self._is_knowledge_question(message) or self._is_open_disclosure(message):
            return ""
        if not self._should_fast_ack(message, state or {}):
            return ""

        # Tier 1: 轻承接 — very short disclosures get minimal ack
        if self._is_single_word_disclosure(message):
            return self._template("fast_ack", "light_ack", "嗯，我收到啦。\n\n")

        # Tier 3: 共情展开 — complete narratives
        if self._is_relationship_conflict(message):
            return self._template(
                "fast_ack",
                "relationship_conflict",
                "我听到了，和亲近的人起冲突后还卡在情绪里，真的会很消耗。\n\n",
            )

        # Tier 2: 开放邀请 — incomplete expressions
        if self._has_real_body_discomfort(message, state or {}):
            return self._template(
                "fast_ack",
                "body_discomfort",
                "我听到啦，身体不舒服真的会把人往下拽。先安顿一下，不急。\n\n",
            )
        if self._is_fatigue(message):
            return self._template(
                "fast_ack",
                "fatigue",
                "收到啦，累的时候什么都不用急着做。\n\n",
            )
        if self._is_insomnia(message):
            return self._template(
                "fast_ack",
                "insomnia",
                "我收到啦，睡不好的夜晚真的很磨人。\n\n",
            )
        if self._has_real_emotional_distress(message):
            return self._template(
                "fast_ack",
                "emotional_distress",
                "我在，先陪你稳一下。你不用马上解释清楚，可以慢慢说，我会听着。\n\n",
            )
        return ""

    def action_ack_if_applicable(self, user_message: str, state: Dict) -> str:
        """Return a short first token for explicit next-step requests."""
        message = (user_message or "").strip()
        if not self._looks_like_action_request(message):
            return ""
        if self._is_knowledge_question(message):
            return ""
        if (state or {}).get("risk_level") in {"high", "crisis"}:
            return ""
        return self._template(
            "fast_ack",
            "action_support",
            "我先陪你把眼前这一步理一下，我们不一下子想很远。\n\n",
        )

    def _is_first_support_disclosure(self, state: Dict) -> bool:
        """Return whether this is the first user disclosure in the visible session context."""
        messages = state.get("conversation_messages") or []
        previous_user_turns = [
            item for item in messages
            if isinstance(item, dict) and item.get("role") == "user" and item.get("content")
        ]
        return len(previous_user_turns) == 0

    def _should_fast_ack(self, message: str, state: Dict) -> bool:
        """Return whether to send fast_ack, preventing overuse in multi-turn conversations."""
        messages = state.get("conversation_messages") or []
        previous_user_turns = [
            item for item in messages
            if isinstance(item, dict) and item.get("role") == "user" and item.get("content")
        ]

        if len(previous_user_turns) == 0:
            return True

        last_user_content = (previous_user_turns[-1].get("content") or "").strip()
        already_in_support = (
            self._has_real_emotional_distress(last_user_content)
            or self._has_real_body_discomfort(last_user_content, state)
            or self._is_relationship_conflict(last_user_content)
        )
        return not already_in_support

    def _has_real_emotional_distress(self, message: str) -> bool:
        """Detect normal Chinese emotional disclosure even when legacy mojibake keywords miss it."""
        compact = "".join((message or "").split())
        markers = (
            "不开心", "难过", "伤心", "委屈", "想哭", "焦虑", "紧张", "不安", "烦躁", "烦", "生气",
            "低落", "崩溃", "撑不住", "心里堵", "压力大", "害怕", "孤单", "无助",
        )
        return any(marker in compact for marker in markers)

    def _has_real_body_discomfort(self, message: str, state: Dict) -> bool:
        """Detect normal Chinese menstrual/body discomfort for immediate acknowledgement."""
        compact = "".join((message or "").split())
        markers = (
            "来月经", "经期", "姨妈", "例假", "肚子疼", "肚子痛", "小腹痛", "腹痛",
            "痛经", "头痛", "头晕", "腰酸", "恶心", "乏力", "没力气", "睡不着",
        )
        support_context = (state or {}).get("support_context") or {}
        return any(marker in compact for marker in markers) or bool(support_context.get("body_signals"))

    def _is_fatigue(self, message: str) -> bool:
        """Return whether the user expresses fatigue or exhaustion."""
        compact = "".join((message or "").split())
        if len(compact) > 48:
            return False
        markers = ("好累", "没力气", "没精神", "疲惫", "累死了", "好疲惫", "浑身没劲", "没劲儿")
        return any(marker in compact for marker in markers)

    def _is_insomnia(self, message: str) -> bool:
        """Return whether the user expresses sleep difficulty."""
        compact = "".join((message or "").split())
        if len(compact) > 48:
            return False
        markers = ("睡不着", "失眠", "睡不好", "没睡好", "醒了好几次", "半夜醒了", "熬夜", "睡不踏实")
        return any(marker in compact for marker in markers)

    def _is_single_word_disclosure(self, message: str) -> bool:
        """Return whether the user sent a very short emotional/physical disclosure needing light ack only."""
        compact = "".join((message or "").split())
        if len(compact) > 6:
            return False
        # Messages referencing specific body parts have enough context for
        # category-specific handling — don't short-circuit to light ack.
        body_parts = ("肚子", "头", "腰", "小腹", "胃")
        if any(part in compact for part in body_parts):
            return False
        markers = (
            "难受", "困", "烦", "累", "疼", "痛", "闷", "慌",
            "不开心", "想哭", "好烦", "好累", "好痛", "好闷", "好困", "好慌",
            "不舒服", "很难受", "心累", "好难过", "好想哭", "好疼",
        )
        return any(marker in compact for marker in markers)

    def _dedupe_sentences(self, reply: str) -> str:
        """Remove exact repeated sentences while preserving the first occurrence."""
        text = (reply or "").strip()
        if not text:
            return ""

        parts = re.findall(r"[^。！？!?；;\n]+[。！？!?；;]?", text)
        if len(parts) <= 1:
            return text

        seen = set()
        kept = []
        for part in parts:
            sentence = part.strip()
            if not sentence:
                continue
            normalized = re.sub(r"\s+", "", sentence).strip("。！？!?；;")
            if normalized in seen:
                continue
            seen.add(normalized)
            kept.append(sentence)

        return "".join(kept).strip()

    def _is_open_disclosure(self, message: str) -> bool:
        """Return whether the user is only opening a space to talk."""
        compact = "".join(message.split())
        return len(compact) <= 12 and any(marker in compact for marker in self.open_disclosure_markers)

    def _overreads_open_disclosure(self, reply: str) -> bool:
        """Return whether the reply invents strong emotions not present in the user text."""
        return any(term in reply for term in self.unsupported_negative_terms)

    def _is_emotional_distress(self, message: str) -> bool:
        """Return whether the user directly names a current emotion needing immediate support."""
        compact = "".join((message or "").split())
        if len(compact) > 36:
            return False
        return any(marker in compact for marker in self.emotional_distress_markers)

    def _is_contextual_irritability(self, message: str, state: Dict) -> bool:
        """Return whether a longer turn describes irritability needing local support."""
        compact = "".join((message or "").split())
        if not any(marker in compact for marker in ("烦躁", "烦", "易怒", "火大", "生气")):
            return False
        if len(compact) > 120:
            return False
        support_context = (state or {}).get("support_context") or {}
        return (
            any(marker in compact for marker in ("快来了", "快来月经", "经前", "姨妈", "这段时间", "不知道为什么"))
            or support_context.get("menstrual_related")
            or "irritable" in (support_context.get("emotion_signals") or [])
        )

    def _is_relationship_conflict(self, message: str) -> bool:
        """Return whether the user is describing conflict with a close person."""
        compact = "".join((message or "").split())
        person_markers = ("男朋友", "对象", "伴侣", "老公", "女朋友", "朋友", "家人", "妈妈", "爸爸")
        conflict_markers = ("吵架", "讲几句话", "说几句", "冷战", "生气", "烦", "矛盾", "不理解", "指责", "惹")
        if len(compact) > 140:
            return False
        return any(marker in compact for marker in person_markers) and any(
            marker in compact for marker in conflict_markers
        )

    def _is_ambiguous_distress(self, message: str) -> bool:
        """Return whether the user gives discomfort without naming a clear emotion."""
        compact = "".join((message or "").split())
        ambiguous_markers = ("难受", "不舒服", "心里堵", "有点堵", "堵得慌", "闷", "胸口闷")
        explicit_emotion_markers = (
            "低落",
            "难过",
            "伤心",
            "委屈",
            "焦虑",
            "紧张",
            "生气",
            "烦躁",
            "烦",
            "想哭",
        )
        return any(marker in compact for marker in ambiguous_markers) and not any(
            marker in compact for marker in explicit_emotion_markers
        )

    def _mentions_menstrual_context(self, message: str) -> bool:
        """Return whether the user explicitly brought up menstrual context this turn."""
        compact = "".join((message or "").split())
        return any(marker in compact for marker in self.menstrual_context_markers)

    def _overdirects_emotional_distress(self, message: str, reply: str) -> bool:
        """Detect replies that label, instruct, or medicalize too early."""
        compact_reply = "".join((reply or "").split())
        if self._is_ambiguous_distress(message) and any(term in compact_reply for term in ("低落", "抑郁", "焦虑", "烦躁")):
            return True
        pressure_terms = ("压下去", "解释清楚", "不用急着", "不要急着", "必须", "应该")
        if any(term in compact_reply for term in pressure_terms):
            return True
        if not self._mentions_menstrual_context(message) and any(
            term in compact_reply for term in ("经前", "经期", "月经", "诊断", "仅供参考")
        ):
            return True
        closed_prompt = "被人惹到了、身体不舒服，还是事情太多"
        over_questioning_terms = ("更像什么感觉", "什么样的难受", "愿意说说看")
        return closed_prompt in compact_reply or any(term in compact_reply for term in over_questioning_terms)

    def _is_knowledge_question(self, message: str) -> bool:
        """Return whether a short message is primarily asking for an explanation."""
        compact = "".join((message or "").split())
        question_markers = ("为什么", "什么是", "怎么回事", "原因", "会不会", "正常吗", "是不是", "如何", "怎么办")
        health_context_markers = ("经前", "经期", "月经", "姨妈", "PMS", "pms", "PMDD", "pmdd", "激素", "周期")
        return any(marker in compact for marker in question_markers) and (
            any(marker in compact for marker in health_context_markers) or "？" in compact or "?" in compact
        )

    def _is_positive_shift(self, message: str) -> bool:
        """Return whether the user reports a small improvement that should be reinforced."""
        compact = "".join((message or "").split())
        if len(compact) > 36:
            return False
        return any(marker in compact for marker in self.positive_shift_markers)

    def _overreads_positive_shift(self, message: str, reply: str) -> bool:
        """Return whether a reply turns a small improvement into pressure or invented distress."""
        compact_message = "".join((message or "").split())
        compact_reply = "".join((reply or "").split())
        invented_negative = any(
            term in compact_reply and term not in compact_message
            for term in self.unsupported_negative_terms
        )
        pressure_terms = ("一直保持", "必须开心", "应该开心", "已经过去了吗", "之前感到")
        return invented_negative or any(term in compact_reply for term in pressure_terms)

    def _is_body_discomfort(self, message: str, state: Dict) -> bool:
        """Return whether the user is naming menstrual or body discomfort."""
        compact = "".join((message or "").split())
        support_context = (state or {}).get("support_context") or {}
        body_signals = support_context.get("body_signals") or []
        if len(compact) <= 48 and any(marker in compact for marker in self.body_discomfort_markers):
            return True
        return bool(body_signals) and len(compact) <= 48

    def _has_urgent_body_signal(self, message: str) -> bool:
        """Return whether body symptoms need a safety-first medical nudge."""
        compact = "".join((message or "").split())
        urgent_markers = (
            "疼得受不了",
            "痛得受不了",
            "疼得厉害",
            "痛得厉害",
            "特别疼",
            "剧痛",
            "出血异常",
            "血很多",
            "头晕得厉害",
            "头晕很厉害",
            "站不稳",
            "晕倒",
            "发烧",
            "和平时不一样",
            "越来越严重",
        )
        return any(marker in compact for marker in urgent_markers)

    def _conversation_messages(self, state: Dict) -> list[Dict[str, str]]:
        """Return bounded prior conversation messages from the attached context."""
        messages = (state or {}).get("conversation_messages") or []
        return [item for item in messages if isinstance(item, dict)]

    def _last_role_content(self, state: Dict, role: str) -> str:
        """Return the latest prior message content for one role."""
        for item in reversed(self._conversation_messages(state)):
            if item.get("role") == role and item.get("content"):
                return str(item.get("content") or "")
        return ""

    def _previous_body_context(self, state: Dict) -> str:
        """Extract a small human-readable body context from recent user turns."""
        for item in reversed(self._conversation_messages(state)):
            if item.get("role") != "user":
                continue
            content = str(item.get("content") or "")
            compact = "".join(content.split())
            if not compact:
                continue
            if any(marker in compact for marker in ("来月经", "经期", "例假", "姨妈")):
                if "身体不舒服" in compact or "不舒服" in compact:
                    return "来月经了、身体不舒服"
                return "来月经这件事"
            if any(marker in compact for marker in self.body_discomfort_markers):
                return self._truncate_context_phrase(content)
        return ""

    def _truncate_context_phrase(self, text: str, limit: int = 24) -> str:
        """Keep a prior user phrase short enough for a conversational reply."""
        compact = " ".join((text or "").split())
        if len(compact) <= limit:
            return compact
        return f"{compact[: limit - 1]}…"

    def _is_pain_follow_up(self, message: str) -> bool:
        """Return whether this turn intensifies a previous body-discomfort thread."""
        compact = "".join((message or "").split())
        pain_terms = ("痛", "疼", "绞痛", "坠胀")
        follow_terms = ("真的", "还是", "更", "很", "越来越", "又", "现在")
        return any(term in compact for term in pain_terms) and (
            any(term in compact for term in follow_terms) or len(compact) <= 12
        )

    def _is_technical_or_thin_reply(self, reply: str) -> bool:
        """Return whether a reply exposes runtime state or fails to offer real support."""
        compact = "".join((reply or "").split())
        if not compact:
            return True
        return any(term in compact for term in self.technical_failure_terms)

    def _named_emotion(self, message: str, state: Dict) -> str:
        """Use only emotions the user or perception layer has actually surfaced."""
        if "不开心" in message:
            return "不开心"
        if "烦" in message or "火大" in message or "生气" in message:
            return "烦躁"
        if "焦虑" in message or "紧张" in message or "不安" in message:
            return "焦虑"
        if "想哭" in message or "委屈" in message:
            return "委屈"
        if "低落" in message or "难过" in message or "难受" in message:
            return "低落"

        support_context = (state or {}).get("support_context") or {}
        emotion_signals = support_context.get("emotion_signals") or []
        if "irritable" in emotion_signals:
            return "烦躁"
        if "anxious" in emotion_signals:
            return "焦虑"
        if "tearful" in emotion_signals:
            return "委屈"
        if "sad" in emotion_signals:
            return "低落"
        return "这种感受"

    def _clear_emotional_context_reply(self, message: str, emotion: str) -> str:
        """Return support that follows a concrete event without asking again."""
        compact = "".join((message or "").split())
        relationship_reply = self._relationship_conflict_reply(message, {})
        if relationship_reply:
            return relationship_reply
        return ""

    def _relationship_conflict_reply(self, message: str, state: Dict) -> str:
        """Return support for relationship conflict without generic breathing advice."""
        compact = "".join((message or "").split())
        if "男朋友" in compact and "吵架" in compact:
            return (
                "我听到了，和男朋友吵架后还卡在情绪里，确实会又委屈又累。"
                "这不是小题大做，亲近的人一句话有时候比外人的话更容易刺到。"
                "我会先站在你这边陪你缓一下；先别急着继续解释或证明自己，可以先说说，他哪句话最让你难受。"
            )
        if "男朋友" in compact:
            return (
                "我听到了，男朋友讲几句话你就烦，后面他生气、你又自责，这种夹在中间的感觉很消耗。"
                "这不等于你故意发脾气，可能是这段时间身体和情绪本来就更容易被点着。"
                "我们先不急着判谁对谁错；你可以先说说，他刚刚哪句话或哪个语气最触发你。"
            )
        return ""

    def _contextual_irritability_reply(self, message: str, state: Dict) -> str:
        """Return a quick local reply for menstrual irritability without model latency."""
        cycle_note = ""
        if self._mentions_menstrual_context(message) or (state or {}).get("cycle_phase") in {"经前期", "黄体期"}:
            cycle_note = "如果这正好在经前或快来月经的阶段，它可能和睡眠、压力、身体不适、激素波动叠在一起；这只是自我观察，不是诊断。"
        return (
            "我听到了，你不是单纯“脾气差”，而是这段时间一点刺激都更容易被放大。"
            f"{cycle_note}"
            "先别急着压住它，我们先找触发点：刚刚是某句话、某个语气，还是事情堆在一起让你一下子烦起来？"
        )

    def _cycle_note(self, state: Dict, message: str = "") -> str:
        """Return a non-diagnostic menstrual-context note woven into a caring tone."""
        if self._mentions_menstrual_context(message) or (state or {}).get("cycle_phase"):
            return (
                "我只是根据你的描述陪着你感受，"
                "如果身体有和平时很不一样的信号，帮你把关的还是医生呀🩺。"
            )
        return ""

    def _positive_shift_reply(self, message: str, state: Dict) -> str:
        """Reinforce a small emotional improvement without over-directing the user."""
        return (
            "我听见了，你感觉开心一点了。这个小小的变好也值得被认真接住，不用急着把它放大成“必须一直开心”。"
            "我们可以轻轻看一眼：刚才是什么让它出现了一点点？"
            f"{self._cycle_note(state, message)}"
        )

    def _body_discomfort_reply(self, message: str, state: Dict) -> str:
        """Witness menstrual/body discomfort before moving into advice."""
        compact = "".join((message or "").split())
        if self._has_urgent_body_signal(compact):
            return (
                "我听到啦，这种不舒服听起来已经很难靠自己硬扛了。"
                "先让身边可信任的人知道，同时尽快联系医生或当地急诊；我这里不能替代医生判断，但会陪你把当下稳住。"
                "先坐下或躺好，别一个人硬撑着。"
            )

        previous_body_context = self._previous_body_context(state)
        if previous_body_context and self._is_pain_follow_up(compact):
            quoted_message = self._truncate_context_phrase(message, 20)
            return (
                f"我接上了，刚才你说{previous_body_context}，现在这句“{quoted_message}”听起来是在同一份不舒服里继续往下走。"
                "这真的很折磨人，先把身体放到最省力的位置，能热敷就轻轻热敷一下。"
                "我会陪你把这一阵慢慢撑过去 🫶"
            )

        if "头晕" in compact and any(term in compact for term in ("小腹", "肚子", "腹痛", "痛", "疼")):
            return (
                "我听到啦，来月经时头晕、小腹痛真的很不好受。"
                "先坐下或躺一会儿，能热敷就轻轻热敷小腹，慢慢喝一点温水。"
                "如果头晕明显、站不稳或出血异常，要尽快联系身边人和医生哦。"
            )

        if "来月经" in compact or "经期" in compact or "例假" in compact or "姨妈" in compact:
            felt_sense = "来月经的时候身体不舒服"
        elif "肚子疼" in compact or "肚子痛" in compact or "腹痛" in compact or "痛经" in compact or "绞痛" in compact:
            felt_sense = "肚子疼"
        elif "头痛" in compact:
            felt_sense = "头痛"
        elif "腰酸" in compact:
            felt_sense = "腰酸"
        else:
            felt_sense = "身体不舒服"

        return (
            f"我听到啦，{felt_sense}真的不好受，也很容易让人没力气。"
            "先把身体放到舒服一点的位置，喝一点温水或靠着休息一下。"
            "我会在这里陪你慢慢稳下来 🫶"
        )

    def _emotional_distress_reply(self, message: str, state: Dict) -> str:
        """Immediate support for short emotional disclosures without waiting for the model."""
        emotion = self._named_emotion(message, state)
        clear_context_reply = self._clear_emotional_context_reply(message, emotion)
        if clear_context_reply:
            return clear_context_reply

        if self._is_ambiguous_distress(message):
            return (
                "我在。现在像是心里堵着，或者身体也有点不舒服。"
                "先不用急着分清是哪一种；如果你愿意，就从现在最难受的那一点开始说。"
            )

        first_sentence = f"我在，也听到你现在{emotion}。"
        cycle_note = self._cycle_note(state, message)
        invitation = "如果你愿意，可以先告诉我，刚刚哪一下最让你难受。"
        if cycle_note:
            invitation = f"{cycle_note}{invitation}"
        return f"{first_sentence}先不用急着把原因讲清楚；{invitation}"

    def _fatigue_reply(self, message: str, state: Dict) -> str:
        """Gentle acknowledgment for fatigue without pushing for action."""
        return (
            "我听到了，累的时候什么都不用急着做，也不用急着解释为什么累。"
            "先在这儿靠一会儿，能靠多久靠多久。"
            "如果愿意，可以跟我说说，是身体累更多，还是心里累更多。"
        )

    def _insomnia_reply(self, message: str, state: Dict) -> str:
        """Gentle support for sleep difficulty without sleep hygiene lectures."""
        return (
            "我听到了，睡不着的夜晚真的很磨人——身体很累，脑子却停不下来。"
            "不用急着睡着，也不用数羊，我在这儿陪你说说话。"
            "如果愿意，可以告诉我，是脑子里在想什么，还是身体哪里不舒服让你睡不着。"
        )

    def _light_ack_reply(self, message: str, state: Dict) -> str:
        """Light acknowledgment for very short disclosures — no questions, just presence."""
        compact = "".join((message or "").split())
        if "困" in compact or "累" in compact or "没力气" in compact or "没精神" in compact:
            return "嗯，我收到啦。没力气也没关系，它现在就在这儿，我也在这儿，不急。"
        if "痛" in compact or "疼" in compact:
            return "嗯，我收到啦。疼的时候真的很难熬，它现在就在这儿，我也在这儿陪着。不急。"
        return "嗯，我收到啦。这种感觉沉沉的，让人没力气。它现在就在这儿，我也在这儿，不急。"

    def _open_invitation_reply(self, message: str, state: Dict, category: str) -> str:
        """Open invitation for incomplete emotional/physical expression: acknowledge weight, leave optional hook."""
        emotion = self._named_emotion(message, state or {})

        if category == "body_discomfort":
            compact = "".join((message or "").split())

            if self._has_urgent_body_signal(compact):
                return (
                    "我听到啦，这种不舒服听起来已经很难靠自己硬扛了。"
                    "先让身边可信任的人知道，同时尽快联系医生或当地急诊；"
                    "我这里不能替代医生判断，但会陪你把当下稳住。"
                    "先坐下或躺好，别一个人硬撑着。"
                )

            previous_body_context = self._previous_body_context(state or {})
            if previous_body_context and self._is_pain_follow_up(compact):
                quoted_message = self._truncate_context_phrase(message, 20)
                return (
                    f"我接上了，刚才你说{previous_body_context}，"
                    f'现在这句\u201c{quoted_message}\u201d听起来是在同一份不舒服里继续往下走。'
                    "这真的很折磨人，先把身体放到最省力的位置。"
                    "如果你想多说一点，我就听着；不想说的话，我们就这样先安顿下来。"
                )

            if "来月经" in compact or "经期" in compact or "例假" in compact or "姨妈" in compact:
                body_phrase = "来月经的时候身体不舒服"
            elif "肚子疼" in compact or "肚子痛" in compact or "腹痛" in compact or "痛经" in compact or "绞痛" in compact:
                body_phrase = "肚子疼"
            elif "头痛" in compact:
                body_phrase = "头痛"
            elif "腰酸" in compact:
                body_phrase = "腰酸"
            else:
                body_phrase = "身体不舒服"
            disclaimer = self._cycle_note(state or {}, message)
            return (
                f"我听到啦，{body_phrase}真的不好受，整个人都像被往下拽。"
                f"你先找个舒服的位置安顿下来。"
                f"如果你想多说一点，我就听着；不想说的话，我们就这么安静待一会儿。"
                f"{disclaimer}"
            )

        if category in ("fatigue",):
            return (
                "累的时候整个人都像被往下拽。"
                "我记住了。如果你想多说一点，我就听着；不想说的话，先靠一会儿也没关系。"
            )

        if category in ("insomnia",):
            return (
                "睡不好的夜晚真的很磨人——身体很累，脑子却停不下来。"
                "我记住了。如果你想多说一点，我就听着；不想说话的话，我们就这样安静待一会儿。"
            )

        if category in ("open_disclosure",):
            return (
                "我在，你可以慢慢说，不用急着完整。"
                "如果你想多说一点，我就听着；不想说的话，我们就先这么待一会儿。"
            )

        # emotional_distress or generic
        emotion_desc = self._emotion_sensation(emotion)
        return (
            f"我在，也听到你现在{emotion}。{emotion_desc}"
            "如果你想多说一点，我就听着；不想说的话，我们就这么安静待一会儿。"
        )

    def _emotion_sensation(self, emotion: str) -> str:
        """Return a brief physical/emotional sensation descriptor for the given emotion."""
        sensations = {
            "低落": "心里像蒙了一层灰，有点透不过气。",
            "焦虑": "胸口闷闷的，总觉得有什么悬着放不下来。",
            "烦躁": "像有一团小火苗堵在胸口，碰哪都不对劲。",
            "委屈": "明明很难受，又怕别人觉得不至于。",
            "害怕": "心悬在嗓子眼，不知道该往哪里放。",
            "愤怒": "一口气堵在胸口，怎么都顺不下去。",
            "疲惫": "整个人像被抽空了力气。",
            "这种感受": "这种感觉沉沉的，让人没力气。",
        }
        return sensations.get(emotion, sensations["这种感受"])

    def _empathy_expansion_reply(self, message: str, state: Dict, category: str) -> str:
        """Empathy expansion for complete narratives: reflect back the emotional core."""
        emotion = self._named_emotion(message, state or {})
        extraction = self._extract_emotional_core(message)

        if category == "relationship_conflict":
            disclaimer = self._cycle_note(state or {}, message)
            return (
                f"所以是{extraction}，对吗？"
                "和亲近的人起冲突之后还卡在情绪里，真的会很消耗。"
                f"{disclaimer}"
            )

        if category == "contextual_irritability":
            cycle_note = self._cycle_note(state or {}, message)
            return (
                f"所以是{extraction}，对吗？"
                '这种感觉不是单纯"脾气差"，而是一点刺激都更容易被放大。'
                f"{cycle_note}"
                "先别急着压住它，我们慢慢看一眼：刚才是什么让它出现的？"
            )

        if category == "partner_invalidation":
            return (
                f"所以是{extraction}，对吗？"
                "明明不是小事，对方一句'至于吗'，就像一盆冷水泼过来。"
                "这种感觉真的很消耗人。"
            )

        # generic
        return (
            f"所以是{extraction}，对吗？"
            f"这种感觉真的会把人消耗得很空。"
        )

    def _extract_emotional_core(self, message: str) -> str:
        """Extract a short core phrase from the user's message for empathy reflection."""
        compact = "".join((message or "").split())
        max_len = min(len(compact), 24)

        # prefer the last clause that contains emotion markers
        markers = ["烦", "难受", "委屈", "焦虑", "害怕", "生气", "难过", "累", "痛", "疼", "不开心"]
        last_pos = -1
        for marker in markers:
            pos = compact.rfind(marker, 0, max_len)
            if pos > last_pos:
                last_pos = pos

        if last_pos >= 0:
            start = max(0, last_pos - 8)
            end = min(len(compact), last_pos + 8)
            core = compact[start:end].strip()
            return core

        return compact[:max_len].strip() or "这种感觉"

    def _open_disclosure_reply(self, state: Dict) -> str:
        """A neutral invitation that does not add unspoken emotion."""
        cycle_phase = state.get("cycle_phase", "")
        if cycle_phase in {"经前期", "经期", "黄体期", "月经期"}:
            return self._template(
                "open_disclosure",
                "cycle",
                "我在，你可以慢慢说，不用急着完整。你愿意把今天最想被听见的一句话先放在这里吗？如果和经前/经期状态有关，我们也只把它当作自我观察参考，不做诊断。",
            )
        return self._template(
            "open_disclosure",
            "default",
            "我在，你可以慢慢说，不用急着完整。你愿意把今天最想被听见的一句话先放在这里吗？",
        )

    def _is_partner_invalidation(self, message: str) -> bool:
        """Return whether the user reports partner invalidation around being dramatic."""
        return "男朋友" in message and "矫情" in message

    def _addresses_partner_invalidation(self, reply: str) -> bool:
        """Return whether the reply visibly follows the concrete partner topic."""
        return ("男朋友" in reply or "亲近的人" in reply) and "矫情" in reply

    def _partner_invalidation_reply(self, state: Dict) -> str:
        """A topic-following fallback for partner invalidation."""
        cycle_phase = state.get("cycle_phase", "")
        cycle_note = ""
        if cycle_phase in {"经前期", "经期", "黄体期", "月经期"}:
            cycle_note = "如果这几天正好在经前/经期，身体和情绪可能会更敏感一些，但这仅供参考，不是诊断。"
        else:
            cycle_note = "如果这和经前/经期状态有重叠，也可以一起观察一下，但这仅供参考，不是诊断。"
        return (
            "男朋友一直说你矫情，这句话本身就很容易让人觉得不被理解；"
            "这不代表你就是矫情。"
            f"{cycle_note}你愿意说说，他通常是在什么情况下这么说你吗？"
        )
