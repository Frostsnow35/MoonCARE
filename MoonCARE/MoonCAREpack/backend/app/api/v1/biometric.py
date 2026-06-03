from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import random
import json

from app.database import get_db
from app.models.biometric import BiometricData
from app.schemas.biometric import BiometricUpload, BiometricResponse, BiometricDataPoint
from app.services.emotion_engine import EmotionEngine
from app.api.v1.deps import get_current_user_id

router = APIRouter(prefix="/biometric", tags=["生理数据"])


class RawBiometricUpload(BaseModel):
    """原始硬件数据格式 - 允许部分字段缺失"""
    temp: Optional[float] = None
    bpm: Optional[float] = None
    motion: Optional[str] = None
    wearing: Optional[bool] = None
    cerebral_blood_flow: Optional[float] = None  # 脑血流量


@router.post("/upload", response_model=BiometricResponse)
async def upload_biometric_data(
    data: BiometricUpload,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    上传生理数据（温度、心率、运动状态）
    触发条件：耳挂设备采集到数据后上传
    前置条件：蓝牙连接成功
    注意：只有 confidence == "HIGH" 时才写入数据库
    """
    try:
        # Check confidence - if LOW, skip writing to database
        confidence = (data.confidence or "HIGH").upper()
        if confidence == "LOW":
            return BiometricResponse(
                status="skipped",
                msg="Confidence LOW, not stored",
                data_id=None
            )

        # Use current time if timestamp not provided by hardware
        timestamp = data.timestamp or datetime.now()

        # Create biometric record
        biometric = BiometricData(
            user_id=user_id,
            device_id=data.device_id,
            timestamp=timestamp,
            hrv=data.bpm,  # hardware bpm -> stored as hrv
            skin_temperature=data.temp,
            motion=data.motion,
            cerebral_blood_flow=data.cerebral_blood_flow,  # 脑血流量
            is_valid=1
        )

        db.add(biometric)
        db.commit()
        db.refresh(biometric)

        return BiometricResponse(
            status="success",
            msg="Data received",
            data_id=biometric.id
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query", response_model=List[BiometricDataPoint])
async def query_biometric_data(
    user_id: int = Depends(get_current_user_id),
    start_date: datetime = None,
    end_date: datetime = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """查询用户的生理数据历史"""
    query = db.query(BiometricData).filter(BiometricData.user_id == user_id)

    if start_date:
        query = query.filter(BiometricData.timestamp >= start_date)
    if end_date:
        query = query.filter(BiometricData.timestamp <= end_date)

    query = query.order_by(BiometricData.timestamp.desc()).limit(limit)

    return query.all()


@router.get("/latest")
async def get_latest_biometric(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """获取最新一条生理数据"""
    latest = db.query(BiometricData).filter(
        BiometricData.user_id == user_id
    ).order_by(BiometricData.timestamp.desc()).first()

    if not latest:
        return None

    return {
        "timestamp": latest.timestamp,
        "hrv": latest.hrv,
        "skin_temperature": latest.skin_temperature,
        "motion": latest.motion,
        "cerebral_blood_flow": latest.cerebral_blood_flow
    }


@router.post("/seed")
async def seed_mock_data(
    user_id: int = Depends(get_current_user_id),
    count: int = 50,
    db: Session = Depends(get_db)
):
    """
    生成模拟生理数据用于测试
    生成指定数量的模拟数据点，时间间隔均匀分布
    """
    now = datetime.now()
    motions = ["LOW", "MEDIUM", "HIGH"]

    for i in range(count):
        # 模拟数据，略带随机波动
        biometric = BiometricData(
            user_id=user_id,
            device_id="MOCK_DEVICE",
            timestamp=now - timedelta(seconds=count - i),
            hrv=random.uniform(60, 90),  # 心率 60-90 BPM
            skin_temperature=random.uniform(35.5, 37.0),  # 体温 35.5-37.0°C
            cerebral_blood_flow=random.uniform(45, 60),  # 脑血流量 45-60 mL/100g/min
            motion=random.choice(motions),
            is_valid=1
        )
        db.add(biometric)

    db.commit()

    return {
        "status": "success",
        "msg": f"已生成 {count} 条模拟数据",
        "count": count
    }


@router.post("/raw")
async def upload_raw_biometric_data(
    data: RawBiometricUpload,
    user_id: int = Depends(get_current_user_id),
    device_id: str = "DEVICE_001",
    db: Session = Depends(get_db)
):
    """
    接收原始硬件数据（通过USB/蓝牙网关转发）
    硬件数据格式: {"temp":24.2,"bpm":94.5,"motion":"LOW","wearing":false}
    """
    try:
        biometric = BiometricData(
            user_id=user_id,
            device_id=device_id,
            timestamp=datetime.now(),
            hrv=data.bpm,
            skin_temperature=data.temp,
            motion=data.motion,
            cerebral_blood_flow=data.cerebral_blood_flow,
            is_valid=1
        )

        db.add(biometric)
        db.commit()
        db.refresh(biometric)

        return {
            "status": "success",
            "data_id": biometric.id
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "msg": str(e)
        }


# ==================== 脑血流量相关API预留接口 ====================

class CerebralBloodFlowUpload(BaseModel):
    """脑血流量数据上传格式"""
    device_id: Optional[str] = "DEVICE_001"
    timestamp: Optional[datetime] = None
    cbf_value: float  # 脑血流量值 mL/100g/min
    measurement_mode: Optional[str] = "NIRS"  # 测量方式: NIRS, TCD, MRI等
    quality_score: Optional[float] = None  # 数据质量评分 0-1


@router.post("/cerebral-blood-flow/upload")
async def upload_cerebral_blood_flow(
    data: CerebralBloodFlowUpload,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    [预留接口] 上传脑血流量数据
    用于专部门的脑血流测量设备数据上传
    """
    try:
        timestamp = data.timestamp or datetime.now()
        
        # 同时更新到biometric_data表的cerebral_blood_flow字段
        biometric = BiometricData(
            user_id=user_id,
            device_id=data.device_id,
            timestamp=timestamp,
            cerebral_blood_flow=data.cbf_value,
            is_valid=1
        )
        
        db.add(biometric)
        db.commit()
        db.refresh(biometric)
        
        return {
            "status": "success",
            "msg": "Cerebral blood flow data uploaded",
            "data_id": biometric.id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cerebral-blood-flow/history")
async def get_cbf_history(
    user_id: int = Depends(get_current_user_id),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    [预留接口] 获取脑血流量历史数据
    返回指定时间范围内的脑血流量测量记录
    """
    query = db.query(BiometricData).filter(
        BiometricData.user_id == user_id,
        BiometricData.cerebral_blood_flow.isnot(None)
    )
    
    if start_date:
        query = query.filter(BiometricData.timestamp >= start_date)
    if end_date:
        query = query.filter(BiometricData.timestamp <= end_date)
    
    results = query.order_by(BiometricData.timestamp.desc()).limit(limit).all()
    
    return [
        {
            "timestamp": r.timestamp,
            "cerebral_blood_flow": r.cerebral_blood_flow,
            "device_id": r.device_id
        }
        for r in results
    ]


@router.get("/cerebral-blood-flow/average")
async def get_cbf_average(
    user_id: int = Depends(get_current_user_id),
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """
    [预留接口] 获取指定时间窗口内的平均脑血流量
    用于趋势分析和健康评估
    """
    from sqlalchemy import func
    
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    avg_cbf = db.query(func.avg(BiometricData.cerebral_blood_flow)).filter(
        BiometricData.user_id == user_id,
        BiometricData.timestamp >= cutoff_time,
        BiometricData.cerebral_blood_flow.isnot(None)
    ).scalar()
    
    return {
        "user_id": user_id,
        "time_window_hours": hours,
        "average_cbf": round(avg_cbf, 2) if avg_cbf else None,
        "normal_range_min": 45,
        "normal_range_max": 60
    }
