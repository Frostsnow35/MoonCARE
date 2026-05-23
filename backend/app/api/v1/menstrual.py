from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any, List
import json

from app.database import get_db
from app.models.menstrual import MenstrualRecord
from app.models.mood import MoodDiary
from app.schemas.menstrual import MenstrualRecordCreate, MenstrualRecordResponse, CyclePredictResponse
from app.services.cycle_predictor import CyclePredictor
from app.api.v1.deps import get_current_user_id

router = APIRouter(prefix="/menstrual", tags=["月经周期"])


def _decode_symptoms(value: Any) -> List[str] | None:
    """Decode symptoms stored as JSON text into a response-ready list."""
    if not value:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            if isinstance(decoded, list):
                return [str(item) for item in decoded]
        except json.JSONDecodeError:
            return [value]
    return [str(value)]


def _prepare_record_response(record: MenstrualRecord) -> MenstrualRecord:
    """Normalize DB-only fields before FastAPI response validation."""
    record.symptoms = _decode_symptoms(record.symptoms)
    return record


@router.post("/record", response_model=MenstrualRecordResponse)
async def create_menstrual_record(
    record: MenstrualRecordCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    手动记录月经
    触发条件：用户进入周期记录页面并执行标记操作
    前置条件：用户已登录账户
    """
    # Check for duplicate start date
    existing = db.query(MenstrualRecord).filter(
        MenstrualRecord.user_id == user_id,
        MenstrualRecord.start_date == record.start_date
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="该日期已有记录，是否覆盖？"
        )

    # Calculate duration
    duration = None
    if record.end_date:
        duration = (record.end_date - record.start_date).days

    # Get cycle number
    last_record = db.query(MenstrualRecord).filter(
        MenstrualRecord.user_id == user_id
    ).order_by(MenstrualRecord.start_date.desc()).first()

    cycle_number = 1
    if last_record:
        cycle_number = last_record.cycle_number + 1 if last_record.cycle_number else 1

    # Create record
    menstrual_record = MenstrualRecord(
        user_id=user_id,
        cycle_number=cycle_number,
        start_date=record.start_date,
        end_date=record.end_date,
        duration=duration,
        flow_intensity=record.flow_intensity,
        symptoms=json.dumps(record.symptoms) if record.symptoms else None,
        notes=record.notes
    )

    db.add(menstrual_record)
    db.commit()
    db.refresh(menstrual_record)

    # Update prediction
    predictor = CyclePredictor(db)
    predictor.update_prediction(user_id)

    return _prepare_record_response(menstrual_record)


@router.get("/records", response_model=List[MenstrualRecordResponse])
async def get_menstrual_records(
    user_id: int = Depends(get_current_user_id),
    limit: int = 12,
    db: Session = Depends(get_db)
):
    """获取月经记录历史"""
    records = db.query(MenstrualRecord).filter(
        MenstrualRecord.user_id == user_id
    ).order_by(MenstrualRecord.start_date.desc()).limit(limit).all()

    for record in records:
        _prepare_record_response(record)

    return records


@router.get("/predict")
async def predict_next_period(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    预测下次经期时间
    触发条件：用户完成至少两个完整周期记录后自动激活
    """
    predictor = CyclePredictor(db)

    try:
        result = predictor.predict(user_id)

        return {
            "predicted_start": result["predicted_start"],
            "confidence": result["confidence"],
            "error_range": result["error_range"],
            "next_period_date": result["predicted_start"],
            "current_phase": result["current_phase"],
            "phase_days_remaining": result["phase_days_remaining"],
            "status": "success"
        }
    except ValueError as e:
        return {
            "predicted_start": None,
            "confidence": 0,
            "error_range": 0,
            "next_period_date": None,
            "current_phase": "unknown",
            "phase_days_remaining": None,
            "status": "no_data",
            "message": str(e)
        }


@router.put("/record/{record_id}", response_model=MenstrualRecordResponse)
async def update_menstrual_record(
    record_id: int,
    record: MenstrualRecordCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """更新月经记录（补录结束日期等）"""
    existing = db.query(MenstrualRecord).filter(
        MenstrualRecord.id == record_id,
        MenstrualRecord.user_id == user_id,
    ).first()

    if not existing:
        raise HTTPException(status_code=404, detail="记录不存在")

    # Update fields
    existing.start_date = record.start_date
    existing.end_date = record.end_date
    existing.flow_intensity = record.flow_intensity
    existing.symptoms = json.dumps(record.symptoms) if record.symptoms else None
    existing.notes = record.notes

    if record.end_date:
        existing.duration = (record.end_date - record.start_date).days
    else:
        existing.duration = None

    db.commit()
    db.refresh(existing)

    # Recalculate prediction
    predictor = CyclePredictor(db)
    predictor.update_prediction(user_id)

    return _prepare_record_response(existing)


@router.delete("/record/{record_id}")
async def delete_menstrual_record(
    record_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """删除月经记录"""
    record = db.query(MenstrualRecord).filter(
        MenstrualRecord.id == record_id,
        MenstrualRecord.user_id == user_id,
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    db.delete(record)
    db.commit()

    return {"status": "success", "msg": "记录已删除"}
