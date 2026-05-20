from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.psst_scoring_service import PSSTScoringService
from app.services.report_service import ReportService
from app.agents.interview_agent import InterviewAgent
from app.agents.intervention_agent import InterventionAgent
from app.api.v1.deps import get_current_user_id

router = APIRouter(prefix="/interview", tags=["经前状态了解"])


class InterviewMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class InterviewStartResponse(BaseModel):
    reply: str
    phase: int = 1
    is_complete: bool = False


class InterviewTurnRequest(BaseModel):
    messages: List[InterviewMessage] = Field(default_factory=list)


class InterviewTurnResponse(BaseModel):
    reply: str
    phase: int = 1
    is_complete: bool = False
    crisis: bool = False
    psst: Optional[dict] = None
    report: Optional[str] = None


# In-memory storage for interview sessions (in production, use Redis or DB)
interview_sessions = {}


@router.post("/start", response_model=InterviewStartResponse)
async def start_interview(user_id: int = Depends(get_current_user_id)):
    """开始经前状态了解对话"""
    interview_agent = InterviewAgent()
    reply = interview_agent.start()

    interview_sessions[user_id] = {
        "agent": interview_agent,
        "started": True
    }

    return InterviewStartResponse(
        reply=reply,
        phase=1,
        is_complete=False
    )


@router.post("/turn", response_model=InterviewTurnResponse)
async def interview_turn(
    request: InterviewTurnRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """继续经前状态了解对话"""
    if user_id not in interview_sessions:
        return InterviewTurnResponse(
            reply="请先调用 /interview/start 开始访谈",
            phase=0,
            is_complete=False
        )

    interview_agent = interview_sessions[user_id]["agent"]

    # 检测危机
    crisis_detected = interview_agent.detect_crisis(request.messages)

    if crisis_detected:
        intervention_agent = InterventionAgent()
        state = {"risk_level": "crisis", "cycle_phase": "经前期"}
        reply = intervention_agent.respond(
            request.messages[-1].content if request.messages else "",
            state
        )
        return InterviewTurnResponse(
            reply=reply,
            phase=99,
            is_complete=True,
            crisis=True
        )

    # 正常流程：获取下一轮回复
    reply = interview_agent.next_turn(request.messages)

    # 判断是否完成（6轮后）
    is_complete = len([m for m in request.messages if m.role == "assistant"]) >= 6

    # 如果完成，进行评分
    psst_result = None
    report_text = None

    if is_complete:
        psst_service = PSSTScoringService()
        report_service = ReportService()

        # 合并所有用户输入
        user_blob = " ".join(m.content for m in request.messages if m.role == "user")
        signals = psst_service.signals_from_user_text(user_blob)
        psst_result = psst_service.score_from_ratings(signals)
        report_text = report_service.build_screening_report(psst_result)

    return InterviewTurnResponse(
        reply=reply,
        phase=min(len([m for m in request.messages if m.role == "assistant"]) + 1, 7),
        is_complete=is_complete,
        crisis=False,
        psst=psst_result,
        report=report_text
    )


@router.post("/knowledge")
async def ask_knowledge(
    question: str,
    user_id: int = Depends(get_current_user_id)
):
    """直接查询经期/PMS相关知识库"""
    from app.agents.knowledge_agent import KnowledgeAgent

    knowledge_agent = KnowledgeAgent()
    reply = knowledge_agent.respond(question, {})

    return {"reply": reply}
