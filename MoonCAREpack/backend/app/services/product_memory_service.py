from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.services.chat_memory_service import ChatMemoryService


class ProductMemoryService:
    """MoonCARE-owned memory core and prompt context manager."""

    def __init__(
        self,
        db: Session,
        memory_provider: Optional[Any] = None,
    ):
        self.db = db
        self.memory_provider = memory_provider or ChatMemoryService(db)

    def build_prompt_context(
        self,
        user_id: int,
        session_id: str,
        query_message: str = "",
        recent_turn_limit: int = 8,
        memory_limit: int = 12,
        retrieval_limit: int = 4,
    ) -> Dict[str, Any]:
        """Build prompt context from MoonCARE-owned memory and conversation history."""
        return self.memory_provider.build_prompt_context(
            user_id=user_id,
            session_id=session_id,
            query_message=query_message,
            recent_turn_limit=recent_turn_limit,
            memory_limit=memory_limit,
            retrieval_limit=retrieval_limit,
        )

    def capture_user_message(
        self,
        user_id: int,
        conversation_id: Optional[int],
        message: str,
        context: Optional[Dict[str, Any]] = None,
        is_sensitive: bool = False,
    ) -> Dict[str, Any]:
        """Capture safe memories in MoonCARE's own database."""
        state = self.memory_provider.capture_user_message(
            user_id=user_id,
            conversation_id=conversation_id,
            message=message,
            context=context or {},
            is_sensitive=is_sensitive,
        )
        result = dict(state)
        result["provider"] = "mooncare_memory_core"
        return result
