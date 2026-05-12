from typing import Dict, Any, Optional


class ReportService:
    """
    把 PSST 风格结果转成用户可读的个性化小画像
    """

    def build_screening_report(
        self,
        psst_summary: Dict[str, Any],
        user_excerpt: Optional[str] = None
    ) -> str:
        level = psst_summary.get("level", "mild_or_none")
        scores = psst_summary.get("scores", {})

        symptom_map = {
            "irritability": "烦躁/易怒",
            "anxiety": "焦虑/紧张",
            "tearful": "想哭/敏感",
            "depressed": "低落感",
            "work_interest": "对工作/学习提不起劲",
            "home_interest": "家务动力下降",
            "social_interest": "社交兴趣下降",
            "concentration": "难以集中",
            "fatigue": "疲惫乏力",
            "craving": "食欲变化",
            "insomnia": "睡眠困难",
            "hypersomnia": "嗜睡",
            "overwhelmed": "失控感",
            "physical_symptoms": "身体不适",
            "work_impairment": "工作/学习效率受影响",
            "coworker_impairment": "工作关系受影响",
            "family_impairment": "家庭关系受影响",
            "social_impairment": "社交活动受影响",
            "home_impairment": "家务责任受影响",
        }

        highlighted = [k for k, v in scores.items() if v >= 2 and k in symptom_map]
        symptom_text = "、".join(symptom_map[x] for x in highlighted[:6]) or "轻微波动"

        if level == "mild_or_none":
            return (
                "【你的经前状态小结】\n"
                f"根据这次聊天，你最近经前的状态整体更偏轻度波动，主要表现为：{symptom_text}。\n"
                "这些变化目前还属于可以观察和慢慢照顾自己的范围。\n\n"
                "你接下来可以先试试：\n"
                "1. 去和情绪宝宝聊聊，继续说说这几天最明显的感受\n"
                "2. 做一个轻量疗愈活动，比如呼吸练习或情绪日记\n"
                "3. 开始记录你的情绪周期，看看下个月有没有相似规律"
            )

        if level == "moderate_to_severe_pms":
            return (
                "【你的经前状态小结】\n"
                f"根据这次聊天，你这个月经前已经出现了一些值得认真照顾的信号，主要表现为：{symptom_text}，并且这些变化对生活有一定影响。\n"
                "这不代表你有问题，而是说明你的身体和情绪在这个阶段更需要被好好照顾。\n\n"
                "你接下来可以优先试试：\n"
                "1. 去和情绪宝宝聊聊，让陪伴宝宝继续接住你\n"
                "2. 打开百科宝宝，看看身体和情绪为什么会在经前被放大\n"
                "3. 做一个疗愈活动，比如呼吸、音乐或轻量行动提醒\n"
                "4. 如果这种情况反复出现，也建议考虑咨询专业医生进一步评估"
            )

        return (
            "【你的经前状态小结】\n"
            f"根据这次聊天，你这次经前的波动已经比较明显，主要表现为：{symptom_text}。\n"
            "这份内容只是基于本次聊天整理出的参考小结，不等于正式诊断，但说明你现在很需要被更认真地照顾。\n\n"
            "你接下来最重要的是：\n"
            "1. 优先进入守护支持，不要一个人扛着\n"
            "2. 如有需要，尽快联系身边可信任的人或专业支持资源\n"
            "3. 在产品内先使用低负担的疗愈活动，慢慢把身体和情绪稳定下来"
        )
