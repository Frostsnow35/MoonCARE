from typing import Iterable


CRISIS_KEYWORDS = (
    "不想活",
    "想死",
    "自杀",
    "自残",
    "轻生",
    "结束生命",
    "结束自己",
    "活不下去",
    "伤害自己",
    "kill myself",
    "suicide",
    "self-harm",
    "end it all",
)


SAFE_INTERVENTION_FALLBACK = (
    "我很担心你现在的安全。请先尽量待在有人的地方，"
    "马上联系一个可信任的人陪你，或拨打当地紧急电话/心理危机热线。"
    "你不用一个人扛着。"
)


def contains_crisis_signal(text: str, keywords: Iterable[str] = CRISIS_KEYWORDS) -> bool:
    """Return True when text contains a crisis or self-harm signal."""
    normalized = (text or "").lower()
    return any(keyword in normalized for keyword in keywords)
