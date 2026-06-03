from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, time, timedelta
import json
import logging

from app.database import get_db
from app.models.mood import MoodDiary, DiaryDraft
from app.schemas.diary import MoodDiaryCreate, MoodDiaryUpdate, MoodDiaryResponse, MoodDiaryListResponse, DiaryDraftCreate, DiaryDraftResponse
from app.services.nlp_service import NLPService
from app.api.v1.deps import get_current_user_id

router = APIRouter(prefix="/diary", tags=["情绪日记"])
logger = logging.getLogger(__name__)


def success_response(data=None, message="success", code=200):
    return {"code": code, "data": data, "message": message}


def error_response(message, code=400):
    return {"code": code, "data": None, "message": message}


@router.post("")
async def create_mood_diary(
    diary: MoodDiaryCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    diary_date = datetime.fromisoformat(diary.date.replace('Z', '+00:00')) if diary.date else datetime.now()
    day_start = datetime.combine(diary_date.date(), time.min)
    day_end = datetime.combine(diary_date.date(), time.max)

    today_count = db.query(MoodDiary).filter(
        MoodDiary.user_id == user_id,
        MoodDiary.date >= day_start,
        MoodDiary.date <= day_end
    ).count()

    if today_count >= 2:
        logger.warning(f"User {user_id} exceeded daily diary limit")
        raise HTTPException(status_code=400, detail="每天最多只能写两篇日记")

    nlp_service = NLPService()

    if diary.original_text and not diary.processed_text:
        nlp_result = await nlp_service.analyze_text(diary.original_text)
        diary.processed_text = nlp_result["processed_text"]
        if not diary.emotion_tags:
            diary.emotion_tags = nlp_result["emotion_tags"]
        if not diary.emotion_scores:
            diary.emotion_scores = nlp_result["emotion_scores"]
        if not diary.mood_level:
            diary.mood_level = nlp_result["mood_level"]
        if not diary.keywords:
            diary.keywords = nlp_result["keywords"]

    mood_diary = MoodDiary(
        user_id=user_id,
        date=diary.date,
        input_type=diary.input_type,
        original_text=diary.original_text,
        processed_text=diary.processed_text,
        emotion_tags=json.dumps(diary.emotion_tags) if diary.emotion_tags else None,
        emotion_scores=json.dumps(diary.emotion_scores) if diary.emotion_scores else None,
        mood_level=diary.mood_level,
        keywords=json.dumps(diary.keywords) if diary.keywords else None
    )

    db.add(mood_diary)
    db.commit()
    db.refresh(mood_diary)

    logger.info({
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "action": "create_diary",
        "diary_id": mood_diary.id,
        "details": {
            "input_type": diary.input_type,
            "emotion_tags": diary.emotion_tags
        },
        "result": "success"
    })

    if mood_diary.emotion_tags:
        mood_diary.emotion_tags = json.loads(mood_diary.emotion_tags)
    if mood_diary.emotion_scores:
        mood_diary.emotion_scores = json.loads(mood_diary.emotion_scores)
    if mood_diary.keywords:
        mood_diary.keywords = json.loads(mood_diary.keywords)

    return success_response(data=MoodDiaryResponse.model_validate(mood_diary).model_dump(), message="日记保存成功")


@router.get("")
async def get_mood_diaries(
    user_id: int = Depends(get_current_user_id),
    limit: int = 30,
    offset: int = 0,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(MoodDiary).filter(MoodDiary.user_id == user_id)

    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.filter(MoodDiary.date >= from_date)
        except ValueError:
            pass

    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.filter(MoodDiary.date <= to_date)
        except ValueError:
            pass

    total = query.count()

    diaries = query.order_by(MoodDiary.date.desc()).offset(offset).limit(limit).all()

    for diary in diaries:
        if diary.emotion_tags:
            diary.emotion_tags = json.loads(diary.emotion_tags)
        if diary.emotion_scores:
            diary.emotion_scores = json.loads(diary.emotion_scores)
        if diary.keywords:
            diary.keywords = json.loads(diary.keywords)

    diary_responses = [MoodDiaryResponse.model_validate(d).model_dump() for d in diaries]
    return success_response(data={"diaries": diary_responses, "total": total}, message="success")


@router.get("/today")
async def get_today_diary(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    today_start = datetime.combine(date.today(), time.min)
    today_end = datetime.combine(date.today(), time.max)
    diary = db.query(MoodDiary).filter(
        MoodDiary.user_id == user_id,
        MoodDiary.date >= today_start,
        MoodDiary.date <= today_end
    ).first()

    if not diary:
        return success_response(data={
            "has_diary": False,
            "content": None,
            "emotion_tags": [],
            "created_at": None
        }, message="success")

    emotion_tags = []
    if diary.emotion_tags:
        emotion_tags = json.loads(diary.emotion_tags)

    return success_response(data={
        "has_diary": True,
        "content": diary.original_text or diary.processed_text,
        "emotion_tags": emotion_tags,
        "created_at": diary.created_at.isoformat() if diary.created_at else None
    }, message="success")


@router.get("/{diary_id}")
async def get_mood_diary(
    diary_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    diary = db.query(MoodDiary).filter(
        MoodDiary.id == diary_id,
        MoodDiary.user_id == user_id,
    ).first()

    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")

    if diary.emotion_tags:
        diary.emotion_tags = json.loads(diary.emotion_tags)
    if diary.emotion_scores:
        diary.emotion_scores = json.loads(diary.emotion_scores)
    if diary.keywords:
        diary.keywords = json.loads(diary.keywords)

    return success_response(data=MoodDiaryResponse.model_validate(diary).model_dump(), message="success")


@router.put("/{diary_id}")
async def update_mood_diary(
    diary_id: int,
    diary: MoodDiaryUpdate,
    skip_nlp: Optional[bool] = False,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    existing = db.query(MoodDiary).filter(
        MoodDiary.id == diary_id,
        MoodDiary.user_id == user_id,
    ).first()

    if not existing:
        raise HTTPException(status_code=404, detail="日记不存在")

    changed_fields = []

    if not skip_nlp and diary.original_text and diary.original_text != existing.original_text:
        nlp_service = NLPService()
        nlp_result = await nlp_service.analyze_text(diary.original_text)

        existing.processed_text = nlp_result["processed_text"]
        existing.emotion_tags = json.dumps(nlp_result["emotion_tags"])
        existing.emotion_scores = json.dumps(nlp_result["emotion_scores"])
        existing.mood_level = nlp_result["mood_level"]
        existing.keywords = json.dumps(nlp_result["keywords"])
        changed_fields = ["processed_text", "emotion_tags", "emotion_scores", "mood_level", "keywords"]
    else:
        if diary.original_text:
            existing.original_text = diary.original_text
            changed_fields.append("original_text")
            if not skip_nlp and diary.original_text != existing.processed_text:
                nlp_service = NLPService()
                nlp_result = await nlp_service.analyze_text(diary.original_text)
                existing.processed_text = nlp_result["processed_text"]
                existing.keywords = json.dumps(nlp_result["keywords"])
        if diary.processed_text:
            existing.processed_text = diary.processed_text
        if diary.emotion_tags is not None:
            existing.emotion_tags = json.dumps(diary.emotion_tags)
            changed_fields.append("emotion_tags")
        if diary.emotion_scores:
            existing.emotion_scores = json.dumps(diary.emotion_scores)
            changed_fields.append("emotion_scores")
        if diary.mood_level is not None:
            existing.mood_level = diary.mood_level
            changed_fields.append("mood_level")

    db.commit()
    db.refresh(existing)

    logger.info({
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "action": "update_diary",
        "diary_id": diary_id,
        "details": {"changed_fields": changed_fields},
        "result": "success"
    })

    if existing.emotion_tags:
        existing.emotion_tags = json.loads(existing.emotion_tags)
    if existing.emotion_scores:
        existing.emotion_scores = json.loads(existing.emotion_scores)
    if existing.keywords:
        existing.keywords = json.loads(existing.keywords)

    return success_response(data=MoodDiaryResponse.model_validate(existing).model_dump(), message="日记已更新")


@router.delete("/{diary_id}")
async def delete_mood_diary(
    diary_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    diary = db.query(MoodDiary).filter(
        MoodDiary.id == diary_id,
        MoodDiary.user_id == user_id,
    ).first()

    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")

    db.delete(diary)
    db.commit()

    logger.info({
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "action": "delete_diary",
        "diary_id": diary_id,
        "result": "success"
    })

    return success_response(data=None, message="日记已删除")


@router.post("/draft")
async def save_draft(
    draft: DiaryDraftCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    existing_draft = db.query(DiaryDraft).filter(DiaryDraft.user_id == user_id).first()

    if existing_draft:
        existing_draft.content = draft.content
        existing_draft.emotion_tags = json.dumps(draft.emotion_tags) if draft.emotion_tags else None
        existing_draft.mood_level = draft.mood_level
        existing_draft.updated_at = datetime.now()
        db.commit()
        db.refresh(existing_draft)
        draft_id = existing_draft.id
    else:
        new_draft = DiaryDraft(
            user_id=user_id,
            content=draft.content,
            emotion_tags=json.dumps(draft.emotion_tags) if draft.emotion_tags else None,
            mood_level=draft.mood_level
        )
        db.add(new_draft)
        db.commit()
        db.refresh(new_draft)
        draft_id = new_draft.id

    return success_response(data={"draft_id": draft_id}, message="草稿保存成功")


@router.get("/draft")
async def get_draft(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    draft = db.query(DiaryDraft).filter(DiaryDraft.user_id == user_id).first()

    if not draft:
        return success_response(data=None, message="暂无草稿")

    if draft.created_at < datetime.now() - timedelta(hours=24):
        db.delete(draft)
        db.commit()
        return success_response(data=None, message="草稿已过期")

    if draft.emotion_tags:
        draft.emotion_tags = json.loads(draft.emotion_tags)

    return success_response(data=DiaryDraftResponse.model_validate(draft).model_dump(), message="success")


@router.delete("/draft")
async def delete_draft(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    draft = db.query(DiaryDraft).filter(DiaryDraft.user_id == user_id).first()

    if draft:
        db.delete(draft)
        db.commit()

    return success_response(data=None, message="草稿已删除")


@router.post("/draft/publish")
async def publish_draft(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    draft = db.query(DiaryDraft).filter(DiaryDraft.user_id == user_id).first()

    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")

    if draft.created_at < datetime.now() - timedelta(hours=24):
        db.delete(draft)
        db.commit()
        raise HTTPException(status_code=400, detail="草稿已过期")

    day_start = datetime.combine(datetime.now().date(), time.min)
    day_end = datetime.combine(datetime.now().date(), time.max)
    today_count = db.query(MoodDiary).filter(
        MoodDiary.user_id == user_id,
        MoodDiary.date >= day_start,
        MoodDiary.date <= day_end
    ).count()

    if today_count >= 2:
        raise HTTPException(status_code=400, detail="每天最多只能写两篇日记")

    emotion_tags = json.loads(draft.emotion_tags) if draft.emotion_tags else None

    nlp_service = NLPService()
    processed_text = draft.content
    nlp_result = {"emotion_tags": emotion_tags, "emotion_scores": None, "mood_level": draft.mood_level, "keywords": None}
    if draft.content:
        nlp_result = nlp_service.analyze_text(draft.content)

    mood_diary = MoodDiary(
        user_id=user_id,
        date=datetime.now(),
        input_type="text",
        original_text=draft.content,
        processed_text=processed_text,
        emotion_tags=json.dumps(nlp_result["emotion_tags"]) if nlp_result["emotion_tags"] else None,
        emotion_scores=json.dumps(nlp_result["emotion_scores"]) if nlp_result["emotion_scores"] else None,
        mood_level=draft.mood_level or nlp_result["mood_level"],
        keywords=json.dumps(nlp_result["keywords"]) if nlp_result.get("keywords") else None
    )

    db.add(mood_diary)
    db.delete(draft)
    db.commit()
    db.refresh(mood_diary)

    logger.info({
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "action": "publish_draft",
        "diary_id": mood_diary.id,
        "result": "success"
    })

    if mood_diary.emotion_tags:
        mood_diary.emotion_tags = json.loads(mood_diary.emotion_tags)
    if mood_diary.emotion_scores:
        mood_diary.emotion_scores = json.loads(mood_diary.emotion_scores)
    if mood_diary.keywords:
        mood_diary.keywords = json.loads(mood_diary.keywords)

    return success_response(data=MoodDiaryResponse.model_validate(mood_diary).model_dump(), message="日记发布成功")
