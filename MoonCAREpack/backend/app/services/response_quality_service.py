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
    technical_failure_terms = ("模型", "响应", "重试", "稍后再试", "状况", "连接")

    def repair_reply(self, user_message: str, reply: str, state: Dict) -> str:
        """Return a reply that follows the user's actual conversational cue."""
        message = (user_message or "").strip()
        original_reply = (reply or "").strip()
        state = state or {}

        if self._is_open_disclosure(message) and self._overreads_open_disclosure(original_reply):
            return self._open_disclosure_reply(state)

        if self._is_partner_invalidation(message) and not self._addresses_partner_invalidation(original_reply):
            return self._partner_invalidation_reply(state)

        if self._is_positive_shift(message) and (
            self._is_technical_or_thin_reply(original_reply)
            or self._overreads_positive_shift(message, original_reply)
        ):
            return self._positive_shift_reply(message, state)

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
        if self._is_positive_shift(message):
            return "我听见了，你感觉开心一点了。这个小小的变好也值得被认真接住。"
        if self._is_emotional_distress(message):
            emotion = self._named_emotion(message, state or {})
            return f"我听见了，你现在感到{emotion}。先不用急着把它压下去。"
        return ""

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

    def _cycle_note(self, state: Dict) -> str:
        """Return a non-diagnostic menstrual-context note when relevant."""
        state = state or {}
        support_context = state.get("support_context") or {}
        cycle_phase = state.get("cycle_phase", "")
        menstrual_related = support_context.get("menstrual_related")
        if menstrual_related or cycle_phase in {"经前期", "经期", "黄体期", "月经期"}:
            return "如果这几天接近经前/经期，情绪阈值变低是一些人会经历的状态；这里仅供参考，可作为自我观察，不代表诊断。"
        return "如果你之后发现它总和经前/经期重叠，我们也可以一起观察规律；这里仅供参考，不代表诊断。"

    def _positive_shift_reply(self, message: str, state: Dict) -> str:
        """Reinforce a small emotional improvement without over-directing the user."""
        return (
            "我听见了，你感觉开心一点了。这个小小的变好也值得被认真接住，不用急着把它放大成“必须一直开心”。"
            "我们可以轻轻看一眼：刚才是什么让它出现了一点点？"
            f"{self._cycle_note(state)}"
        )

    def _body_discomfort_reply(self, message: str, state: Dict) -> str:
        """Offer concrete, low-pressure care for menstrual/body discomfort."""
        compact = "".join((message or "").split())
        symptom = "肚子疼" if ("肚子疼" in compact or "肚子痛" in compact or "腹痛" in compact or "痛经" in compact or "绞痛" in compact) else "身体不舒服"
        return (
            f"我听见了，{symptom}会很消耗人，尤其是来月经或经期前后。"
            "你可以先试试热敷小腹、喝点温水、把身体蜷起来休息一会儿，先别逼自己立刻恢复。"
            "如果疼痛很剧烈、出血异常，或和平时明显不同，建议联系专业医生；这里仅供参考，不代表诊断。"
            "现在更像一阵一阵的绞痛，还是持续的坠胀？"
        )

    def _emotional_distress_reply(self, message: str, state: Dict) -> str:
        """Immediate support for short emotional disclosures without waiting for the model."""
        emotion = self._named_emotion(message, state)
        return (
            f"我听见了，你现在感到{emotion}。先不用急着把它压下去，也不用马上解释清楚为什么会这样。"
            f"{self._cycle_note(state)}"
            "我们先把这一刻放慢一点：把肩膀松下来，呼气稍微拉长一点。"
            "然后你可以告诉我，这股感觉更像是被人惹到了、身体不舒服，还是事情太多挤在一起？"
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
