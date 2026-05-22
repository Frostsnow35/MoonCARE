from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class ChatMessage(BaseModel):
    content: str
    role: str  # "user" or "assistant"


class ChatSessionCreate(BaseModel):
    user_id: int


class ChatSessionResponse(BaseModel):
    session_id: str
    created_at: datetime


class ChatTurn(BaseModel):
    session_id: str
    message: str
    sentiment_score: Optional[float] = None
    intent: Optional[str] = None
    is_sensitive: bool = False


class ChatResponse(BaseModel):
    message: str
    sentiment_score: float
    intent: str
    is_sensitive: bool
    suggestions: Optional[List[str]] = None


class ChatHistoryResponse(BaseModel):
    session_id: str
    turns: List[Dict]
    total_turns: int
