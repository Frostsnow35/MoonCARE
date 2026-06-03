import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.services.chat_memory_service import ChatMemoryService
from app.services.health_context_service import HealthContextService


logger = logging.getLogger(__name__)


class ProductMemoryService:
    """Compose MoonCARE-owned local DB memory with health context."""

    def __init__(
        self,
        db: Session,
    ):
        self.db = db
        self.local_memory = ChatMemoryService(db)

    def build_prompt_context(
        self,
        user_id: int,
        session_id: str,
        query_message: str = "",
        recent_turn_limit: int = 8,
        memory_limit: int = 12,
        retrieval_limit: int = 4,
    ) -> Dict[str, Any]:
        """Build prompt context with local memory and health context."""
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
        """Capture safe local memories in the MoonCARE database."""
        context = context or {}
        local_state = self.local_memory.capture_user_message(
            user_id=user_id,
            conversation_id=conversation_id,
            message=message,
            context=context,
            is_sensitive=is_sensitive,
        )
        result = dict(local_state)
        result["provider"] = "local_db"
        return result
