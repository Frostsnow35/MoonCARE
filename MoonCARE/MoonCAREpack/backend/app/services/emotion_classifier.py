"""
情绪分类服务 v2.0
基于生理信号的实时情绪分类

算法依据:
1. 心率(HR)与情绪的关系 - 愤怒/焦虑时心率升高
2. 皮肤温度与压力的关系 - 紧张时外周血管收缩导致手脚冰凉
3. 运动状态与情绪的交互 - 静止时的心率更能反映情绪状态

文献参考:
- Kreibig, S. D. (2010). Autonomic nervous system activity in emotion
- Kim, J. et al. (2018). WESAD: Wearable Stress and Affect Detection
- Picard, R. W. (1997). Affective Computing
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime
import math


@dataclass
class EmotionScores:
    """情绪得分"""
    depression: float = 20.0   # 抑郁/低落
    anxiety: float = 20.0       # 焦虑/紧张
    anger: float = 15.0       # 愤怒/烦躁
    calm: float = 45.0         # 平静/放松

    def get_dominant(self) -> str:
        emotions = {
            "depression": self.depression,
            "anxiety": self.anxiety,
            "anger": self.anger,
            "calm": self.calm
        }
        return max(emotions, key=emotions.get)

    def get_dominant_cn(self) -> str:
        mapping = {
            "depression": "抑郁",
            "anxiety": "焦虑",
            "anger": "愤怒",
            "calm": "平静"
        }
        return mapping[self.get_dominant()]

    def to_dict(self) -> dict:
        return {
            "depression": round(self.depression, 1),
            "anxiety": round(self.anxiety, 1),
            "anger": round(self.anger, 1),
            "calm": round(self.calm, 1),
            "dominant": self.get_dominant_cn()
        }


@dataclass
class HRVFeatures:
    """提取的HRV特征"""
    heart_rate: float = 0.0          # 心率 (bpm)
    hrv_index: float = 0.0          # HRV指数 (如果直接测量)
    rmssd: float = 0.0              # RMSSD (ms)
    sdnn: float = 0.0               # SDNN (ms)
    pnn50: float = 0.0              # pNN50 (%)
    lf_hf_ratio: float = 0.0        # LF/HF比值


class EmotionClassifier:
    """
    基于生理信号的实时情绪分类器 v2.0

    心率参考范围 (bpm):
    - 睡眠: 40-60
    - 平静: 60-75
    - 正常活动: 75-100
    - 轻度活动: 100-120
    - 剧烈活动: 120+

    HRV指数参考:
    - 极高 (>100): 极度放松/冥想状态
    - 高 (60-100): 放松
    - 正常 (30-60): 日常状态
    - 低 (15-30): 轻度压力
    - 极低 (<15): 高度紧张/压力

    皮肤温度参考:
    - 低温 (<34°C): 高度紧张/焦虑 (外周血管收缩)
    - 偏低 (34-35.5°C): 轻度紧张
    - 正常 (35.5-36.5°C): 平静
    - 温暖 (>36.5°C): 放松
    """

    # 心率分区阈值
    HR_RESTING = 60
    HR_NORMAL = 75
    HR_ELEVATED = 90
    HR_HIGH = 110

    # HRV指数阈值
    HRV_VERY_LOW = 15
    HRV_LOW = 30
    HRV_NORMAL = 60
    HRV_HIGH = 100

    # 温度阈值
    TEMP_COLD = 34.0
    TEMP_LOW = 35.5
    TEMP_NORMAL = 36.5

    # 运动权重
    MOTION_EFFECTS = {
        "LOW": {
            "calm_weight": 1.2,    # 静止时心率更能反映情绪
            "anxiety_amplifier": 1.0,
            "anger_amplifier": 1.0
        },
        "MEDIUM": {
            "calm_weight": 0.7,
            "anxiety_amplifier": 1.3,
            "anger_amplifier": 1.5
        },
        "HIGH": {
            "calm_weight": 0.3,
            "anxiety_amplifier": 1.5,
            "anger_amplifier": 2.0
        }
    }

    def classify(
        self,
        heart_rate: Optional[float] = None,
        hrv_index: Optional[float] = None,
        skin_temperature: Optional[float] = None,
        motion: str = "LOW"
    ) -> EmotionScores:
        """
        根据生理数据分类情绪

        Args:
            heart_rate: 心率 (bpm)
            hrv_index: HRV指数 (如果设备直接测量)
            skin_temperature: 皮肤温度 (°C)
            motion: 运动状态 ("LOW", "MEDIUM", "HIGH")

        Returns:
            EmotionScores: 各情绪状态的得分 (0-100)
        """
        scores = EmotionScores()

        # 获取运动相关的权重调整
        motion_weights = self.MOTION_EFFECTS.get(motion, self.MOTION_EFFECTS["LOW"])

        # 1. 基于心率计算基础情绪分数
        if heart_rate and heart_rate > 0:
            self._apply_heart_rate(scores, heart_rate, motion_weights)

        # 2. 基于HRV指数调整
        if hrv_index and hrv_index > 0:
            self._apply_hrv_index(scores, hrv_index, motion_weights)

        # 3. 基于皮肤温度调整
        if skin_temperature and skin_temperature > 0:
            self._apply_temperature(scores, skin_temperature)

        # 4. 基于运动状态调整
        self._apply_motion(scores, motion)

        # 5. 归一化
        self._normalize(scores)

        return scores

    def _apply_heart_rate(
        self,
        scores: EmotionScores,
        hr: float,
        weights: Dict
    ):
        """应用心率数据"""
        # 心率基础分
        base_calm = 50.0

        if hr < self.HR_RESTING:
            # 低于静息心率 → 极度平静/放松
            cal_adjust = min((self.HR_RESTING - hr) * 2, 25)
            scores.calm += cal_adjust
            scores.anxiety -= 5
            scores.anger -= 10

        elif hr < self.HR_NORMAL:
            # 正常偏低的静息心率 → 平静
            scores.calm += 10 * weights["calm_weight"]
            scores.anxiety -= 5
            scores.anger -= 5

        elif hr < self.HR_ELEVATED:
            # 正常偏开心率 → 轻微紧张/兴奋
            excess = hr - self.HR_NORMAL
            anxiety_inc = min(excess * 1.5, 20) * weights["anxiety_amplifier"]
            scores.anxiety += anxiety_inc
            scores.calm -= 5
            scores.anger += 5

        elif hr < self.HR_HIGH:
            # 高心率 → 焦虑/紧张
            excess = hr - self.HR_ELEVATED
            anxiety_inc = min(excess * 2.5, 30) * weights["anxiety_amplifier"]
            anger_inc = min(excess * 1.5, 20) * weights["anger_amplifier"]
            scores.anxiety += anxiety_inc
            scores.anger += anger_inc
            scores.calm -= 15

        else:
            # 极高心率 → 高度紧张/愤怒/恐惧
            scores.anxiety += 35 * weights["anxiety_amplifier"]
            scores.anger += 30 * weights["anger_amplifier"]
            scores.calm -= 30
            scores.depression += 10

    def _apply_hrv_index(
        self,
        scores: EmotionScores,
        hrv: float,
        weights: Dict
    ):
        """应用HRV指数数据"""
        if hrv >= self.HRV_VERY_LOW:
            # 极低HRV → 高度压力状态
            scores.anxiety += 25 * weights["anxiety_amplifier"]
            scores.anger += 15 * weights["anger_amplifier"]
            scores.calm -= 25
            scores.depression += 10

        elif hrv >= self.HRV_LOW:
            # 低HRV → 轻度压力
            scores.anxiety += 12 * weights["anxiety_amplifier"]
            scores.calm -= 10
            scores.anger += 5

        elif hrv >= self.HRV_NORMAL:
            # 正常HRV → 平静
            scores.calm += 20 * weights["calm_weight"]
            scores.anxiety -= 5
            scores.depression -= 5

        else:
            # 高HRV → 极度放松
            scores.calm += 30 * weights["calm_weight"]
            scores.anxiety -= 15
            scores.anger -= 15
            scores.depression -= 10

    def _apply_temperature(
        self,
        scores: EmotionScores,
        temp: float
    ):
        """应用皮肤温度数据"""
        if temp < self.TEMP_COLD:
            # 低温 → 高度紧张 (外周血管收缩)
            scores.anxiety += 20
            scores.calm -= 20
            scores.anger += 5

        elif temp < self.TEMP_LOW:
            # 偏低 → 轻度紧张
            scores.anxiety += 10
            scores.calm -= 10

        elif temp >= self.TEMP_NORMAL:
            # 正常或温暖 → 放松
            warm_bonus = min((temp - self.TEMP_NORMAL) * 3, 15)
            scores.calm += warm_bonus
            scores.anxiety -= 10

    def _apply_motion(
        self,
        scores: EmotionScores,
        motion: str
    ):
        """应用运动状态"""
        if motion == "HIGH":
            # 高运动状态
            # 心率可能受运动影响，不完全反映情绪
            scores.anger += 10
            scores.anxiety += 5

        elif motion == "LOW":
            # 静止状态 → 心率更能反映情绪
            scores.calm += 5

    def _normalize(self, scores: EmotionScores):
        """归一化分数到0-100范围"""
        # 确保最小值为0
        scores.depression = max(0, scores.depression)
        scores.anxiety = max(0, scores.anxiety)
        scores.anger = max(0, scores.anger)
        scores.calm = max(0, scores.calm)

        # 计算总和
        total = scores.depression + scores.anxiety + scores.anger + scores.calm

        if total > 0:
            # 归一化到100
            factor = 100 / total
            scores.depression *= factor
            scores.anxiety *= factor
            scores.anger *= factor
            scores.calm *= factor

        # 确保主要情绪差异明显
        max_score = max(scores.depression, scores.anxiety, scores.anger, scores.calm)
        min_score = min(scores.depression, scores.anxiety, scores.anger, scores.calm)

        if max_score - min_score < 10:
            # 如果差距太小，强化主要情绪
            dominant = scores.get_dominant()
            adjustment = 15
            if dominant == "calm":
                scores.calm += adjustment
                scores.anxiety -= 5
                scores.anger -= 5
                scores.depression -= 5
            elif dominant == "anxiety":
                scores.anxiety += adjustment
                scores.calm -= 5
            elif dominant == "anger":
                scores.anger += adjustment
                scores.calm -= 5
            elif dominant == "depression":
                scores.depression += adjustment
                scores.calm -= 5

            # 再次归一化
            total = scores.depression + scores.anxiety + scores.anger + scores.calm
            factor = 100 / total
            scores.depression *= factor
            scores.anxiety *= factor
            scores.anger *= factor
            scores.calm *= factor


class HRVAnalyzer:
    """
    HRV特征分析器
    从原始心率数据提取HRV特征
    """

    @staticmethod
    def extract_features(heart_rates: List[float], timestamps: List[datetime] = None) -> HRVFeatures:
        """
        从心率时间序列提取HRV特征

        Args:
            heart_rates: 心率值列表 (bpm)
            timestamps: 对应的时间戳列表

        Returns:
            HRVFeatures: 提取的HRV特征
        """
        features = HRVFeatures()

        if not heart_rates or len(heart_rates) < 2:
            return features

        # 心率统计
        features.heart_rate = sum(heart_rates) / len(heart_rates)

        # 计算RR间期 (ms)
        rr_intervals = [60000.0 / hr if hr > 0 else 0 for hr in heart_rates]

        # RMSSD: 相邻RR间期差值的均方根
        diffs = []
        for i in range(1, len(rr_intervals)):
            diff = rr_intervals[i] - rr_intervals[i-1]
            diffs.append(diff * diff)
        if diffs:
            features.rmssd = math.sqrt(sum(diffs) / len(diffs))
        else:
            features.rmssd = 0

        # SDNN: RR间期标准差 (ms)
        mean_rr = sum(rr_intervals) / len(rr_intervals)
        variance = sum((rr - mean_rr) ** 2 for rr in rr_intervals) / len(rr_intervals)
        features.sdnn = math.sqrt(variance)

        # pNN50: 相邻RR间期差>50ms的比例
        nn50_count = sum(1 for d in diffs if abs(math.sqrt(d)) > 50)
        if len(diffs) > 0:
            features.pnn50 = (nn50_count / len(diffs)) * 100
        else:
            features.pnn50 = 0

        # 估算LF/HF比值 (基于心率变异性)
        if features.rmssd > 0:
            # 简化估算: LF/HF ≈ 1/HRV指数
            features.lf_hf_ratio = features.sdnn / features.rmssd if features.rmssd > 0 else 1.0

        # HRV指数 (基于RMSSD的标准化)
        if features.rmssd >= 100:
            features.hrv_index = 9  # 极高
        elif features.rmssd >= 60:
            features.hrv_index = 7
        elif features.rmssd >= 30:
            features.hrv_index = 5
        elif features.rmssd >= 15:
            features.hrv_index = 3
        else:
            features.hrv_index = 1

        return features


# 全局实例
emotion_classifier = EmotionClassifier()
hrv_analyzer = HRVAnalyzer()


def classify_emotion(
    heart_rate: Optional[float] = None,
    hrv_index: Optional[float] = None,
    skin_temperature: Optional[float] = None,
    motion: str = "LOW"
) -> dict:
    """
    便捷函数：分类情绪

    Args:
        heart_rate: 心率 (bpm)
        hrv_index: HRV指数 (可选)
        skin_temperature: 皮肤温度 (°C)
        motion: 运动状态 ("LOW", "MEDIUM", "HIGH")

    Returns:
        dict: 包含各情绪得分和主要情绪状态
    """
    scores = emotion_classifier.classify(
        heart_rate=heart_rate,
        hrv_index=hrv_index,
        skin_temperature=skin_temperature,
        motion=motion
    )
    return scores.to_dict()


def classify_from_time_series(
    heart_rates: List[float],
    skin_temperature: Optional[float] = None,
    motion: str = "LOW"
) -> dict:
    """
    从心率时间序列分类情绪

    Args:
        heart_rates: 心率值列表 (bpm)
        skin_temperature: 皮肤温度 (°C)
        motion: 运动状态 ("LOW", "MEDIUM", "HIGH")

    Returns:
        dict: 包含HRV特征、各情绪得分和主要情绪状态
    """
    features = hrv_analyzer.extract_features(heart_rates)

    scores = emotion_classifier.classify(
        heart_rate=features.heart_rate,
        hrv_index=features.hrv_index,
        skin_temperature=skin_temperature,
        motion=motion
    )

    return {
        "features": {
            "heart_rate": round(features.heart_rate, 1),
            "hrv_index": round(features.hrv_index, 1),
            "rmssd": round(features.rmssd, 1),
            "sdnn": round(features.sdnn, 1),
            "pnn50": round(features.pnn50, 1),
            "lf_hf_ratio": round(features.lf_hf_ratio, 2)
        },
        "emotion": scores.to_dict()
    }
