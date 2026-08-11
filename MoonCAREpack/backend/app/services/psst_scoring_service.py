from typing import Any, Dict, List


PSST_ITEM_CATALOG: List[Dict[str, str]] = [
    {"code": "1", "key": "irritability", "section": "symptom", "domain": "core_emotion", "label": "愤怒/易怒"},
    {"code": "2", "key": "anxiety", "section": "symptom", "domain": "core_emotion", "label": "焦虑/紧张"},
    {"code": "3", "key": "tearful", "section": "symptom", "domain": "core_emotion", "label": "想哭/敏感"},
    {"code": "4", "key": "depressed", "section": "symptom", "domain": "core_emotion", "label": "低落/无望"},
    {"code": "5", "key": "work_interest", "section": "symptom", "domain": "behavior", "label": "工作/学习兴趣下降"},
    {"code": "6", "key": "home_interest", "section": "symptom", "domain": "behavior", "label": "家务兴趣下降"},
    {"code": "7", "key": "social_interest", "section": "symptom", "domain": "behavior", "label": "社交兴趣下降"},
    {"code": "8", "key": "concentration", "section": "symptom", "domain": "behavior", "label": "难以集中"},
    {"code": "9", "key": "fatigue", "section": "symptom", "domain": "body", "label": "疲惫/乏力"},
    {"code": "10", "key": "craving", "section": "symptom", "domain": "body", "label": "食欲变化"},
    {"code": "11", "key": "insomnia", "section": "symptom", "domain": "body", "label": "失眠"},
    {"code": "12", "key": "hypersomnia", "section": "symptom", "domain": "body", "label": "嗜睡"},
    {"code": "13", "key": "overwhelmed", "section": "symptom", "domain": "body", "label": "失控/难以应对"},
    {"code": "14", "key": "physical_symptoms", "section": "symptom", "domain": "body", "label": "身体症状"},
    {"code": "A", "key": "work_impairment", "section": "impairment", "domain": "function", "label": "工作/学习效率受影响"},
    {"code": "B", "key": "coworker_impairment", "section": "impairment", "domain": "function", "label": "工作关系受影响"},
    {"code": "C", "key": "family_impairment", "section": "impairment", "domain": "function", "label": "家庭关系受影响"},
    {"code": "D", "key": "social_impairment", "section": "impairment", "domain": "function", "label": "社交活动受影响"},
    {"code": "E", "key": "home_impairment", "section": "impairment", "domain": "function", "label": "家务责任受影响"},
]


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
            "irritability": ["烦躁", "易怒", "脾气大", "一点就炸", "火大", "爆炸", "暴躁"],
            "anxiety": ["焦虑", "紧张", "慌", "心里绷着", "担心很多", "担心", "不安"],
            "tearful": ["想哭", "容易哭", "委屈", "敏感", "受伤"],
            "depressed": ["低落", "没意思", "无望", "绝望", "开心不起来"],

            # 行为（题5-8）
            "work_interest": ["不想工作", "不想学习", "提不起劲", "不想上班", "不想学"],
            "home_interest": ["不想做家务", "不想收拾", "不想动", "家里的事不想管"],
            "social_interest": ["不想社交", "不想回消息", "不想见人", "想一个人待着", "不想出门"],
            "concentration": ["难集中", "很难集中", "注意力", "专注不了", "脑子乱", "看不进去"],

            # 身体（题9-14）
            "fatigue": ["很累", "累", "没精神", "乏力", "疲惫"],
            "craving": ["想吃", "暴食", "想吃甜的", "停不下来"],
            "insomnia": ["睡不着", "睡不好", "失眠", "很难入睡", "入睡困难", "老醒"],
            "hypersomnia": ["一直想睡", "嗜睡", "睡不醒", "困得不行"],
            "overwhelmed": ["失控", "撑不住", "扛不住", "控制不了", "管不住", "事情太多"],
            "physical_symptoms": ["头痛", "乳房胀痛", "乳房痛", "肚子胀", "腹痛", "腰酸", "水肿", "胀痛"],

            # 功能损害（A-E）
            "work_impairment": ["效率下降", "工作受影响", "学习受影响", "明显受影响", "做不动"],
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

    def item_catalog(self) -> List[Dict[str, str]]:
        """Return the 19 PSST items used as the hidden interview scoring backbone."""
        return [dict(item) for item in PSST_ITEM_CATALOG]

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
                "document_level": "safety_handoff",
                "label": "较高风险",
                "summary": "本次聊天出现需要立即认真对待的安全信号，这不是诊断；请优先联系可信任的人或专业支持。",
                "scores": signals,
                "rule_hits": {},
            }

        core_ge2 = sum(1 for d in self.core_dims if signals.get(d, 0) >= 2)
        core_eq3 = sum(1 for d in self.core_dims if signals.get(d, 0) == 3)
        symptom_ge2 = sum(1 for d in self.symptom_dims if signals.get(d, 0) >= 2)
        impairment_ge2 = sum(1 for d in self.impairment_dims if signals.get(d, 0) >= 2)
        impairment_eq3 = sum(1 for d in self.impairment_dims if signals.get(d, 0) == 3)

        rule_hits = {
            "core_ge2": core_ge2 >= 1,
            "core_eq3": core_eq3 >= 1,
            "symptom_ge2": symptom_ge2 >= 4,
            "impairment_ge2": impairment_ge2 >= 1,
            "impairment_eq3": impairment_eq3 >= 1,
        }

        if rule_hits["core_eq3"] and rule_hits["symptom_ge2"] and rule_hits["impairment_eq3"]:
            level = "high_risk"
            document_level = "pmdd_possible"
            label = "较高风险"
            summary = "这次聊天里，经前情绪、身体和生活影响信号都比较明显；这只是自我观察参考，不代表诊断，建议尽快咨询妇科或心理健康专业人员。"
        elif rule_hits["core_ge2"] and rule_hits["symptom_ge2"] and rule_hits["impairment_ge2"]:
            level = "moderate_to_severe_pms"
            document_level = "moderate_to_severe_pms"
            label = "中度至重度"
            summary = "你的经前波动已经到了值得认真照顾和持续观察的程度；这只是参考小结，不代表诊断。"
        else:
            level = "mild_or_none"
            document_level = "mild_or_none"
            label = "无/轻度"
            summary = "目前看来，你的经前波动更偏轻度，仍然值得持续观察和温柔照顾；这不代表诊断。"

        return {
            "level": level,
            "document_level": document_level,
            "label": label,
            "summary": summary,
            "scores": signals,
            "rule_hits": rule_hits,
            "core_ge2": core_ge2,
            "symptom_ge2": symptom_ge2,
            "impairment_ge2": impairment_ge2,
        }
