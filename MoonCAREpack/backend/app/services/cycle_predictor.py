"""
周期预测服务 (F-013)
基于历史数据与AI模型推算下次经期时间
使用加权移动平均法
"""

from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import Dict, Optional, List
from collections import defaultdict

from app.models.menstrual import MenstrualRecord
from app.config import settings


class CyclePredictor:
    """
    周期预测器
    使用加权移动平均法，近期周期权重更高
    """

    def __init__(self, db: Session):
        self.db = db
        self.min_history = settings.CYCLE_PREDICTION_MIN_HISTORY
        self.error_range = settings.CYCLE_PREDICTION_ERROR_RANGE

    def predict(self, user_id: int) -> Dict:
        """
        预测下次月经开始日期
        触发条件：用户完成至少两个完整周期记录后
        """
        records = self.db.query(MenstrualRecord).filter(
            MenstrualRecord.user_id == user_id,
            MenstrualRecord.start_date.isnot(None)
        ).order_by(MenstrualRecord.start_date.desc()).all()

        if len(records) < self.min_history:
            raise ValueError(
                f"需要至少{self.min_history}个周期记录才能进行预测，当前有{len(records)}个记录"
            )

        # Calculate cycle lengths
        cycle_lengths = self._calculate_cycle_lengths(records)

        # Calculate weighted average
        predicted_length = self._weighted_average(cycle_lengths)

        # Determine current phase
        current_phase, phase_days_remaining = self._determine_current_phase(
            records[0].start_date, predicted_length
        )

        # Calculate predicted start date
        last_start = records[0].start_date
        predicted_start = last_start + timedelta(days=int(predicted_length))

        # Calculate confidence based on variance
        confidence = self._calculate_confidence(cycle_lengths, predicted_length)

        return {
            "predicted_start": predicted_start,
            "predicted_length": round(predicted_length, 1),
            "confidence": round(confidence, 2),
            "error_range": self.error_range,
            "current_phase": current_phase,
            "phase_days_remaining": phase_days_remaining
        }

    def update_prediction(self, user_id: int):
        """
        更新预测结果
        当用户添加新记录后自动调用
        """
        try:
            result = self.predict(user_id)

            # Update the most recent record with prediction
            latest = self.db.query(MenstrualRecord).filter(
                MenstrualRecord.user_id == user_id
            ).order_by(MenstrualRecord.start_date.desc()).first()

            if latest:
                latest.predicted_next_start = result["predicted_start"]
                latest.prediction_confidence = result["confidence"]
                self.db.commit()

        except ValueError:
            # Not enough data yet, skip update
            pass

    def _calculate_cycle_lengths(self, records: List) -> List[int]:
        """计算各周期长度"""
        lengths = []

        # Sort by date ascending for calculation
        sorted_records = sorted(records, key=lambda r: r.start_date)

        for i in range(1, len(sorted_records)):
            prev_start = sorted_records[i - 1].start_date
            curr_start = sorted_records[i].start_date
            length = (curr_start - prev_start).days
            if 15 <= length <= 45:  # Sanity check: normal cycle is 21-35 days
                lengths.append(length)

        return lengths

    def _weighted_average(self, cycle_lengths: List[int]) -> float:
        """
        计算加权移动平均
        近期周期权重更高
        """
        if not cycle_lengths:
            return 28.0  # Default average

        n = len(cycle_lengths)
        weights = list(range(1, n + 1))  # [1, 2, 3, ..., n]
        total_weight = sum(weights)

        weighted_sum = sum(length * weight for length, weight in zip(cycle_lengths, weights))

        return weighted_sum / total_weight

    def _calculate_confidence(self, cycle_lengths: List[int], predicted: float) -> float:
        """
        计算预测置信度
        周期规律性越高，置信度越高
        """
        if len(cycle_lengths) < 2:
            return 0.5

        # Calculate variance
        mean = sum(cycle_lengths) / len(cycle_lengths)
        variance = sum((x - mean) ** 2 for x in cycle_lengths) / len(cycle_lengths)

        # Lower variance = higher confidence
        # Normal cycle variance is about 2-7 days²
        if variance <= 4:
            confidence = 0.9
        elif variance <= 9:
            confidence = 0.75
        elif variance <= 16:
            confidence = 0.6
        elif variance <= 25:
            confidence = 0.5
        else:
            confidence = 0.4

        # More history = higher confidence
        if len(cycle_lengths) >= 4:
            confidence += 0.1

        return min(1.0, confidence)

    def _determine_current_phase(
        self,
        last_period_start: date,
        cycle_length: float
    ) -> tuple:
        """
        确定当前所处阶段
        返回: (phase_name, days_remaining_in_phase)
        """
        days_since_start = (date.today() - last_period_start).days
        cycle_day = days_since_start % int(cycle_length) if cycle_length > 0 else 0

        # Phase definitions
        phases = [
            ("menstrual", 0, 5),      # 经期: 开始后0-5天
            ("follicular", 5, 12),    # 卵泡期: 第6-12天
            ("ovulation", 12, 16),     # 排卵期: 第13-16天
            ("luteal", 16, 28)         # 黄体期: 第17-28天
        ]

        for phase_name, start_day, end_day in phases:
            if start_day <= cycle_day < end_day:
                days_remaining = end_day - cycle_day
                return phase_name, days_remaining

        # Default to luteal if something's off
        return "luteal", 28 - cycle_day

    def check_irregularity(self, user_id: int) -> Dict:
        """
        检查周期是否极度不规律
        方差 > 7天² 时提示警告
        """
        records = self.db.query(MenstrualRecord).filter(
            MenstrualRecord.user_id == user_id,
            MenstrualRecord.start_date.isnot(None)
        ).order_by(MenstrualRecord.start_date).all()

        if len(records) < 2:
            return {"is_irregular": False, "variance": 0, "warning": None}

        lengths = self._calculate_cycle_lengths(records)

        if len(lengths) < 2:
            return {"is_irregular": False, "variance": 0, "warning": None}

        mean = sum(lengths) / len(lengths)
        variance = sum((x - mean) ** 2 for x in lengths) / len(lengths)

        warning = None
        if variance > 49:  # 7 days squared
            warning = "您的周期波动较大，预测仅供参考"

        return {
            "is_irregular": variance > 49,
            "variance": round(variance, 2),
            "warning": warning
        }
