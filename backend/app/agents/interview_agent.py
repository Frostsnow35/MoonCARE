from app.utils.safety import contains_crisis_signal


class InterviewAgent:
    MAX_ASSISTANT_TURNS = 6

    def start(self):
        return (
            "嗨，欢迎来到她语 MoonCARE。第一次见面，我想先慢慢了解一下你最近经前那几天的状态。\n\n"
            "不用担心没有标准答案，就像平时聊天一样就好。\n\n"
            "最近那几天，你更像是哪种感觉：容易被点着，还是一直有点绷着、压着？"
        )

    def next_turn(self, messages):
        # 当前已经问到第几轮（assistant说了几次）
        assistant_count = sum(1 for m in messages if m.role == "assistant")

        if assistant_count == 1:
            return (
                '我听到了，你说那种的感觉，其实挺不好受的。\n\n'
                "那我再多问你一点：那几天你会不会也更容易委屈、想哭，或者别人一句话就特别容易戳到你？"
            )

        elif assistant_count == 2:
            return (
                "嗯，我大概能想象那种状态。\n\n"
                "那种时候，会不会有一阵子整个人突然变得很低落？比如什么都提不起劲，连平时还挺喜欢的事情也不太想做？"
            )

        elif assistant_count == 3:
            return (
                "听起来那几天对你来说真的挺消耗的。\n\n"
                "那这种状态会影响到你日常吗？比如学习、做事效率变低，或者很难开始一件事情？"
            )

        elif assistant_count == 4:
            return (
                "明白了，那其实已经在影响你节奏了。\n\n"
                "我再确认一个小点：那几天你会不会更容易累、注意力很难集中，或者不太想和别人说话？"
            )

        elif assistant_count == 5:
            return (
                "嗯，这些感觉其实很多人都会在那几天经历到。\n\n"
                "那身体上呢？比如睡不好、容易胀、或者会特别想吃甜的、吃东西停不下来？"
            )

        elif assistant_count == 6:
            return (
                "我差不多了解你的状态了。\n\n"
                "最后想问一个整体一点的问题：这些变化，大概会影响你到什么程度？"
                "是有点不舒服但还能正常生活，还是已经明显影响到你的节奏、人际或者状态？"
            )

        else:
            return (
                "谢谢你愿意认真说这些，这已经不容易了。\n\n"
                "我会帮你整理一下刚刚这些信息，看看你现在更接近什么样的状态，也会给你一些更适合你的建议，我们一起慢慢来。"
            )

    def detect_crisis(self, messages):
        for m in messages:
            if m.role == "user":
                if contains_crisis_signal(m.content):
                    return True
        return False
