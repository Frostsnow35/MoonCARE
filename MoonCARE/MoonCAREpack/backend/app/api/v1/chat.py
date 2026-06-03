from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Form, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List, AsyncGenerator, Optional
import asyncio
import json
import logging
import uuid
from jose import ExpiredSignatureError, JWTError, jwt
from datetime import datetime

from app.database import get_db, SessionLocal
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.chat import ChatMessage, ChatResponse, ChatHistoryResponse
from app.services.agent_service import get_agent_service
from app.services.assessment_service import AssessmentOrchestrator
from app.services.product_memory_service import ProductMemoryService
from app.services.nlp_service import NLPService
from app.api.v1.deps import get_current_user_id
from app.config import settings

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


def _decode_websocket_token(token: str) -> Optional[int]:
    """Return the authenticated user id from a WebSocket token, or None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        return int(user_id) if user_id is not None else None
    except (ExpiredSignatureError, JWTError, TypeError, ValueError):
        return None


async def _authenticate_websocket(websocket: WebSocket, db: Session) -> Optional[int]:
    """Authenticate a browser WebSocket using a query token."""
    token = websocket.query_params.get("token") or websocket.query_params.get("access_token")
    user_id = _decode_websocket_token(token) if token else None
    if user_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    user_exists = db.query(User.id).filter(User.id == user_id).first()
    if not user_exists:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

    return user_id


def _ensure_chat_session_access(db: Session, user_id: int, session_id: Optional[str]) -> None:
    """Reject writes to a chat session that already belongs to another user."""
    if not session_id:
        return

    owner = db.query(Conversation.user_id).filter(
        Conversation.session_id == session_id,
    ).order_by(Conversation.id.asc()).first()
    if owner and owner[0] != user_id:
        raise HTTPException(status_code=404, detail="会话不存在")


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
        return ProductMemoryService(db).capture_user_message(
            user_id=user_id,
            conversation_id=conversation_id,
            message=message,
            context=context,
            is_sensitive=is_sensitive,
        )
    except Exception as exc:
        logger.warning("Failed to update chat memory state: %s", exc)
        return {"updated": False, "count": 0, "categories": [], "reason": "error"}


def _truncate_client_context(text: str, limit: int = 500) -> str:
    """Bound client-provided context before it is used as prompt-only history."""
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1]}…"


def _parse_client_context_messages(client_context: Optional[str], current_message: str = "") -> List[Dict[str, str]]:
    """Parse recent client-visible chat turns as bounded, prompt-only fallback context."""
    if not client_context:
        return []

    try:
        payload = json.loads(client_context)
    except (json.JSONDecodeError, TypeError):
        return []

    if not isinstance(payload, list):
        return []

    safe_messages: List[Dict[str, str]] = []
    for item in payload[-12:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = _truncate_client_context(str(item.get("content") or ""))
        if role not in {"user", "assistant"} or not content:
            continue
        safe_messages.append({"role": role, "content": content})

    current = " ".join((current_message or "").split())
    while safe_messages and safe_messages[-1]["role"] == "user" and safe_messages[-1]["content"] == current:
        safe_messages.pop()

    return safe_messages


def _format_client_recent_context(messages: List[Dict[str, str]]) -> str:
    """Format client fallback turns like DB recent context."""
    if not messages:
        return "暂无最近对话。"
    return "\n".join(f"{item['role']}: {item['content']}" for item in messages)


def _merge_client_context_into_memory(
    conversation_memory: Dict[str, object],
    client_messages: List[Dict[str, str]],
) -> Dict[str, object]:
    """Use client-visible history only when server-side session turns are unavailable."""
    memory = dict(conversation_memory or {})
    memory_state = dict(memory.get("memory_state") or {})
    has_server_messages = bool(memory.get("conversation_messages"))
    memory_state["client_context_used"] = False
    memory_state["client_context_turns"] = len(client_messages)

    if client_messages and not has_server_messages:
        memory["conversation_messages"] = client_messages
        if not memory.get("recent_context") or memory.get("recent_context") == "暂无最近对话。":
            memory["recent_context"] = _format_client_recent_context(client_messages)
        memory_state["client_context_used"] = True

    memory["memory_state"] = memory_state
    return memory


def _build_conversation_memory_context(
    db: Session,
    user_id: int,
    session_id: str,
    query_message: str,
    client_context: Optional[str] = None,
) -> Dict[str, object]:
    """Build server memory, with bounded client-visible history as fallback only."""
    memory_service = ProductMemoryService(db)
    conversation_memory = memory_service.build_prompt_context(
        user_id=user_id,
        session_id=session_id,
        query_message=query_message,
    )
    client_messages = _parse_client_context_messages(client_context, query_message)
    return _merge_client_context_into_memory(conversation_memory, client_messages)


async def _websocket_chat_authenticated(websocket: WebSocket):
    """
    WebSocket AI对话
    触发条件：用户点击聊聊按钮或系统检测到情绪波动升高
    支持多轮上下文记忆
    """
    db = SessionLocal()
    user_id = await _authenticate_websocket(websocket, db)
    if user_id is None:
        db.close()
        return

    session_id = str(uuid.uuid4())
    await manager.connect(websocket, session_id, user_id)

    agent_service = get_agent_service()
    nlp_service = NLPService()

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
            client_context = data.get("client_context")

            if not user_message:
                continue

            # Analyze user message
            nlp_result = await nlp_service.analyze_text(user_message)
            intent = nlp_service.get_intent(user_message)
            is_sensitive = nlp_service.check_sensitive(user_message)
            nlp_result["intent"] = intent
            nlp_result["conversation_memory"] = _build_conversation_memory_context(
                db=db,
                user_id=user_id,
                session_id=session_id,
                query_message=user_message,
                client_context=client_context,
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
            if assessment_result.assessment_prompt_hint and not response.get("suppress_assessment_prompt"):
                response["message"] = f"{response["message"]}\n\n{assessment_result.assessment_prompt_hint}"

            needs_llm_followup = response.get("needs_llm_followup", False)

            last_turn = db.query(func.max(Conversation.turn_number)).filter(
                Conversation.user_id == user_id,
                Conversation.session_id == session_id,
            ).scalar() or 0
            user_turn = last_turn + 1
            assistant_turn = last_turn + 2

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

            async def _send_llm_followup() -> None:
                """Background task: call LLM for a deeper reply, then send to the client."""
                print(f"[_send_llm_followup] START user_message={user_message[:20]}...")
                await asyncio.sleep(0)
                db_followup = SessionLocal()
                try:
                    print(f"[_send_llm_followup] analyzing NLP...")
                    nlp_followup = await nlp_service.analyze_text(user_message)
                    print(f"[_send_llm_followup] NLP done, sentiment={nlp_followup.get('sentiment_score')}")
                    intent_followup = nlp_service.get_intent(user_message)
                    nlp_followup["intent"] = intent_followup
                    nlp_followup["conversation_memory"] = _build_conversation_memory_context(
                        db=db_followup,
                        user_id=user_id,
                        session_id=session_id,
                        query_message=user_message,
                        client_context=client_context,
                    )
                    assessment_followup = AssessmentOrchestrator(db_followup)
                    assessment_followup.prepare_turn(
                        user_id=user_id,
                        chat_session_id=session_id,
                        user_message=user_message,
                        context=nlp_followup,
                    )

                    llm_response = await agent_service.get_response(
                        user_id=user_id,
                        session_id=session_id,
                        user_message=user_message,
                        context=nlp_followup,
                        agent_mode=agent_mode,
                        skip_deterministic_reply=True,
                    )
                    print(f"[_send_llm_followup] LLM done, reply_len={len(llm_response.get('message',''))}")

                    last_t = db_followup.query(func.max(Conversation.turn_number)).filter(
                        Conversation.user_id == user_id,
                        Conversation.session_id == session_id,
                    ).scalar() or 0
                    followup_turn = last_t + 1
                    followup_conv = Conversation(
                        user_id=user_id,
                        session_id=session_id,
                        turn_number=followup_turn,
                        role="assistant",
                        content=llm_response["message"],
                    )
                    db_followup.add(followup_conv)
                    db_followup.commit()
                    llm_state = llm_response.get("state", {}) or {}
                    await websocket.send_json({
                        "type": "llm_followup",
                        "message": llm_response["message"],
                        "sentiment_score": nlp_followup.get("sentiment_score", 0.0),
                        "intent": llm_response.get("intent", "support"),
                        "is_sensitive": is_sensitive,
                        "suggestions": llm_response.get("suggestions", []),
                        "actions": llm_response.get("actions", []),
                        "risk_level": llm_state.get("risk_level", "low"),
                        "reply_status": llm_response.get("reply_status", "ok"),
                        "elapsed_ms": llm_response.get("elapsed_ms", 0),
                        "memory_state": memory_state,
                    })
                except Exception as ex:
                    print(f"[_send_llm_followup] error: {ex}")
                finally:
                    db_followup.close()

            if needs_llm_followup:
                asyncio.get_running_loop().create_task(_send_llm_followup())

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


@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    """Authenticated WebSocket chat endpoint."""
    await _websocket_chat_authenticated(websocket)


@router.websocket("/ws/{path_user_id}")
async def websocket_chat_legacy(websocket: WebSocket, path_user_id: int):
    """Legacy WebSocket path; path_user_id is ignored and token identity wins."""
    await _websocket_chat_authenticated(websocket)


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
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
async def create_chat_session(user_id: int = Depends(get_current_user_id)):
    """创建新的对话会话"""
    session_id = str(uuid.uuid4())
    return {
        "session_id": session_id,
        "created_at": datetime.now().isoformat()
    }


@router.post("/message")
async def send_chat_message(
    message: str = Form(...),
    user_id: int = Depends(get_current_user_id),
    session_id: Optional[str] = Form(None),
    cycle_phase: Optional[str] = Form(None),
    agent_mode: str = Form("auto"),
    client_context: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """直接发送消息获取AI回复（REST API，非WebSocket）"""
    if not session_id:
        session_id = str(uuid.uuid4())
    else:
        _ensure_chat_session_access(db, user_id, session_id)

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
    context["conversation_memory"] = _build_conversation_memory_context(
        db=db,
        user_id=user_id,
        session_id=session_id,
        query_message=message,
        client_context=client_context,
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
    if assessment_result.assessment_prompt_hint and not response.get("suppress_assessment_prompt"):
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
    user_id: int = Depends(get_current_user_id),
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


@router.post("/stream")
async def stream_chat_message(
    message: str = Form(...),
    user_id: int = Depends(get_current_user_id),
    session_id: Optional[str] = Form(None),
    cycle_phase: Optional[str] = Form(None),
    agent_mode: str = Form("auto"),
    client_context: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """SSE 流式聊天接口 - 支持双通道响应（确定性回复 + LLM深度回复）"""
    if not message:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    if not session_id:
        session_id = str(uuid.uuid4())
    else:
        _ensure_chat_session_access(db, user_id, session_id)

    agent_service = get_agent_service()
    nlp_service = NLPService()

    nlp_result, intent, is_sensitive = await asyncio.gather(
        nlp_service.analyze_text(message),
        asyncio.to_thread(nlp_service.get_intent, message),
        asyncio.to_thread(nlp_service.check_sensitive, message),
    )

    context = {
        **nlp_result,
        "intent": intent,
        "cycle_phase": cycle_phase,
        "sensor_data": {}
    }
    context["conversation_memory"] = _build_conversation_memory_context(
        db=db,
        user_id=user_id,
        session_id=session_id,
        query_message=message,
        client_context=client_context,
    )

    # 构建 perception + 上下文（只做一次，后续 streaming 复用）
    state, _ = await agent_service.prepare_streaming_state(message, context, agent_mode)
    risk_level = state.get("risk_level", "low")

    async def event_stream() -> AsyncGenerator[str, None]:
        # 全部走 LLM 流式响应，无模板直接回复
        full_response = ""
        
        async for chunk in agent_service.get_streaming_response(
            user_id=user_id,
            session_id=session_id,
            user_message=message,
            context=context,
            agent_mode=agent_mode,
            pre_built_state=state,
        ):
                chunk_type = chunk.get("type")

                if chunk_type == "start":
                    data = {
                        'type': 'start',
                        'session_id': session_id,
                        'risk_level': chunk.get('risk_level', 'low'),
                        'agent_name': chunk.get('agent_name', 'support'),
                    }
                    yield f"data: {json.dumps(data)}\n\n"

                elif chunk_type == "token":
                    token = chunk.get("token", "")
                    full_response += token
                    data = {
                        'type': 'token',
                        'token': token,
                        'is_final': chunk.get('is_final', False),
                        'first_token_latency_ms': chunk.get('first_token_latency_ms', 0),
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                
                elif chunk_type == "end":
                    final_response = chunk.get("full_response") or full_response
                    full_response = final_response

                    # 保存对话记录（用户消息 + 两条AI回复）
                    last_turn = db.query(func.max(Conversation.turn_number)).filter(
                        Conversation.user_id == user_id,
                        Conversation.session_id == session_id,
                    ).scalar() or 0
                    
                    user_conv = Conversation(
                        user_id=user_id,
                        session_id=session_id,
                        turn_number=last_turn + 1,
                        role="user",
                        content=message,
                        intent=intent,
                        sentiment_score=nlp_result.get("sentiment_score"),
                        is_sensitive=1 if is_sensitive else 0,
                    )
                    # 保存 LLM 回复
                    llm_conv = Conversation(
                        user_id=user_id,
                        session_id=session_id,
                        turn_number=last_turn + 2,
                        role="assistant",
                        content=final_response,
                    )
                    db.add(user_conv)
                    db.add(llm_conv)
                    db.commit()
                    
                    memory_state = _safe_capture_memory(
                        db=db,
                        user_id=user_id,
                        conversation_id=user_conv.id,
                        message=message,
                        context=context,
                        is_sensitive=is_sensitive,
                    )

                    data = {
                        'type': 'end',
                        'session_id': session_id,
                        'full_response': final_response,
                        'actions': chunk.get('actions', []),
                        'elapsed_ms': chunk.get('elapsed_ms', 0),
                        'memory_state': memory_state,
                    }
                    yield f"data: {json.dumps(data)}\n\n"
    
    # 如果不需要 LLM followup，保存单条回复
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
            "X-Accel-Buffering": "no",
        }
    )
