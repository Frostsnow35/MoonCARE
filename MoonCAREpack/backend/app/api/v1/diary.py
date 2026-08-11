from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, time
import json

from app.database import get_db
from app.models.mood import MoodDiary
from app.schemas.diary import MoodDiaryCreate, MoodDiaryUpdate, MoodDiaryResponse, MoodDiaryListResponse
from app.services.nlp_service import NLPService
from app.api.v1.deps import get_current_user_id

router = APIRouter(prefix="/diary", tags=["情绪日记"])


@router.post("", response_model=MoodDiaryResponse)
async def create_mood_diary(
    diary: MoodDiaryCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    创建情绪日记
    触发条件：用户进入情绪日记页面并开始录音或输入文字
    前置条件：麦克风权限已授权
    """
    nlp_service = NLPService()

    # Process text with NLP if not provided
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

    # Parse JSON fields for response
    if mood_diary.emotion_tags:
        mood_diary.emotion_tags = json.loads(mood_diary.emotion_tags)
    if mood_diary.emotion_scores:
        mood_diary.emotion_scores = json.loads(mood_diary.emotion_scores)
    if mood_diary.keywords:
        mood_diary.keywords = json.loads(mood_diary.keywords)

    return mood_diary


@router.get("", response_model=MoodDiaryListResponse)
async def get_mood_diaries(
    user_id: int = Depends(get_current_user_id),
    limit: int = 30,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """获取情绪日记列表"""
    query = db.query(MoodDiary).filter(MoodDiary.user_id == user_id)
    total = query.count()

    diaries = query.order_by(MoodDiary.date.desc()).offset(offset).limit(limit).all()

    # Parse JSON fields
    for diary in diaries:
        if diary.emotion_tags:
            diary.emotion_tags = json.loads(diary.emotion_tags)
        if diary.emotion_scores:
            diary.emotion_scores = json.loads(diary.emotion_scores)
        if diary.keywords:
            diary.keywords = json.loads(diary.keywords)

    return MoodDiaryListResponse(diaries=diaries, total=total)


@router.get("/today")
async def get_today_diary(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    获取当日日记，用于聊天Agent个性化问候
    """
    today_start = datetime.combine(date.today(), time.min)
    today_end = datetime.combine(date.today(), time.max)
    diary = db.query(MoodDiary).filter(
        MoodDiary.user_id == user_id,
        MoodDiary.date >= today_start,
        MoodDiary.date <= today_end
    ).first()

    if not diary:
        return {
            "has_diary": False,
            "content": None,
            "emotion_tags": [],
            "created_at": None
        }

    emotion_tags = []
    if diary.emotion_tags:
        emotion_tags = json.loads(diary.emotion_tags)

    return {
        "has_diary": True,
        "content": diary.original_text or diary.processed_text,
        "emotion_tags": emotion_tags,
        "created_at": diary.created_at.isoformat() if diary.created_at else None
    }


@router.get("/{diary_id}", response_model=MoodDiaryResponse)
async def get_mood_diary(
    diary_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """获取单条情绪日记"""
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

    return diary


@router.put("/{diary_id}", response_model=MoodDiaryResponse)
async def update_mood_diary(
    diary_id: int,
    diary: MoodDiaryUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    更新情绪日记（编辑修改转写文本）
    支持编辑后重新分析标签
    """
    existing = db.query(MoodDiary).filter(
        MoodDiary.id == diary_id,
        MoodDiary.user_id == user_id,
    ).first()

    if not existing:
        raise HTTPException(status_code=404, detail="日记不存在")

    # If text was updated, re-analyze
    if diary.original_text and diary.original_text != existing.original_text:
        nlp_service = NLPService()
        nlp_result = await nlp_service.analyze_text(diary.original_text)

        existing.processed_text = nlp_result["processed_text"]
        existing.emotion_tags = json.dumps(nlp_result["emotion_tags"])
        existing.emotion_scores = json.dumps(nlp_result["emotion_scores"])
        existing.mood_level = nlp_result["mood_level"]
        existing.keywords = json.dumps(nlp_result["keywords"])
    else:
        # Just update provided fields
        if diary.emotion_tags:
            existing.emotion_tags = json.dumps(diary.emotion_tags)
        if diary.emotion_scores:
            existing.emotion_scores = json.dumps(diary.emotion_scores)
        if diary.mood_level:
            existing.mood_level = diary.mood_level

    db.commit()
    db.refresh(existing)

    if existing.emotion_tags:
        existing.emotion_tags = json.loads(existing.emotion_tags)
    if existing.emotion_scores:
        existing.emotion_scores = json.loads(existing.emotion_scores)
    if existing.keywords:
        existing.keywords = json.loads(existing.keywords)

    return existing


@router.delete("/{diary_id}")
async def delete_mood_diary(
    diary_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """删除情绪日记"""
    diary = db.query(MoodDiary).filter(
        MoodDiary.id == diary_id,
        MoodDiary.user_id == user_id,
    ).first()

    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")

    db.delete(diary)
    db.commit()

    return {"status": "success", "msg": "日记已删除"}
