"""
情绪分析引擎 (F-004)
综合分析生理信号、用户输入与AI对话结果
输出: phase, pms_risk, mood_level
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import json

from app.models.biometric import BiometricData
from app.models.assessment import AssessmentObservation
from app.models.conversation import Conversation
from app.models.mood import MoodDiary
from app.models.menstrual import MenstrualRecord
from app.config import settings


class EmotionEngine:
    def __init__(self, db: Session):
        self.db = db
        self.high_risk_threshold = settings.PMS_RISK_HIGH_THRESHOLD

    async def analyze(self, user_id: int, days: int = 7) -> Dict:
        """
        综合分析情绪状态
        输入维度:
        - 过去72小时HRV均值
        - 皮肤温度变化斜率
        - 情绪日记关键词密度
        - AI对话负向情绪占比
        """
        # Get data within analysis window
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 1. Calculate HRV metrics (last 72 hours)
        hrv_data = self._get_hrv_metrics(user_id, end_date - timedelta(hours=72), end_date)

        # 2. Calculate skin temperature trend
        temp_trend = self._get_temperature_trend(user_id, end_date - timedelta(hours=72), end_date)

        # 3. Get mood diary keywords density
        keyword_density = self._get_keyword_density(user_id, start_date, end_date)

        # 4. Calculate negative emotion ratio from conversations
        negative_ratio = self._get_negative_emotion_ratio(user_id, start_date, end_date)

        # 4b. Calculate hidden premenstrual assessment signal
        assessment_signal = self._get_assessment_signal_score(user_id, start_date, end_date)

        # 5. Determine current phase
        phase = self._determine_phase(user_id)

        # 6. Calculate PMS risk
        pms_risk = self._calculate_pms_risk(
            hrv_data, temp_trend, keyword_density, negative_ratio
        )
        pms_risk = min(1.0, pms_risk + assessment_signal * 0.20)

        # 7. Calculate mood level (1-10)
        mood_level = self._calculate_mood_level(keyword_density, negative_ratio, hrv_data)

        # 8. Calculate confidence
        confidence = self._calculate_confidence(hrv_data, keyword_density)
        if assessment_signal > 0:
            confidence = min(1.0, confidence + 0.1)

        return {
            "phase": phase,
            "pms_risk": round(pms_risk, 2),
            "mood_level": round(mood_level, 1),
            "confidence": round(confidence, 2),
            "updated_at": datetime.now()
        }

    def _get_hrv_metrics(self, user_id: int, start, end) -> Dict:
        """获取HRV指标"""
        data = self.db.query(BiometricData).filter(
            BiometricData.user_id == user_id,
            BiometricData.timestamp >= start,
            BiometricData.timestamp <= end,
            BiometricData.is_valid == 1
        ).order_by(BiometricData.timestamp).all()

        if not data:
            return {"mean": None, "trend": None, "sample_count": 0}

        hrv_values = [d.hrv for d in data if d.hrv is not None]

        if not hrv_values:
            return {"mean": None, "trend": None, "sample_count": len(data)}

        mean_hrv = sum(hrv_values) / len(hrv_values)

        # Calculate trend (simple linear)
        if len(hrv_values) > 1:
            # Positive trend means improving (higher HRV = lower stress)
            trend = (hrv_values[-1] - hrv_values[0]) / len(hrv_values)
        else:
            trend = 0

        return {
            "mean": mean_hrv,
            "trend": trend,
            "sample_count": len(data)
        }

    def _get_temperature_trend(self, user_id: int, start, end) -> float:
        """获取皮肤温度变化斜率"""
        data = self.db.query(BiometricData).filter(
            BiometricData.user_id == user_id,
            BiometricData.timestamp >= start,
            BiometricData.timestamp <= end,
            BiometricData.is_valid == 1
        ).order_by(BiometricData.timestamp).all()

        temp_values = [d.skin_temperature for d in data if d.skin_temperature is not None]

        if len(temp_values) < 2:
            return 0.0

        # Normal body temp is ~36.5°C, elevated temp can indicate stress/inflammation
        # Positive slope indicates rising temperature
        n = len(temp_values)
        # Simple trend calculation
        trend = (temp_values[-1] - temp_values[0]) / n

        return round(trend, 3)

    def _get_keyword_density(self, user_id: int, start, end) -> float:
        """获取情绪日记关键词密度"""
        diaries = self.db.query(MoodDiary).filter(
            MoodDiary.user_id == user_id,
            MoodDiary.date >= start,
            MoodDiary.date <= end
        ).all()

        if not diaries:
            return 0.0

        negative_keywords = [
            "烦躁", "焦虑", "低落", "失眠", "头痛", "疲劳", "易怒",
            "沮丧", "紧张", "不安", "压力大", "不开心", "郁闷",
            "anxious", "stressed", "sad", "angry", "tired"
        ]

        total_negative = 0
        total_words = 0

        for diary in diaries:
            if diary.keywords:
                keywords = json.loads(diary.keywords) if isinstance(diary.keywords, str) else diary.keywords
                total_negative += sum(1 for k in keywords if k in negative_keywords)
                total_words += len(keywords)
            elif diary.processed_text:
                text = diary.processed_text.lower()
                total_words += len(text.split())
                for kw in negative_keywords:
                    total_negative += text.count(kw.lower())

        if total_words == 0:
            return 0.0

        return total_negative / total_words

    def _get_negative_emotion_ratio(self, user_id: int, start, end) -> float:
        """获取对话中负向情绪占比"""
        query = self.db.query(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.role == "user",
            Conversation.sentiment_score.isnot(None),
        )
        if start is not None:
            query = query.filter(Conversation.created_at >= start)
        if end is not None:
            query = query.filter(Conversation.created_at <= end)

        conversations = query.all()
        if not conversations:
            return 0.0

        negative_count = sum(1 for item in conversations if (item.sentiment_score or 0.0) < -0.2)
        return negative_count / len(conversations)

    def _get_assessment_signal_score(self, user_id: int, start, end) -> float:
        """Aggregate hidden assessment observations into a conservative 0-1 signal."""
        query = self.db.query(AssessmentObservation).join(AssessmentObservation.assessment_session).filter(
            AssessmentObservation.assessment_session.has(user_id=user_id),
            AssessmentObservation.crisis_signal == False,  # noqa: E712
        )
        if start is not None:
            query = query.filter(AssessmentObservation.created_at >= start)
        if end is not None:
            query = query.filter(AssessmentObservation.created_at <= end)

        observations = query.all()
        if not observations:
            return 0.0

        values = []
        for observation in observations:
            signal = observation.value or {}
            numeric_scores = [
                value
                for key, value in signal.items()
                if key not in {"self_harm", "suicidal_ideation", "confidence"} and isinstance(value, int)
            ]
            if numeric_scores:
                values.append(min(1.0, sum(numeric_scores) / (len(numeric_scores) * 3)))

        if not values:
            return 0.0
        return sum(values) / len(values)

    def _determine_phase(self, user_id: int) -> str:
        """确定当前所处周期阶段"""
        # Get latest menstrual record
        latest = self.db.query(MenstrualRecord).filter(
            MenstrualRecord.user_id == user_id
        ).order_by(MenstrualRecord.start_date.desc()).first()

        if not latest or not latest.start_date:
            return "unknown"

        # Calculate days since start of current cycle
        days_since_start = (datetime.now().date() - latest.start_date).days

        if latest.end_date and datetime.now().date() <= latest.end_date:
            return "menstrual"
        elif days_since_start < 0:
            return "unknown"
        elif days_since_start <= 7:
            return "follicular"  # 卵泡期
        elif days_since_start <= 14:
            return "ovulation"  # 排卵期
        elif days_since_start <= 28:
            return "luteal"  # 黄体期
        else:
            # Could be next cycle starting
            return "luteal"

    def _calculate_pms_risk(
        self,
        hrv_data: Dict,
        temp_trend: float,
        keyword_density: float,
        negative_ratio: float
    ) -> float:
        """
        计算PMS风险值 (0.0 - 1.0)
        风险值 >= 0.7 判定为高风险
        """
        risk_score = 0.5  # Base risk

        # HRV contribution (lower HRV = higher risk)
        if hrv_data["mean"]:
            # Normal HRV is 50-100ms, lower suggests stress
            if hrv_data["mean"] < 30:
                risk_score += 0.2
            elif hrv_data["mean"] < 50:
                risk_score += 0.1
            elif hrv_data["mean"] > 70:
                risk_score -= 0.1

            # Negative trend increases risk
            if hrv_data["trend"] and hrv_data["trend"] < -5:
                risk_score += 0.15

        # Temperature trend (rising temp = higher risk)
        if temp_trend > 0.5:
            risk_score += 0.15
        elif temp_trend > 0.2:
            risk_score += 0.1

        # Keyword density
        risk_score += min(keyword_density * 0.3, 0.2)

        # Negative emotion ratio
        risk_score += negative_ratio * 0.15

        # Clamp to 0-1 range
        return max(0.0, min(1.0, risk_score))

    def _calculate_mood_level(
        self,
        keyword_density: float,
        negative_ratio: float,
        hrv_data: Dict
    ) -> float:
        """
        计算情绪等级 (1-10)
        1 = 非常低落, 10 = 非常愉悦
        """
        mood = 5.0  # Baseline

        # HRV contribution (higher HRV = better mood)
        if hrv_data["mean"]:
            if hrv_data["mean"] > 70:
                mood += 1.5
            elif hrv_data["mean"] > 50:
                mood += 0.5
            elif hrv_data["mean"] < 30:
                mood -= 1.5

        # Keyword density (negative keywords = lower mood)
        mood -= keyword_density * 3

        # Negative emotion ratio
        mood -= negative_ratio * 2

        return max(1.0, min(10.0, mood))

    def _calculate_confidence(
        self,
        hrv_data: Dict,
        keyword_density: float
    ) -> float:
        """
        计算分析结果置信度
        数据越完整，置信度越高
        """
        confidence = 0.5  # Base confidence

        # More HRV samples = higher confidence
        if hrv_data["sample_count"] > 100:
            confidence += 0.2
        elif hrv_data["sample_count"] > 50:
            confidence += 0.15
        elif hrv_data["sample_count"] > 10:
            confidence += 0.1

        # Have mood diary data
        if keyword_density > 0:
            confidence += 0.15

        # Both data sources present
        if hrv_data["mean"] and keyword_density > 0:
            confidence += 0.1

        return max(0.0, min(1.0, confidence))

    def get_current_phase(self, user_id: int) -> str:
        """获取当前周期阶段"""
        return self._determine_phase(user_id)

    def get_intervention_recommendations(self, user_id: int, context: str) -> List[str]:
        """
        根据情境获取干预建议
        返回推荐列表
        """
        recommendations = []

        # Get current PMS risk
        result = self.db.query(MenstrualRecord).filter(
            MenstrualRecord.user_id == user_id
        ).first()

        phase = self._determine_phase(user_id)

        # Base recommendations by phase
        if phase == "luteal":
            recommendations.extend(["breathing_exercise", "hot_compress"])

        if context in ["mood_low", "stress", "anxiety"]:
            recommendations.extend(["breathing_exercise", "music_therapy"])

        if context in ["stress", "anxiety"]:
            recommendations.append("walking")

        # Remove duplicates and limit
        seen = set()
        unique_recs = []
        for r in recommendations:
            if r not in seen:
                seen.add(r)
                unique_recs.append(r)

        return unique_recs[:4]  # Max 4 recommendations
