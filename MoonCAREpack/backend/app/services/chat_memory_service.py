import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from app.models.chat_memory import ChatMemory
from app.models.conversation import Conversation
from app.utils.safety import contains_crisis_signal


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MemoryCandidate:
    """A safe, minimal memory candidate extracted from one user turn."""

    category: str
    key: str
    value: str
    confidence: float = 0.65


class ChatMemoryService:
    """Create and retrieve bounded chat memories for prompt context."""

    max_value_length = 120
    max_recent_turn_length = 300

    def __init__(self, db: Session):
        self.db = db

    def build_prompt_context(
        self,
        user_id: int,
        session_id: str,
        query_message: str = "",
        recent_turn_limit: int = 24,
        memory_limit: int = 12,
        retrieval_limit: int = 4,
    ) -> Dict[str, Any]:
        """Return prompt-ready recent context, long-term memories, and metadata."""
        memories = (
            self.db.query(ChatMemory)
            .filter(ChatMemory.user_id == user_id)
            .order_by(ChatMemory.last_seen_at.desc(), ChatMemory.id.desc())
            .limit(memory_limit)
            .all()
        )
        recent_turns = self._recent_turns(user_id, session_id, recent_turn_limit)
        retrieved_turns = self._retrieve_relevant_turns(
            user_id=user_id,
            session_id=session_id,
            query_message=query_message,
            recent_turns=recent_turns,
            limit=retrieval_limit,
        )
        conversation_messages = self._conversation_messages(recent_turns, retrieved_turns)
        needs_context_resolution = self._needs_context_resolution(query_message)

        return {
            "memory_context": self._format_memories(memories),
            "recent_context": self._format_recent_turns(recent_turns),
            "retrieved_context": self._format_recent_turns(retrieved_turns),
            "conversation_messages": conversation_messages,
            "memory_state": {
                "has_memory": bool(memories),
                "count": len(memories),
                "updated": False,
                "categories": sorted({memory.category for memory in memories}),
                "retrieved_turns": len(retrieved_turns),
                "needs_context_resolution": needs_context_resolution,
            },
        }

    def capture_user_message(
        self,
        user_id: int,
        conversation_id: Optional[int],
        message: str,
        context: Optional[Dict[str, Any]] = None,
        is_sensitive: bool = False,
    ) -> Dict[str, Any]:
        """Extract safe memory candidates from a user message and persist them."""
        context = context or {}
        if is_sensitive or contains_crisis_signal(message):
            logger.info("Skipped chat memory capture for sensitive user turn.")
            return {"updated": False, "count": self._memory_count(user_id), "categories": [], "reason": "sensitive"}

        candidates = self._extract_candidates(message, context)
        if not candidates:
            return {"updated": False, "count": self._memory_count(user_id), "categories": [], "reason": "no_candidate"}

        updated_categories: List[str] = []
        for candidate in candidates:
            self._upsert_memory(user_id, conversation_id, candidate)
            updated_categories.append(candidate.category)

        self.db.commit()
        return {
            "updated": True,
            "count": self._memory_count(user_id),
            "categories": sorted(set(updated_categories)),
        }

    def _recent_turns(self, user_id: int, session_id: str, limit: int) -> List[Conversation]:
        """Load the most recent conversation turns for this chat session."""
        if not session_id:
            return []

        rows = (
            self.db.query(Conversation)
            .filter(
                Conversation.user_id == user_id,
                Conversation.session_id == session_id,
            )
            .order_by(Conversation.turn_number.desc(), Conversation.id.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(rows))

    def _retrieve_relevant_turns(
        self,
        user_id: int,
        session_id: str,
        query_message: str,
        recent_turns: List[Conversation],
        limit: int,
    ) -> List[Conversation]:
        """Retrieve older turns that are relevant to the current user query."""
        if not session_id or not query_message or limit <= 0:
            return []

        recent_ids = {turn.id for turn in recent_turns if turn.id is not None}
        candidates = (
            self.db.query(Conversation)
            .filter(
                Conversation.user_id == user_id,
                Conversation.session_id == session_id,
            )
            .order_by(Conversation.turn_number.desc(), Conversation.id.desc())
            .limit(80)
            .all()
        )

        scored = []
        for turn in candidates:
            if turn.id in recent_ids:
                continue
            if turn.role == "user" and int(turn.is_sensitive or 0) == 1:
                continue
            if contains_crisis_signal(turn.content):
                continue
            score = self._relevance_score(query_message, turn)
            if score > 0:
                scored.append((score, turn.turn_number or 0, turn))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        selected = [turn for _, _, turn in scored[:limit]]
        return sorted(selected, key=lambda turn: (turn.turn_number or 0, turn.id or 0))

    def _relevance_score(self, query_message: str, turn: Conversation) -> float:
        """Score a conversation turn for lightweight hybrid retrieval."""
        query = (query_message or "").lower()
        content = (turn.content or "").lower()
        score = 0.0

        for token in self._query_tokens(query):
            if token and token in content:
                score += 2.0 if len(token) >= 3 else 1.0

        if self._needs_context_resolution(query):
            if turn.role == "assistant":
                score += 0.8
            if any(term in content for term in ["游戏", "玩", "电影", "票", "音乐", "刚才", "这个", "那个"]):
                score += 1.2
            if any(char.isdigit() for char in content) or any("a" <= char <= "z" for char in content):
                score += 0.6

        return score

    def _query_tokens(self, text: str) -> List[str]:
        """Extract stable query tokens without adding external dependencies."""
        import re

        tokens = re.findall(r"[a-zA-Z0-9_]{2,}", text)
        domain_terms = [
            "游戏", "电影", "票", "音乐", "经前", "月经", "烦躁", "睡眠", "学习",
            "工作", "喜欢", "偏好", "这个", "那个", "刚才", "是什么",
        ]
        tokens.extend(term for term in domain_terms if term in text)
        return list(dict.fromkeys(tokens))

    def _needs_context_resolution(self, text: str) -> bool:
        """Return whether a query likely depends on prior turns."""
        normalized = text or ""
        markers = ["这", "这个", "那个", "刚才", "上面", "前面", "它", "他说", "你刚", "是什么", "哪一个"]
        return any(marker in normalized for marker in markers)

    def _extract_candidates(self, message: str, context: Dict[str, Any]) -> List[MemoryCandidate]:
        """Use conservative rules to extract user-confirmed facts and preferences."""
        text = (message or "").strip()
        if not text:
            return []

        candidates: List[MemoryCandidate] = []
        lower_text = text.lower()

        if "喜欢" in text or "爱听" in text:
            music_value = self._music_preference_value(text)
            if music_value:
                candidates.append(MemoryCandidate("preference", "music_preference", music_value, 0.75))

        if any(term in text for term in ["别一下子给我很多建议", "不要一下子给我很多建议", "少给建议", "一步一步"]):
            candidates.append(MemoryCandidate("preference", "guidance_style", "少量建议、一步一步来", 0.8))

        if any(term in text for term in ["经前", "月经前", "姨妈前", "黄体期"]):
            pattern = self._premenstrual_pattern_value(text)
            if pattern:
                candidates.append(MemoryCandidate("premenstrual_trait", "premenstrual_pattern", pattern, 0.7))

        emotional_trait = self._emotional_trait_value(text, context)
        if emotional_trait:
            candidates.append(MemoryCandidate("emotional_trait", "recent_emotional_pattern", emotional_trait, 0.6))

        personal_fact = self._personal_fact_value(text)
        if personal_fact:
            candidates.append(MemoryCandidate("personal_fact", personal_fact["key"], personal_fact["value"], 0.7))

        return candidates

    def _music_preference_value(self, text: str) -> Optional[str]:
        """Extract a compact music preference summary."""
        if "音乐" not in text and "歌" not in text:
            return None
        parts: List[str] = []
        if "晚上" in text or "睡前" in text:
            parts.append("晚上")
        if "轻音乐" in text:
            parts.append("听轻音乐")
        elif "舒缓" in text:
            parts.append("听舒缓音乐")
        else:
            parts.append("听音乐")
        return "".join(parts)

    def _premenstrual_pattern_value(self, text: str) -> Optional[str]:
        """Summarize PMS-adjacent self-observation without diagnostic wording."""
        signals = self._matched_terms(
            text,
            {
                "睡不好": ["睡不好", "失眠", "睡不着"],
                "学习效率下降": ["学习效率", "学习", "效率下降"],
                "工作效率下降": ["工作效率", "上班", "工作"],
                "烦躁": ["烦躁", "易怒", "脾气"],
                "低落": ["低落", "难过", "想哭"],
                "胀痛": ["胀痛", "腹痛", "头痛", "腰酸"],
            },
        )
        if not signals:
            return None
        return f"经前常出现：{'、'.join(signals[:4])}"

    def _emotional_trait_value(self, text: str, context: Dict[str, Any]) -> Optional[str]:
        """Summarize recurring emotional self-description from safe turns."""
        signals = self._matched_terms(
            text,
            {
                "焦虑": ["焦虑", "紧张", "不安", "慌"],
                "烦躁": ["烦躁", "易怒", "生气"],
                "低落": ["低落", "难过", "沮丧", "想哭"],
                "疲惫": ["疲惫", "累", "没精神"],
            },
        )
        if not signals and context.get("sentiment_score", 0.0) >= -0.35:
            return None
        if not signals:
            return "近期容易出现低落或压力感"
        return f"近期常提到：{'、'.join(signals[:3])}"

    def _personal_fact_value(self, text: str) -> Optional[Dict[str, str]]:
        """Extract stable personal facts only when the user states them explicitly."""
        if text.startswith("我叫") and len(text) <= 20:
            name = text.replace("我叫", "", 1).strip(" ，。,.")
            if 1 <= len(name) <= 12:
                return {"key": "preferred_name", "value": f"用户称呼：{name}"}
        return None

    def _matched_terms(self, text: str, mapping: Dict[str, Iterable[str]]) -> List[str]:
        """Return normalized labels whose keywords occur in text."""
        labels: List[str] = []
        for label, keywords in mapping.items():
            if any(keyword in text for keyword in keywords):
                labels.append(label)
        return labels

    def _upsert_memory(
        self,
        user_id: int,
        conversation_id: Optional[int],
        candidate: MemoryCandidate,
    ) -> ChatMemory:
        """Create or update one user memory by stable category/key."""
        now = datetime.now()
        value = self._truncate(candidate.value, self.max_value_length)
        memory = (
            self.db.query(ChatMemory)
            .filter(
                ChatMemory.user_id == user_id,
                ChatMemory.category == candidate.category,
                ChatMemory.key == candidate.key,
            )
            .first()
        )

        if memory is None:
            memory = ChatMemory(
                user_id=user_id,
                source_conversation_id=conversation_id,
                category=candidate.category,
                key=candidate.key,
                value=value,
                confidence=candidate.confidence,
                source="chat",
                last_seen_at=now,
            )
            self.db.add(memory)
            return memory

        memory.value = self._merge_values(memory.value, value)
        memory.confidence = max(float(memory.confidence or 0.0), candidate.confidence)
        memory.source_conversation_id = conversation_id or memory.source_conversation_id
        memory.last_seen_at = now
        return memory

    def _merge_values(self, old_value: str, new_value: str) -> str:
        """Merge short memory values without producing a long transcript."""
        if not old_value:
            return self._truncate(new_value, self.max_value_length)
        if new_value in old_value:
            return self._truncate(old_value, self.max_value_length)
        if old_value in new_value:
            return self._truncate(new_value, self.max_value_length)
        return self._truncate(f"{old_value}；{new_value}", self.max_value_length)

    def _format_memories(self, memories: List[ChatMemory]) -> str:
        """Format long-term memories for a system prompt."""
        if not memories:
            return "暂无可用长期记忆。"
        labels = {
            "preference": "用户偏好",
            "premenstrual_trait": "经前体验",
            "emotional_trait": "情绪特点",
            "personal_fact": "个人信息",
        }
        return "\n".join(
            f"- {labels.get(memory.category, memory.category)}：{memory.value}"
            for memory in memories
        )

    def _format_recent_turns(self, turns: List[Conversation]) -> str:
        """Format recent turns with bounded length for prompt context."""
        if not turns:
            return "暂无最近对话。"
        return "\n".join(
            f"{turn.role}: {self._truncate(turn.content, self.max_recent_turn_length)}"
            for turn in turns
        )

    def _conversation_messages(
        self,
        recent_turns: List[Conversation],
        retrieved_turns: List[Conversation],
    ) -> List[Dict[str, str]]:
        """Build OpenAI-compatible conversation messages with no duplicates."""
        merged: Dict[int, Conversation] = {}
        for turn in retrieved_turns + recent_turns:
            if turn.id is not None:
                merged[turn.id] = turn

        turns = sorted(merged.values(), key=lambda turn: (turn.turn_number or 0, turn.id or 0))
        messages: List[Dict[str, str]] = []
        for turn in turns:
            if turn.role not in {"user", "assistant"}:
                continue
            content = self._truncate(turn.content, self.max_recent_turn_length)
            if content:
                messages.append({"role": turn.role, "content": content})
        return messages

    def _memory_count(self, user_id: int) -> int:
        """Return total memory count for one user."""
        return self.db.query(ChatMemory).filter(ChatMemory.user_id == user_id).count()

    def _truncate(self, text: str, limit: int) -> str:
        """Trim text for prompt and storage boundaries."""
        normalized = " ".join((text or "").split())
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[: limit - 1]}…"

    EMOTION_DICT = {
        "积极": ["开心", "高兴", "快乐", "愉快", "幸福", "喜悦", "兴奋", "满足", "舒服", "轻松"],
        "焦虑": ["烦躁", "焦虑", "不安", "紧张", "担心", "害怕", "恐慌", "压力", "忐忑"],
        "难过": ["难过", "伤心", "失落", "沮丧", "绝望", "痛苦", "哭泣", "沮丧", "郁闷"],
        "疲惫": ["累", "疲惫", "困", "无力", "疲倦", "困倦", "疲劳", "没劲"],
        "中性": ["平静", "正常", "一般", "还好", "还行"]
    }

    def extract_emotion_keywords(self, text: str) -> List[str]:
        """从文本中提取情绪关键词"""
        if not text:
            return []

        found_emotions = []
        text_lower = text.lower()

        for emotion_type, keywords in self.EMOTION_DICT.items():
            for keyword in keywords:
                if keyword in text:
                    found_emotions.append(emotion_type)
                    break

        return found_emotions

    def get_dominant_emotion(self, text: str) -> str:
        """获取文本中的主导情绪"""
        if not text:
            return "中性"

        found_emotions = self.extract_emotion_keywords(text)

        if not found_emotions:
            return "中性"

        emotion_counts = {}
        for emotion in found_emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

        return max(emotion_counts, key=emotion_counts.get)
