from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List
import json
import logging
import uuid
from datetime import datetime

from app.database import get_db, SessionLocal
from app.models.conversation import Conversation
from app.schemas.chat import ChatMessage, ChatResponse, ChatHistoryResponse
from app.services.agent_service import get_agent_service
from app.services.assessment_service import AssessmentOrchestrator
from app.services.chat_memory_service import ChatMemoryService
from app.services.nlp_service import NLPService

router = APIRouter(prefix="/chat", tags=["AI对话"])
logger = logging.getLogger(__name__)


# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict] = {}

    async def connect(self, websocket: WebSocket, session_id: str, user_id: int):
        await websocket.accept()
        self.active_connections[session_id] = {
            "websocket": websocket,
            "user_id": user_id,
            "created_at": datetime.now()
        }

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    def get_connection(self, session_id: str):
        return self.active_connections.get(session_id)


manager = ConnectionManager()


def _safe_capture_memory(
    db: Session,
    user_id: int,
    conversation_id: int,
    message: str,
    context: Dict,
    is_sensitive: bool,
) -> Dict:
    """Persist safe chat memories without blocking the main assistant reply."""
    try:
        return ChatMemoryService(db).capture_user_message(
            user_id=user_id,
            conversation_id=conversation_id,
            message=message,
            context=context,
            is_sensitive=is_sensitive,
        )
    except Exception as exc:
        logger.warning("Failed to update chat memory state: %s", exc)
        return {"updated": False, "count": 0, "categories": [], "reason": "error"}


@router.websocket("/ws/{user_id}")
async def websocket_chat(websocket: WebSocket, user_id: int):
    """
    WebSocket AI对话
    触发条件：用户点击聊聊按钮或系统检测到情绪波动升高
    支持多轮上下文记忆
    """
    session_id = str(uuid.uuid4())
    await manager.connect(websocket, session_id, user_id)

    agent_service = get_agent_service()
    nlp_service = NLPService()
    db = SessionLocal()

    try:
        # Send session info
        await websocket.send_json({
            "type": "session",
            "session_id": session_id,
            "message": "连接成功，开始聊天吧~"
        })

        while True:
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            agent_mode = data.get("agent_mode", "auto")

            if not user_message:
                continue

            # Analyze user message
            nlp_result = await nlp_service.analyze_text(user_message)
            intent = nlp_service.get_intent(user_message)
            is_sensitive = nlp_service.check_sensitive(user_message)
            nlp_result["intent"] = intent
            memory_service = ChatMemoryService(db)
            nlp_result["conversation_memory"] = memory_service.build_prompt_context(
                user_id=user_id,
                session_id=session_id,
                query_message=user_message,
            )

            assessment = AssessmentOrchestrator(db)
            should_record_assessment_answer = assessment.is_awaiting_answer(user_id, session_id)
            assessment_result = assessment.prepare_turn(
                user_id=user_id,
                chat_session_id=session_id,
                user_message=user_message,
                context=nlp_result,
            )

            # Get AI response
            response = await agent_service.get_response(
                user_id=user_id,
                session_id=session_id,
                user_message=user_message,
                context=nlp_result,
                agent_mode=agent_mode,
            )
            if assessment_result.assessment_prompt_hint:
                response["message"] = f"{response['message']}\n\n{assessment_result.assessment_prompt_hint}"

            last_turn = db.query(func.max(Conversation.turn_number)).filter(
                Conversation.user_id == user_id,
                Conversation.session_id == session_id,
            ).scalar() or 0
            user_turn = last_turn + 1
            assistant_turn = last_turn + 2

            # Save conversation turn
            conversation = Conversation(
                user_id=user_id,
                session_id=session_id,
                turn_number=user_turn,
                role="user",
                content=user_message,
                intent=intent,
                sentiment_score=nlp_result.get("sentiment_score"),
                is_sensitive=1 if is_sensitive else 0
            )
            db.add(conversation)

            assistant_conv = Conversation(
                user_id=user_id,
                session_id=session_id,
                turn_number=assistant_turn,
                role="assistant",
                content=response["message"]
            )
            db.add(assistant_conv)
            db.commit()
            db.refresh(conversation)
            if should_record_assessment_answer:
                assessment.record_user_answer(
                    user_id=user_id,
                    chat_session_id=session_id,
                    user_message=user_message,
                    conversation_id=conversation.id,
                )
            memory_state = _safe_capture_memory(
                db=db,
                user_id=user_id,
                conversation_id=conversation.id,
                message=user_message,
                context=nlp_result,
                is_sensitive=is_sensitive,
            )

            # Send response
            await websocket.send_json({
                "type": "assistant",
                "message": response["message"],
                "sentiment_score": nlp_result["sentiment_score"],
                "intent": response.get("intent", "general"),
                "is_sensitive": is_sensitive,
                "suggestions": response.get("suggestions", []),
                "actions": response.get("actions", []),
                "risk_level": response.get("state", {}).get("risk_level", "low"),
                "reply_status": response.get("reply_status", "ok"),
                "elapsed_ms": response.get("elapsed_ms", 0),
                "assessment_state": assessment_result.assessment_state,
                "memory_state": memory_state,
            })

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        db.close()
    except Exception as e:
        manager.disconnect(session_id)
        db.rollback()
        db.close()
        try:
            await websocket.send_json({
                "type": "error",
                "message": "发生错误，请重新连接"
            })
        except:
            pass


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    user_id: int = 1,  # TODO: from auth
    db: Session = Depends(get_db)
):
    """获取对话历史"""
    conversations = db.query(Conversation).filter(
        Conversation.session_id == session_id,
        Conversation.user_id == user_id
    ).order_by(Conversation.turn_number).all()

    turns = [
        {
            "role": conv.role,
            "content": conv.content,
            "sentiment_score": conv.sentiment_score,
            "intent": conv.intent,
            "created_at": conv.created_at.isoformat() if conv.created_at else None
        }
        for conv in conversations
    ]

    return ChatHistoryResponse(
        session_id=session_id,
        turns=turns,
        total_turns=len(turns)
    )


