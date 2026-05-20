from app.utils.safety import contains_crisis_signal


class PerceptionAgent:
    def __init__(self):
        self.emotion_history = {}

    def analyze(self, message: str, cycle_phase: str = None, sensor_data: dict = None, user_id: int = None) -> dict:
        sensor_data = sensor_data or {}
        text = (message or "").lower()

        risk_level = "low"

        high_keywords = [
            "没有意义", "撑不住了", "想消失", "我真的不行了", "崩溃到不行",
            "活着没意思", "不想活了", "太累了", "受不了了", "绝望", "生不如死",
            "没人在乎", "没人理解", "孤独", "孤单"
        ]
        medium_keywords = [
            "烦躁", "难受", "想哭", "崩溃", "焦虑", "累", "低落", "敏感",
            "郁闷", "压抑", "沮丧", "疲惫", "无助", "紧张", "不安",
            "伤心", "痛苦", "担忧", "害怕", "失落", "委屈"
        ]

        support_context = self._extract_support_context(text, cycle_phase)
        emotion_intensity = self._calculate_emotion_intensity(text)
        dominant_emotion = self._detect_dominant_emotion(text)
        emotion_pattern = self._detect_emotion_pattern(text, user_id)

        if contains_crisis_signal(text):
            risk_level = "crisis"
        elif any(kw in text for kw in high_keywords) or emotion_intensity >= 0.7:
            risk_level = "high"
        elif any(kw in text for kw in medium_keywords) or emotion_intensity >= 0.4:
            risk_level = "medium"

        # 更新情绪历史
        if user_id:
            self._update_emotion_history(user_id, dominant_emotion, emotion_intensity)

        return {
            "risk_level": risk_level,
            "cycle_phase": cycle_phase or "经前期",
            "sensor_data": sensor_data,
            "emotion_summary": message,
            "support_context": support_context,
            "emotion_intensity": emotion_intensity,
            "dominant_emotion": dominant_emotion,
            "emotion_tags": support_context.get("emotion_signals", []),
            "emotion_pattern": emotion_pattern,
            "is_repeating_pattern": emotion_pattern is not None,
        }

    def _update_emotion_history(self, user_id: int, emotion: str, intensity: float):
        """Update emotion history for pattern detection."""
        import time
        if user_id not in self.emotion_history:
            self.emotion_history[user_id] = []
        
        now = time.time()
        self.emotion_history[user_id].append({
            "emotion": emotion,
            "intensity": intensity,
            "timestamp": now
        })
        
        # 保留最近20条记录
        self.emotion_history[user_id] = self.emotion_history[user_id][-20:]

    def _detect_emotion_pattern(self, text: str, user_id: int) -> str:
        """Detect repeating emotion patterns in user history."""
        if not user_id or user_id not in self.emotion_history:
            return None
        
        history = self.emotion_history[user_id]
        if len(history) < 3:
            return None
        
        # 检查最近3条记录是否有重复情绪
        recent_emotions = [h["emotion"] for h in history[-3:]]
        if len(set(recent_emotions)) == 1 and recent_emotions[0] != "neutral":
            return f"repeating_{recent_emotions[0]}"
        
        # 检查高强度情绪重复
        high_intensity_count = sum(1 for h in history[-5:] if h["intensity"] >= 0.6)
        if high_intensity_count >= 3:
            return "persistent_high_intensity"
        
        return None

    def _calculate_emotion_intensity(self, text: str) -> float:
        """Calculate emotion intensity based on keyword frequency and intensifiers."""
        intensifiers = ["很", "非常", "特别", "太", "真的", "极其", "实在"]
        intensifier_count = sum(1 for word in intensifiers if word in text)
        
        emotion_keywords = [
            "烦躁", "难受", "想哭", "崩溃", "焦虑", "累", "低落", "敏感",
            "郁闷", "压抑", "沮丧", "疲惫", "无助", "紧张", "不安",
            "伤心", "痛苦", "绝望", "生气", "愤怒", "担忧", "害怕"
        ]
        emotion_count = sum(1 for word in emotion_keywords if word in text)
        
        base_intensity = min(emotion_count * 0.25, 0.6)
        intensifier_boost = min(intensifier_count * 0.15, 0.3)
        
        return min(base_intensity + intensifier_boost, 1.0)

    def _detect_dominant_emotion(self, text: str) -> str:
        """Detect the dominant emotion from the text."""
        emotion_patterns = {
            "anxious": ["焦虑", "紧张", "不安", "担心", "慌", "忐忑", "忧虑"],
            "sad": ["难过", "低落", "伤心", "沮丧", "想哭", "委屈", "失落"],
            "angry": ["生气", "烦躁", "愤怒", "火大", "恼火", "易怒"],
            "tired": ["累", "疲惫", "困倦", "乏力", "没精神"],
            "helpless": ["无助", "绝望", "不知道怎么办", "撑不住"],
            "happy": ["开心", "高兴", "快乐", "幸福", "喜悦", "满足"],
        }
        
        max_count = 0
        dominant = "neutral"
        
        for emotion, keywords in emotion_patterns.items():
            count = sum(1 for kw in keywords if kw in text)
            if count > max_count:
                max_count = count
                dominant = emotion
        
        return dominant

    def _extract_support_context(self, text: str, cycle_phase: str = None) -> dict:
        """Extract lightweight menstrual/body-emotion signals for support tone."""
        body_signal_keywords = {
            "pain": ["肚子痛", "腹痛", "痛经", "绞痛", "疼", "痛", "腰酸", "头痛", "胃疼"],
            "bloating": ["腹胀", "胀", "水肿", "乳房胀痛", "腹部胀气"],
            "fatigue": ["累", "疲惫", "乏力", "没精神", "困", "疲倦"],
            "sleep_change": ["睡不好", "失眠", "睡不着", "嗜睡", "睡眠不好"],
            "appetite": ["想吃", "没胃口", "暴食", "食欲", "吃不下"],
            "headache": ["头痛", "头晕", "偏头痛"],
            "muscle_ache": ["腰酸", "背痛", "肌肉酸痛"],
        }
        emotion_signal_keywords = {
            "sad": ["难过", "低落", "伤心", "沮丧", "想哭", "委屈", "失落"],
            "tearful": ["想哭", "容易哭", "流泪", "眼泪"],
            "irritable": ["烦躁", "易怒", "火大", "生气", "恼火"],
            "anxious": ["焦虑", "紧张", "慌", "不安", "担心", "忧虑"],
            "helpless": ["无助", "撑不住", "不知道怎么办", "绝望"],
            "stressed": ["压力大", "有压力", "紧张", "焦虑"],
            "lonely": ["孤单", "孤独", "没人理解"],
            "hopeless": ["绝望", "没希望", "没办法"],
        }
        menstrual_keywords = [
            "经前", "月经前", "姨妈前", "经期", "月经", "例假", "姨妈", "来大姨妈",
            "黄体期", "pms", "pmdd", "生理期", "排卵期",
        ]
        menstrual_phases = {"经前期", "黄体期", "luteal", "menstrual", "经期", "月经期"}

        body_signals = self._matched_signal_names(text, body_signal_keywords)
        emotion_signals = self._matched_signal_names(text, emotion_signal_keywords)
        menstrual_related = (
            any(keyword in text for keyword in menstrual_keywords)
            or bool(body_signals)
            or (cycle_phase in menstrual_phases)
        )

        return {
            "menstrual_related": menstrual_related,
            "body_signals": body_signals,
            "emotion_signals": emotion_signals,
        }

    def _matched_signal_names(self, text: str, signal_keywords: dict) -> list[str]:
        """Return signal names whose keyword set appears in text."""
        return [
            signal
            for signal, keywords in signal_keywords.items()
            if any(keyword in text for keyword in keywords)
        ]
