from typing import Dict, Any


class PSSTScoringService:
    """
    MVP 版 PMS 维度参考评估：
    - 不做显性量表或正式检验
    - 根据用户文本提取 signals
    - 再映射成简化版 0~3 分
    - 输出三档：
      mild_or_none
      moderate_to_severe_pms
      high_risk
    """

    def __init__(self):
        self.signal_keywords = {
            # 情绪核心（题1-4）
            "irritability": ["烦躁", "易怒", "脾气大", "一点就炸", "火大", "爆炸"],
            "anxiety": ["焦虑", "紧张", "慌", "心里绷着", "担心很多"],
            "tearful": ["想哭", "容易哭", "委屈", "敏感", "受伤"],
            "depressed": ["低落", "没意思", "无望", "绝望", "开心不起来"],

            # 行为（题5-8）
            "work_interest": ["不想工作", "不想学习", "提不起劲", "不想上班", "不想学"],
            "home_interest": ["不想做家务", "不想收拾", "不想动", "家里的事不想管"],
            "social_interest": ["不想社交", "不想回消息", "不想见人", "想一个人待着"],
            "concentration": ["难集中", "专注不了", "脑子乱", "看不进去"],

            # 身体（题9-14）
            "fatigue": ["很累", "没精神", "乏力", "疲惫"],
            "craving": ["想吃", "暴食", "想吃甜的", "停不下来"],
            "insomnia": ["睡不着", "失眠", "很难入睡", "老醒"],
            "hypersomnia": ["一直想睡", "嗜睡", "睡不醒", "困得不行"],
            "overwhelmed": ["失控", "撑不住", "扛不住", "控制不了"],
            "physical_symptoms": ["头痛", "乳房胀痛", "肚子胀", "腹痛", "腰酸", "水肿"],

            # 功能损害（A-E）
            "work_impairment": ["效率下降", "工作受影响", "学习受影响", "做不动"],
            "coworker_impairment": ["和同事冲突", "和老师冲突", "工作关系受影响"],
            "family_impairment": ["和家人吵", "和对象吵", "和父母冲突", "家庭关系受影响"],
            "social_impairment": ["社交受影响", "取消约", "不想和朋友见面"],
            "home_impairment": ["家务顾不上", "家里的事顾不上", "责任扛不动"],

            # 高风险附加
            "crisis": ["不想活", "想死", "自杀", "活不下去", "想消失"]
        }

        self.intensity_words = {
            3: ["特别", "非常", "完全", "每天都", "严重", "根本", "失控"],
            2: ["明显", "经常", "挺", "比较", "反复"],
            1: ["有点", "偶尔", "轻微", "一点点"],
        }

        self.core_dims = ["irritability", "anxiety", "tearful", "depressed"]
        self.symptom_dims = [
            "irritability", "anxiety", "tearful", "depressed",
            "work_interest", "home_interest", "social_interest", "concentration",
            "fatigue", "craving", "insomnia", "hypersomnia", "overwhelmed", "physical_symptoms"
        ]
        self.impairment_dims = [
            "work_impairment", "coworker_impairment", "family_impairment",
            "social_impairment", "home_impairment"
        ]

    def _infer_score(self, text: str, keywords: list[str]) -> int:
        if not any(kw in text for kw in keywords):
            return 0

        for score, words in self.intensity_words.items():
            if any(w in text for w in words):
                return score

        return 2

    def signals_from_user_text(self, user_blob: str) -> Dict[str, int]:
        text = (user_blob or "").lower()
        signals = {}

        for dim, keywords in self.signal_keywords.items():
            signals[dim] = self._infer_score(text, keywords)

        return signals

    def score_from_ratings(self, signals: Dict[str, int]) -> Dict[str, Any]:
        # 高风险单独优先
        crisis_score = signals.get("crisis", 0)
        if crisis_score >= 2:
            return {
                "level": "high_risk",
                "label": "较高风险",
                "summary": "本次访谈中出现了较高风险信号，需要优先关注安全与即时支持。",
                "scores": signals
            }

        core_ge2 = sum(1 for d in self.core_dims if signals.get(d, 0) >= 2)
        core_eq3 = sum(1 for d in self.core_dims if signals.get(d, 0) == 3)
        symptom_ge2 = sum(1 for d in self.symptom_dims if signals.get(d, 0) >= 2)
        impairment_ge2 = sum(1 for d in self.impairment_dims if signals.get(d, 0) >= 2)
        impairment_eq3 = sum(1 for d in self.impairment_dims if signals.get(d, 0) == 3)

        if core_eq3 >= 1 and symptom_ge2 >= 4 and impairment_eq3 >= 1:
            level = "high_risk"
            label = "较高风险"
            summary = "你的经前情绪与生活影响已经比较明显，建议尽快寻求专业支持。"
        elif core_ge2 >= 1 and symptom_ge2 >= 4 and impairment_ge2 >= 1:
            level = "moderate_to_severe_pms"
            label = "中度至重度"
            summary = "你的经前波动已经到了值得认真照顾和持续观察的程度。"
        else:
            level = "mild_or_none"
            label = "无/轻度"
            summary = "目前看来，你的经前波动更偏轻度，仍然值得持续观察和温柔照顾。"

        return {
            "level": level,
            "label": label,
            "summary": summary,
            "scores": signals,
            "core_ge2": core_ge2,
            "symptom_ge2": symptom_ge2,
            "impairment_ge2": impairment_ge2,
        }