@router.post("/session", response_model=dict)
async def create_chat_session(user_id: int = 1):
    """创建新的对话会话"""
    session_id = str(uuid.uuid4())
    return {
        "session_id": session_id,
        "created_at": datetime.now().isoformat()
    }


@router.post("/message")
async def send_chat_message(
    message: str,
    user_id: int = 1,
    session_id: str = None,
    cycle_phase: str = None,
    agent_mode: str = "auto",
    db: Session = Depends(get_db)
):
    """直接发送消息获取AI回复（REST API，非WebSocket）"""
    if not session_id:
        session_id = str(uuid.uuid4())

    agent_service = get_agent_service()
    nlp_service = NLPService()

    # 分析消息
    nlp_result = await nlp_service.analyze_text(message)
    intent = nlp_service.get_intent(message)
    is_sensitive = nlp_service.check_sensitive(message)

    # 构建上下文
    context = {
        **nlp_result,
        "intent": intent,
        "cycle_phase": cycle_phase,
        "sensor_data": {}
    }
    memory_service = ChatMemoryService(db)
    context["conversation_memory"] = memory_service.build_prompt_context(
        user_id=user_id,
        session_id=session_id,
        query_message=message,
    )

    assessment = AssessmentOrchestrator(db)
    should_record_assessment_answer = assessment.is_awaiting_answer(user_id, session_id)
    assessment_result = assessment.prepare_turn(
        user_id=user_id,
        chat_session_id=session_id,
        user_message=message,
        context=context,
    )

    # 获取AI响应（使用新的Agent系统）
    response = await agent_service.get_response(
        user_id=user_id,
        session_id=session_id,
        user_message=message,
        context=context,
        agent_mode=agent_mode,
    )
    if assessment_result.assessment_prompt_hint:
        response["message"] = f"{response['message']}\n\n{assessment_result.assessment_prompt_hint}"

    last_turn = db.query(func.max(Conversation.turn_number)).filter(
        Conversation.user_id == user_id,
        Conversation.session_id == session_id,
    ).scalar() or 0
    user_turn = last_turn + 1
    assistant_turn = last_turn + 2

    user_conv = Conversation(
        user_id=user_id,
        session_id=session_id,
        turn_number=user_turn,
        role="user",
        content=message,
        intent=intent,
        sentiment_score=nlp_result.get("sentiment_score"),
        is_sensitive=1 if is_sensitive else 0,
    )
    assistant_conv = Conversation(
        user_id=user_id,
        session_id=session_id,
        turn_number=assistant_turn,
        role="assistant",
        content=response["message"],
    )
    db.add(user_conv)
    db.add(assistant_conv)
    db.commit()
    db.refresh(user_conv)
    if should_record_assessment_answer:
        assessment.record_user_answer(
            user_id=user_id,
            chat_session_id=session_id,
            user_message=message,
            conversation_id=user_conv.id,
        )
    memory_state = _safe_capture_memory(
        db=db,
        user_id=user_id,
        conversation_id=user_conv.id,
        message=message,
        context=context,
        is_sensitive=is_sensitive,
    )

    return {
        "session_id": session_id,
        "reply": response["message"],
        "intent": response.get("intent", "general"),
        "risk_level": response.get("state", {}).get("risk_level", "low"),
        "suggestions": response.get("suggestions", []),
        "actions": response.get("actions", []),
        "is_sensitive": is_sensitive,
        "reply_status": response.get("reply_status", "ok"),
        "elapsed_ms": response.get("elapsed_ms", 0),
        "assessment_state": assessment_result.assessment_state,
        "memory_state": memory_state,
    }


@router.get("/sessions")
async def get_chat_sessions(
    user_id: int = 1,  # TODO: from auth
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取用户的对话会话列表"""
    from sqlalchemy import func

    # Get distinct sessions
    sessions = db.query(
        Conversation.session_id,
        func.max(Conversation.created_at).label("last_message_at"),
        func.count(Conversation.id).label("message_count")
    ).filter(
        Conversation.user_id == user_id
    ).group_by(
        Conversation.session_id
    ).order_by(
        func.max(Conversation.created_at).desc()
    ).limit(limit).all()

    return [
        {
            "session_id": s.session_id,
            "last_message_at": s.last_message_at.isoformat() if s.last_message_at else None,
            "message_count": s.message_count
        }
        for s in sessions
    ]
