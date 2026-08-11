from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.biometric import BiometricData
from app.models.mood import MoodDiary
from app.models.menstrual import MenstrualRecord
from app.schemas.emotion import EmotionPredictResponse, InterventionRecommendResponse
from app.schemas.menstrual import CyclePredictResponse
from app.services.emotion_engine import EmotionEngine
from app.services.cycle_predictor import CyclePredictor
from app.services.emotion_classifier import classify_emotion, emotion_classifier
from app.api.v1.deps import get_current_user_id

router = APIRouter(prefix="/emotion", tags=["情绪分析"])


@router.get("/predict", response_model=EmotionPredictResponse)
async def predict_emotion(
    user_id: int = Depends(get_current_user_id),
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    情绪分析引擎 - 综合分析当前情绪状态
    触发条件：任一数据源更新后立即启动
    前置条件：用户至少完成一次月经周期记录
    """
    engine = EmotionEngine(db)

    try:
        result = await engine.analyze(user_id, days)

        return EmotionPredictResponse(
            phase=result["phase"],
            pms_risk=result["pms_risk"],
            mood_level=result["mood_level"],
            confidence=result["confidence"],
            updated_at=result["updated_at"]
        )
    except ValueError as e:
        # New user with no history
        return EmotionPredictResponse(
            phase="unknown",
            pms_risk=0.5,
            mood_level=5.0,
            confidence=0.0,
            updated_at=func.now()
        )


@router.get("/intervention/recommend", response_model=InterventionRecommendResponse)
async def recommend_intervention(
    user_id: int = Depends(get_current_user_id),
    context: str = "mood_low",  # mood_low, stress, anxiety, normal
    db: Session = Depends(get_db)
):
    """
    获取干预建议
    触发条件：情绪分析引擎输出pmsRisk >= 0.7
    """
    engine = EmotionEngine(db)
    recommendations = engine.get_intervention_recommendations(user_id, context)

    reasons = {
        "breathing_exercise": "帮助调节呼吸，降低心率",
        "music_therapy": "放松心情，缓解焦虑",
        "walking": "轻度运动促进血液循环",
        "hot_compress": "缓解身体不适"
    }

    return InterventionRecommendResponse(
        recommendations=recommendations,
        reasons={k: reasons.get(k, "") for k in recommendations},
        priority="high" if len(recommendations) > 2 else "medium"
    )


@router.get("/phase")
async def get_current_phase(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """获取用户当前所处周期阶段"""
    engine = EmotionEngine(db)
    phase = engine.get_current_phase(user_id)

    phase_info = {
        "follicular": {"name": "卵泡期", "days": "第1-7天", "description": "精力恢复期"},
        "ovulation": {"name": "排卵期", "days": "第8-14天", "description": "情绪高峰期"},
        "luteal": {"name": "黄体期", "days": "第15-28天", "description": "留意经前不适"},
        "menstrual": {"name": "经期", "days": "出血日", "description": "注意休息"},
        "unknown": {"name": "未知", "days": "-", "description": "数据不足"}
    }

    return {
        "phase": phase,
        **phase_info.get(phase, phase_info["unknown"])
    }


@router.get("/classify")
async def classify_emotion_from_biometric(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    基于生理数据（心率、温度、运动）分类情绪
    返回四种情绪状态：抑郁、焦虑、愤怒、平静

    注意: 数据库中的 hrv 字段实际存储的是心率(bpm)
    """
    # 获取最新的生理数据
    latest = db.query(BiometricData).filter(
        BiometricData.user_id == user_id
    ).order_by(BiometricData.timestamp.desc()).first()

    if not latest:
        return {
            "error": "暂无生理数据",
            "emotion": {
                "depression": 0,
                "anxiety": 0,
                "anger": 0,
                "calm": 0,
                "dominant": "未知"
            }
        }

    # 分类情绪 (hrv字段实际存的是心率bpm)
    result = classify_emotion(
        heart_rate=latest.hrv,
        skin_temperature=latest.skin_temperature,
        motion=latest.motion
    )

    return {
        "biometric": {
            "heart_rate": latest.hrv,  # 实际是心率bpm
            "temperature": latest.skin_temperature,
            "motion": latest.motion,
            "timestamp": latest.timestamp.isoformat() if latest.timestamp else None
        },
        "emotion": result
    }
