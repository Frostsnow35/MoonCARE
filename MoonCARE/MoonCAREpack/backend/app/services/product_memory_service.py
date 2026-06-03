import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.services.awareness_memory_provider import AwarenessLocalProvider
from app.services.chat_memory_service import ChatMemoryService
from app.services.health_context_service import HealthContextService
from app.utils.safety import contains_crisis_signal


logger = logging.getLogger(__name__)


class ProductMemoryService:
    """Compose local DB memory with Awareness Local product memory."""

    def __init__(
        self,
        db: Session,
        awareness_provider: Optional[Any] = None,
        enable_awareness: Optional[bool] = None,
    ):
        self.db = db
        self.local_memory = ChatMemoryService(db)
        enabled = settings.AWARENESS_MEMORY_ENABLED if enable_awareness is None else enable_awareness
        self.awareness_provider = awareness_provider
        if self.awareness_provider is None and enabled:
            self.awareness_provider = AwarenessLocalProvider()

    def build_prompt_context(
        self,
        user_id: int,
        session_id: str,
        query_message: str = "",
        recent_turn_limit: int = 8,
        memory_limit: int = 12,
        retrieval_limit: int = 4,
    ) -> Dict[str, Any]:
        """Build prompt context with local memory and optional Awareness recall."""
        context = self.local_memory.build_prompt_context(
            user_id=user_id,
            session_id=session_id,
            query_message=query_message,
            recent_turn_limit=recent_turn_limit,
            memory_limit=memory_limit,
            retrieval_limit=retrieval_limit,
        )
        memory_state = dict(context.get("memory_state") or {})
        memory_state.update(
            {
                "provider": "local_db",
                "awareness_available": False,
                "awareness_recalled": False,
                "awareness_items": 0,
                "fallback_reason": None,
                "health_context_available": False,
            }
        )
        health_context = self._build_health_context(user_id)
        context["health_context"] = health_context["health_context"]
        context["health_state"] = health_context["health_state"]
        memory_state["health_context_available"] = bool(
            health_context["health_state"].get("available")
        )
        memory_state["health_context_has_cycle"] = bool(
            health_context["health_state"].get("has_cycle")
        )
        memory_state["health_context_has_diary"] = bool(
            health_context["health_state"].get("has_diary")
        )

        if not self.awareness_provider:
            context["memory_state"] = memory_state
            return context

        recall = self.awareness_provider.recall_context(
            user_id=user_id,
            query_message=query_message,
            keyword_query=self._keyword_query(query_message),
        )
        memory_state["awareness_available"] = bool(recall.get("available"))
        memory_state["awareness_recalled"] = bool(recall.get("recalled"))
        memory_state["awareness_items"] = int(recall.get("items_count") or 0)
        memory_state["fallback_reason"] = recall.get("fallback_reason")
        if recall.get("recalled") and recall.get("context"):
            memory_state["provider"] = "awareness_local"
            context["memory_context"] = self._append_awareness_context(
                context.get("memory_context", ""),
                recall["context"],
            )

        context["memory_state"] = memory_state
        return context

    def _build_health_context(self, user_id: int) -> Dict[str, Any]:
        """Build cycle and diary context without blocking chat if it fails."""
        try:
            return HealthContextService(self.db).build_prompt_context(user_id=user_id)
        except Exception as exc:
            logger.warning("Failed to build health context: %s", exc)
            return {
                "health_context": "暂无可用的周期/日记上下文。",
                "health_state": {
                    "available": False,
                    "has_cycle": False,
                    "has_diary": False,
                    "cycle_phase": None,
                    "cycle_day": None,
                    "diary_count": 0,
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
        """Capture safe local memories, then record a sanitized summary to Awareness."""
        context = context or {}
        local_state = self.local_memory.capture_user_message(
            user_id=user_id,
            conversation_id=conversation_id,
            message=message,
            context=context,
            is_sensitive=is_sensitive,
        )
        result = dict(local_state)
        result.update(
            {
                "provider": "local_db",
                "awareness_available": False,
                "awareness_recorded": False,
                "fallback_reason": None,
            }
        )

        if (
            not self.awareness_provider
            or is_sensitive
            or contains_crisis_signal(message)
            or not local_state.get("updated")
        ):
            return result

        record_content = self._record_content(
            user_id=user_id,
            categories=local_state.get("categories") or [],
        )
        insights = self._record_insights(
            user_id=user_id,
            categories=local_state.get("categories") or [],
            content=record_content,
        )
        record_state = self.awareness_provider.record_summary(
            user_id=user_id,
            content=record_content,
            insights=insights,
        )

        result["awareness_available"] = bool(record_state.get("available"))
        result["awareness_recorded"] = bool(record_state.get("recorded"))
        result["fallback_reason"] = record_state.get("fallback_reason")
        if record_state.get("recorded"):
            result["provider"] = "awareness_local"
        return result

    def _append_awareness_context(self, local_context: str, awareness_context: str) -> str:
        """Append Awareness recall without hiding local fallback memory."""
        local_context = local_context or "暂无可用长期记忆。"
        if local_context == "暂无可用长期记忆。":
            return f"{local_context}\n\nAwareness 记忆参考：\n{awareness_context}"
        return f"{local_context}\n\nAwareness 记忆参考：\n{awareness_context}"

    def _keyword_query(self, message: str) -> str:
        """Build a lightweight keyword query for Awareness recall."""
        terms = [
            "经前",
            "月经",
            "姨妈",
            "PMS",
            "睡眠",
            "音乐",
            "偏好",
            "少量建议",
            "刚才",
            "这个",
            "那个",
        ]
        return " ".join(term for term in terms if term in (message or ""))

    def _record_content(self, user_id: int, categories: list[str]) -> str:
        """Create a sanitized Awareness record narrative from local summaries."""
        memory_context = self.local_memory.build_prompt_context(
            user_id=user_id,
            session_id="",
            memory_limit=8,
        )["memory_context"]
        category_text = "、".join(categories) if categories else "未分类"
        return (
            "MoonCARE 安全记忆摘要：本轮聊天产生了可用于后续陪伴的非危机记忆。"
            f"记忆分类：{category_text}。"
            f"当前安全摘要：{memory_context}。"
            "这些内容仅用于陪伴和自我观察参考，不构成医学或心理诊断。"
        )

    def _record_insights(
        self,
        user_id: int,
        categories: list[str],
        content: str,
    ) -> Dict[str, Any]:
        """Build Awareness insights from MoonCARE memory categories."""
        card_category = "health_info"
        if "preference" in categories:
            card_category = "personal_preference"
        elif "personal_fact" in categories:
            card_category = "important_detail"

        title = "MoonCARE 用户陪伴记忆摘要"
        summary = (
            "MoonCARE 在安全聊天中提取了最小必要记忆，用于后续更自然地延续陪伴。"
            f"分类包括：{('、'.join(categories) if categories else '未分类')}。"
            "该摘要不保存完整敏感原文，危机表达不会写入普通长期记忆。"
        )
        return {
            "knowledge_cards": [
                {
                    "category": card_category,
                    "title": title,
                    "summary": summary,
                }
            ],
            "entities": [
                {
                    "canonical_name": f"mooncare_user_{user_id}",
                    "kind": "person",
                    "aliases": [f"user_{user_id}"],
                }
            ],
            "facts": [
                {
                    "subject_id": f"mooncare_user_{user_id}",
                    "predicate": "has_mooncare_safe_memory_summary",
                    "statement": content,
                    "confidence": 0.7,
                }
            ],
        }
