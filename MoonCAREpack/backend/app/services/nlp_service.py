"""
NLP服务 (F-003)
自然语言处理情绪分析
"""

from typing import Dict, List
import re


class NLPService:
    """
    NLP服务 - 情绪分析
    支持中文和英文
    """

    # Emotion keywords mapping
    EMOTION_KEYWORDS = {
        "anxious": ["焦虑", "紧张", "不安", "担心", "害怕", "慌张", "anxious", "worried", "nervous", "afraid"],
        "sad": ["低落", "沮丧", "伤心", "难过", "抑郁", "sad", "depressed", "unhappy", "down"],
        "angry": ["愤怒", "生气", "易怒", "烦躁", "恼火", "angry", "irritated", "frustrated", "annoyed"],
        "happy": ["开心", "高兴", "快乐", "愉悦", "愉快", "happy", "joyful", "pleased", "glad"],
        "calm": ["平静", "宁静", "放松", "舒缓", "安宁", "calm", "relaxed", "peaceful", "serene"],
        "stressed": ["压力", "压力山大", "紧张", "紧绷", "stress", "stressed", "tense"],
        "tired": ["疲劳", "疲惫", "累", "困倦", "疲倦", "tired", "exhausted", "fatigued", "sleepy"],
        "fear": ["恐惧", "害怕", "惊恐", "fear", "scared", "frightened"]
    }

    # PMS related symptoms
    PMS_KEYWORDS = [
        "头痛", "腹胀", "乳房胀痛", "长痘", "食欲改变",
        "失眠", "情绪波动", "焦虑", "疲劳", "注意力不集中",
        "headache", "bloating", "cramps", "acne", "fatigue", "insomnia"
    ]

    # Sensitive keywords that need special handling
    SENSITIVE_KEYWORDS = [
        "不想活了", "想死", "自杀", "自残", "轻生",
        "kill myself", "suicide", "die", "end it all"
    ]

    def __init__(self):
        self.confidence_threshold = 0.6

    async def analyze_text(self, text: str) -> Dict:
        """
        分析文本情绪
        返回:
        - processed_text: 处理后的文本
        - emotion_tags: 情绪标签列表
        - emotion_scores: 各情绪得分
        - mood_level: 情绪等级 (1-10)
        - keywords: 关键词列表
        """
        if not text or not text.strip():
            return {
                "processed_text": "",
                "emotion_tags": ["unknown"],
                "emotion_scores": {},
                "mood_level": 5.0,
                "keywords": [],
                "sentiment_score": 0.0,
                "confidence": 0.0
            }

        text_lower = text.lower()
        words = re.findall(r'[\w]+', text_lower)

        # Find emotion matches
        emotion_matches = {}
        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > 0:
                emotion_matches[emotion] = count

        # Calculate emotion scores (normalize by text length)
        max_possible = max(len(words) / 10, 1)
        emotion_scores = {
            emotion: min(count / max_possible, 1.0)
            for emotion, count in emotion_matches.items()
        }

        # Determine dominant emotion tags
        if emotion_scores:
            threshold = self.confidence_threshold
            emotion_tags = [e for e, s in emotion_scores.items() if s >= threshold]
            if not emotion_tags:
                # Get top emotion if none meet threshold
                top_emotion = max(emotion_scores.items(), key=lambda x: x[1])
                if top_emotion[1] > 0.1:
                    emotion_tags = [top_emotion[0]]
                else:
                    emotion_tags = ["neutral"]
        else:
            emotion_tags = ["neutral"]
            emotion_scores = {"neutral": 0.5}

        # Extract keywords
        keywords = self._extract_keywords(text, words)

        # Calculate mood level (1-10)
        mood_level = self._calculate_mood_level(emotion_scores)

        # Calculate sentiment score (-1 to 1)
        sentiment_score = self._calculate_sentiment(emotion_scores)

        # Calculate confidence
        confidence = self._calculate_confidence(emotion_scores, text)

        return {
            "processed_text": text,  # In production, could do lemmatization, etc.
            "emotion_tags": emotion_tags if emotion_tags else ["neutral"],
            "emotion_scores": emotion_scores,
            "mood_level": round(mood_level, 1),
            "keywords": keywords,
            "sentiment_score": round(sentiment_score, 2),
            "confidence": round(confidence, 2)
        }

    def _extract_keywords(self, text: str, words: List[str]) -> List[str]:
        """提取关键词"""
        text_lower = text.lower()
        keywords = []

        # Check PMS keywords
        for pms_kw in self.PMS_KEYWORDS:
            if pms_kw.lower() in text_lower:
                keywords.append(pms_kw)

        # Add emotion keywords found
        for emotion, emotion_kws in self.EMOTION_KEYWORDS.items():
            for kw in emotion_kws:
                if kw in text_lower and kw not in keywords:
                    keywords.append(kw)

        return keywords[:10]  # Limit to 10 keywords

    def _calculate_mood_level(self, emotion_scores: Dict[str, float]) -> float:
        """
        计算情绪等级 (1-10)
        基于情感得分
        """
        if not emotion_scores:
            return 5.0

        # Weight factors
        positive_emotions = {"happy": 1.0, "calm": 0.7}
        negative_emotions = {"anxious": -0.8, "sad": -0.9, "angry": -0.8, "stressed": -0.6, "tired": -0.5, "fear": -0.9}

        score = 5.0  # Neutral baseline

        for emotion, intensity in emotion_scores.items():
            if emotion in positive_emotions:
                score += positive_emotions[emotion] * intensity * 3
            elif emotion in negative_emotions:
                score += negative_emotions[emotion] * intensity * 3

        return max(1.0, min(10.0, score))

    def _calculate_sentiment(self, emotion_scores: Dict[str, float]) -> float:
        """
        计算情感得分 (-1 to 1)
        """
        if not emotion_scores:
            return 0.0

        positive = sum(emotion_scores.get(e, 0) for e in ["happy", "calm"])
        negative = sum(emotion_scores.get(e, 0) for e in ["anxious", "sad", "angry", "stressed", "tired", "fear"])

        if positive + negative == 0:
            return 0.0

        return (positive - negative) / (positive + negative)

    def _calculate_confidence(self, emotion_scores: Dict[str, float], text: str) -> float:
        """
        计算分析置信度
        """
        # Longer text = higher confidence (more data)
        text_length_factor = min(len(text) / 100, 1.0) * 0.3

        # Emotion density factor
        total_emotion = sum(emotion_scores.values())
        emotion_density_factor = min(total_emotion / 2, 1.0) * 0.4

        # Has clear dominant emotion = higher confidence
        if emotion_scores:
            max_score = max(emotion_scores.values())
            dominant_factor = max_score * 0.3 if max_score > 0.3 else 0.1
        else:
            dominant_factor = 0.0

        confidence = text_length_factor + emotion_density_factor + dominant_factor

        return max(0.1, min(1.0, confidence))

    def check_sensitive(self, text: str) -> bool:
        """
        检测敏感内容
        如果检测到敏感词，返回True
        """
        text_lower = text.lower()

        for keyword in self.SENSITIVE_KEYWORDS:
            if keyword in text_lower:
                return True

        return False

    def get_intent(self, text: str) -> str:
        """
        识别用户意图
        返回: emotion_share, question, greeting, general
        """
        text_lower = text.lower()

        # Greeting patterns
        greetings = ["你好", "hi", "hello", "嗨", " hey"]
        if any(g in text_lower for g in greetings) and len(text) < 20:
            return "greeting"

        # Question patterns
        question_patterns = ["吗", "?", "怎么", "为什么", "what", "how", "why", "?"]
        if any(p in text for p in question_patterns):
            return "question"

        # Emotion sharing (expresses feelings)
        emotion_indicators = ["我", "感觉", "觉得", "今天", "最近", "i feel", "i'm", "i am"]
        if any(e in text_lower for e in emotion_indicators):
            return "emotion_share"

        return "general"
