import re
from typing import Dict


class ResponseQualityGuard:
    """Repair high-risk conversational quality failures before showing replies."""

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

    def repair_reply(self, user_message: str, reply: str, state: Dict) -> str:
        """Return a reply that follows the user's actual conversational cue."""
        message = (user_message or "").strip()
        original_reply = (reply or "").strip()
        state = state or {}

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
        if self._is_open_disclosure(message):
            return self._open_disclosure_reply(state or {})
        if self._is_partner_invalidation(message):
            return self._partner_invalidation_reply(state or {})
        if self._is_positive_shift(message):
            return self._positive_shift_reply(message, state or {})
        if self._is_body_discomfort(message, state or {}):
            return self._body_discomfort_reply(message, state or {})
        if self._is_emotional_distress(message):
            return self._emotional_distress_reply(message, state or {})
        return ""

    def fast_ack_if_applicable(self, user_message: str, state: Dict) -> str:
        """Return a short first token for sensitive support turns before model continuation."""
        message = (user_message or "").strip()
        if self._is_knowledge_question(message) or self._is_open_disclosure(message):
            return ""
        if not self._is_first_support_disclosure(state or {}):
            return ""
        if self._has_real_body_discomfort(message, state or {}):
            return "我在，先别硬撑。你可以先把身体放到舒服一点的位置，我们慢慢来。\n\n"
        if self._has_real_emotional_distress(message):
            return "我在，先陪你稳一下。你不用马上解释清楚，可以慢慢说，我会听着。\n\n"
        return ""

    def _is_first_support_disclosure(self, state: Dict) -> bool:
        """Return whether this is the first user disclosure in the visible session context."""
        messages = state.get("conversation_messages") or []
        previous_user_turns = [
            item for item in messages
            if isinstance(item, dict) and item.get("role") == "user" and item.get("content")
        ]
        return len(previous_user_turns) == 0

    def _has_real_emotional_distress(self, message: str) -> bool:
        """Detect normal Chinese emotional disclosure even when legacy mojibake keywords miss it."""
        compact = "".join((message or "").split())
        markers = (
            "难过", "伤心", "委屈", "想哭", "焦虑", "紧张", "不安", "烦躁", "烦", "生气",
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
        if "男朋友" in compact and "吵架" in compact:
            return (
                f"我听到啦，和男朋友吵架后的{emotion}真的会很扎心。"
                "这不是你在小题大做，是那一刻确实需要有人站在你这边。"
                "先抱抱自己、慢慢呼一口气，我会陪你把这团情绪一点点放下来 💗"
            )
        if "男朋友" in compact:
            return (
                f"我听到啦，和男朋友有关的这份{emotion}很真实。"
                "你不用马上证明自己为什么难受，先让自己靠稳一点。"
                "我会站在你这边，陪你慢慢把这件事理顺 💗"
            )
        return ""

    def _cycle_note(self, state: Dict, message: str = "") -> str:
        """Return a non-diagnostic menstrual-context note when relevant."""
        if self._mentions_menstrual_context(message):
            return "如果它和姨妈前后有重叠，我们可以先把它当作一个小观察记下来；这只是自我观察，不是诊断啦。"
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
                "我听到啦，现在好像是心里或身体有哪里不太舒服。"
                "这份感觉可以先慢慢放在这里，我们不赶时间。"
                "我会陪你稳一小会儿，先不用把它整理成很完整的话 🌷"
            )
        else:
            first_sentence = f"我听到啦，这份{emotion}是真的不好受。"

        cycle_note = self._cycle_note(state, message)
        return (
            f"{first_sentence}"
            "先让自己靠稳一点，慢慢呼一口气。"
            f"{cycle_note}"
            "我会陪你把这股情绪一点点放下来 🌷"
        )

    def _open_disclosure_reply(self, state: Dict) -> str:
        """A neutral invitation that does not add unspoken emotion."""
        cycle_phase = state.get("cycle_phase", "")
        if cycle_phase in {"经前期", "经期", "黄体期", "月经期"}:
            return "我在，你可以慢慢说，不用一下子整理清楚。也可以从今天最想被听见的那一句开始；如果和经前/经期状态有关，我们也只把它当作自我观察参考，不做诊断。"
        return "我在，你可以慢慢说，不用一下子整理清楚。先从今天最想被听见的那一句开始就好。"

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
