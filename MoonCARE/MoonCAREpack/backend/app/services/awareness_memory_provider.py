import json
import logging
import uuid
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


class AwarenessLocalProvider:
    """Local Awareness MCP provider for product runtime memory."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        mcp_path: Optional[str] = None,
        http_client: Optional[Any] = None,
        timeout_seconds: Optional[float] = None,
        recall_limit: Optional[int] = None,
        source: Optional[str] = None,
    ):
        self.base_url = (base_url or settings.AWARENESS_BASE_URL).rstrip("/")
        self.mcp_path = mcp_path or settings.AWARENESS_MCP_PATH
        if not self.mcp_path.startswith("/"):
            self.mcp_path = f"/{self.mcp_path}"
        self.mcp_url = f"{self.base_url}{self.mcp_path}"
        self.timeout_seconds = float(timeout_seconds or settings.AWARENESS_TIMEOUT_SECONDS)
        self.recall_limit = int(recall_limit or settings.AWARENESS_RECALL_LIMIT)
        self.source = source or settings.AWARENESS_SOURCE
        self.http_client = http_client or httpx.Client(timeout=self.timeout_seconds)
        self._session_by_user: Dict[str, str] = {}

    def recall_context(
        self,
        user_id: int,
        query_message: str,
        keyword_query: str = "",
    ) -> Dict[str, Any]:
        """Recall Awareness memory and format it for prompt context."""
        try:
            session_id = self._ensure_session(user_id)
            arguments = {
                "semantic_query": query_message or "MoonCARE user memory",
                "keyword_query": keyword_query or query_message or "",
                "detail": "summary",
                "limit": self.recall_limit,
                "user_id": str(user_id),
                "source": self.source,
            }
            if session_id:
                arguments["session_id"] = session_id

            payload = self._call_tool("awareness_recall", arguments)
            context, count = self._format_recall_payload(payload)
            return {
                "available": True,
                "recalled": bool(context),
                "context": context,
                "items_count": count,
                "fallback_reason": None,
            }
        except Exception as exc:
            logger.info("Awareness recall unavailable: %s", exc)
            return {
                "available": False,
                "recalled": False,
                "context": "",
                "items_count": 0,
                "fallback_reason": str(exc),
            }

    def record_summary(
        self,
        user_id: int,
        content: str,
        insights: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Record a safe summarized memory narrative to Awareness."""
        try:
            session_id = self._ensure_session(user_id)
            arguments = {
                "content": content,
                "insights": insights,
                "user_id": str(user_id),
                "source": self.source,
            }
            if session_id:
                arguments["session_id"] = session_id

            self._call_tool("awareness_record", arguments)
            return {
                "available": True,
                "recorded": True,
                "fallback_reason": None,
            }
        except Exception as exc:
            logger.info("Awareness record unavailable: %s", exc)
            return {
                "available": False,
                "recorded": False,
                "fallback_reason": str(exc),
            }

    def _ensure_session(self, user_id: int) -> Optional[str]:
        """Initialize an Awareness session for one MoonCARE user scope."""
        user_key = str(user_id)
        if user_key in self._session_by_user:
            return self._session_by_user[user_key]

        payload = self._call_tool(
            "awareness_init",
            {
                "source": self.source,
                "rules_version": "2",
                "user_id": user_key,
            },
        )
        session_id = self._find_session_id(payload)
        if session_id:
            self._session_by_user[user_key] = session_id
        return session_id

    def _call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call one Awareness MCP tool using JSON-RPC tools/call."""
        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments,
            },
        }
        response = self.http_client.post(self.mcp_url, json=request)
        response.raise_for_status()
        payload = response.json()
        if "error" in payload:
            raise RuntimeError(payload["error"])
        return self._extract_tool_payload(payload)

    def _extract_tool_payload(self, payload: Dict[str, Any]) -> Any:
        """Extract structured or text content from a MCP JSON-RPC response."""
        result = payload.get("result", payload)
        if isinstance(result, dict):
            if result.get("structuredContent") is not None:
                return result["structuredContent"]
            if result.get("structured_content") is not None:
                return result["structured_content"]
            if result.get("content") is not None:
                return self._parse_content_items(result["content"])
        return result

    def _parse_content_items(self, content: Any) -> Any:
        """Parse MCP content blocks into JSON when possible."""
        if not isinstance(content, list):
            return content

        parsed: List[Any] = []
        texts: List[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if not text:
                continue
            texts.append(text)
            try:
                parsed.append(json.loads(text))
            except json.JSONDecodeError:
                parsed.append(text)

        if len(parsed) == 1:
            return parsed[0]
        if parsed:
            return parsed
        return "\n".join(texts)

    def _find_session_id(self, payload: Any) -> Optional[str]:
        """Return a session id from flexible Awareness init responses."""
        if isinstance(payload, dict):
            session_id = payload.get("session_id") or payload.get("sessionId")
            return str(session_id) if session_id else None
        return None

    def _format_recall_payload(self, payload: Any) -> tuple[str, int]:
        """Format Awareness recall payload into bounded prompt text."""
        items = self._extract_recall_items(payload)
        if items:
            lines = []
            for item in items[: self.recall_limit]:
                title = self._item_title(item)
                summary = self._item_summary(item)
                if summary:
                    lines.append(f"- {title}：{self._truncate(summary, 240)}")
            return "\n".join(lines), len(lines)

        if isinstance(payload, str):
            text = self._truncate(payload.strip(), 800)
            return (text, 1) if text else ("", 0)

        if isinstance(payload, dict):
            text = payload.get("summary") or payload.get("content") or payload.get("text")
            if text:
                return self._truncate(str(text), 800), 1

        return "", 0

    def _extract_recall_items(self, payload: Any) -> List[Dict[str, Any]]:
        """Extract item-like dictionaries from common Awareness response shapes."""
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []
        for key in ("items", "cards", "memories", "results", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return []

    def _item_title(self, item: Dict[str, Any]) -> str:
        """Return a safe display title for one recall item."""
        return str(
            item.get("title")
            or item.get("category")
            or item.get("kind")
            or item.get("id")
            or "记忆"
        )

    def _item_summary(self, item: Dict[str, Any]) -> str:
        """Return a safe summary for one recall item."""
        value = (
            item.get("summary")
            or item.get("content")
            or item.get("text")
            or item.get("statement")
            or ""
        )
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    def _truncate(self, text: str, limit: int) -> str:
        """Trim prompt text to a bounded length."""
        normalized = " ".join((text or "").split())
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[: limit - 1]}…"
