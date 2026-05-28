import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


class ChatAgentQualityTests(unittest.TestCase):
    def test_response_quality_guard_loads_empathy_templates_from_prompt_file(self):
        from app.services.response_quality_service import ResponseQualityGuard

        guard = ResponseQualityGuard()

        self.assertEqual(guard.template_source.name, "empathy_templates.json")
        self.assertIn("fast_ack", guard.empathy_templates)
        self.assertIn("open_disclosure", guard.empathy_templates)

    def test_open_disclosure_reply_uses_empathy_template_open_question(self):
        from app.services.response_quality_service import ResponseQualityGuard

        guard = ResponseQualityGuard()
        reply = guard.direct_reply_if_applicable(
            "我想倾诉",
            {"cycle_phase": "未知", "risk_level": "low"},
        )

        self.assertTrue(reply)
        self.assertTrue(any(marker in reply for marker in ["如果你想多说一点", "如果愿意", "慢慢说"]))
        self.assertNotIn("最想被听见", reply)
        self.assertNotIn("放在这里", reply)

    def test_short_ambiguous_distress_reply_keeps_feeling_open(self):
        from app.services.response_quality_service import ResponseQualityGuard

        guard = ResponseQualityGuard()
        reply = guard.direct_reply_if_applicable(
            "我有点难受",
            {"cycle_phase": "经前期", "risk_level": "medium"},
        )

        self.assertTrue(reply)
        for forbidden in ["低落", "压下去", "解释清楚", "经前", "经期", "诊断"]:
            self.assertNotIn(forbidden, reply)
        self.assertIn("我收到啦", reply)
        self.assertNotIn("更像什么感觉", reply)
        self.assertNotIn("被人惹到了、身体不舒服，还是事情太多", reply)

    def test_clear_body_discomfort_comforts_and_guides_without_more_questioning(self):
        from app.services.response_quality_service import ResponseQualityGuard

        guard = ResponseQualityGuard()
        reply = guard.direct_reply_if_applicable(
            "我来月经了，头晕，小腹也很痛",
            {"cycle_phase": "经期", "risk_level": "low"},
        )

        self.assertTrue(reply)
        self.assertIn("身体不舒服", reply)
        self.assertTrue(any(marker in reply for marker in ["坐", "躺", "安顿", "热敷", "温水", "休息"]))
        for forbidden in ["消耗掉一点", "被看见"]:
            self.assertNotIn(forbidden, reply)

    def test_clear_emotional_context_gets_support_not_interview_question(self):
        from app.services.response_quality_service import ResponseQualityGuard

        guard = ResponseQualityGuard()
        reply = guard.direct_reply_if_applicable(
            "我因为和男朋友吵架很委屈",
            {"cycle_phase": "未知", "risk_level": "low"},
        )

        self.assertTrue(reply)
        self.assertIn("男朋友", reply)
        self.assertIn("委屈", reply)
        self.assertTrue(any(marker in reply for marker in ["抱", "缓", "陪", "站在你这边"]))
        for forbidden in ["愿意说说", "更像什么感觉", "什么样的难受", "待一会儿"]:
            self.assertNotIn(forbidden, reply)

    def test_short_unhappy_disclosure_gets_fast_natural_support_reply(self):
        from app.services.response_quality_service import ResponseQualityGuard

        guard = ResponseQualityGuard()
        reply = guard.direct_reply_if_applicable(
            "我不开心",
            {"cycle_phase": "未知", "risk_level": "low"},
        )

        self.assertTrue(reply)
        self.assertIn("我收到啦", reply)
        self.assertTrue(any(marker in reply for marker in ["陪", "不急", "在这儿"]))
        for forbidden in ["轻飘飘", "继续往下放", "最想被听见", "一句话先放在这里", "呼一口气", "放下来", "🌷"]:
            self.assertNotIn(forbidden, reply)

    def test_reply_repair_removes_repeated_sentence(self):
        from app.services.response_quality_service import ResponseQualityGuard

        guard = ResponseQualityGuard()
        reply = guard.repair_reply(
            "我有点难受",
            "我听到啦，你现在心里/身体不太舒服。我听到啦，你现在心里/身体不太舒服。"
            "这种感觉可以先在这里待一会儿。",
            {"risk_level": "medium"},
        )

        self.assertEqual(reply.count("我听到啦，你现在心里/身体不太舒服"), 1)

    def test_body_discomfort_defaults_to_witnessing_before_advice(self):
        from app.services.response_quality_service import ResponseQualityGuard

        guard = ResponseQualityGuard()
        reply = guard.direct_reply_if_applicable(
            "我来月经了，身体不舒服",
            {"cycle_phase": "经期", "risk_level": "low"},
        )

        self.assertTrue(reply)
        self.assertIn("身体不舒服", reply)
        self.assertIn("就听着", reply)
        self.assertTrue(any(marker in reply for marker in ["啦", "呀", "呢", "🫶", "💗", "🌷"]))
        self.assertNotIn("消耗掉一点", reply)
        self.assertNotIn("被看见", reply)
        for forbidden in [
            "尤其是来月经或经期前后",
            "蜷起来",
            "出血异常",
            "专业医生",
            "仅供参考",
            "一阵一阵",
            "持续的坠胀",
        ]:
            self.assertNotIn(forbidden, reply)

    def test_body_pain_follow_up_uses_recent_context_instead_of_repeating(self):
        from app.services.response_quality_service import ResponseQualityGuard

        guard = ResponseQualityGuard()
        reply = guard.direct_reply_if_applicable(
            "我感觉真的很痛",
            {
                "cycle_phase": "经期",
                "risk_level": "low",
                "support_context": {"body_signals": ["pain"], "menstrual_related": True},
                "conversation_messages": [
                    {"role": "user", "content": "我来月经了，身体不舒服"},
                    {
                        "role": "assistant",
                        "content": "我听到啦，来月经的时候身体不舒服真的会把人消耗掉一点。我们可以先只陪它待一会儿，让这份不舒服被看见。",
                    },
                ],
            },
        )

        self.assertTrue(reply)
        self.assertIn("刚才", reply)
        self.assertIn("来月经", reply)
        self.assertIn("真的很痛", reply)
        self.assertNotIn("来月经的时候身体不舒服真的会把人消耗掉一点", reply)
        self.assertNotIn("愿意", reply)
        self.assertNotIn("说说", reply)

    def test_menstrual_joke_is_detected_and_replaced(self):
        """测试对月经相关玩笑的检测和替换"""
        from app.services.response_quality_service import ResponseQualityGuard

        guard = ResponseQualityGuard()
        
        # 测试各种玩笑模式
        test_cases = [
            "为什么经期女生走路都特别慢？因为她在流量控制模式里，不能加速。🚶‍♀️💨",
            "这就是你的PMS发作了吧，脾气这么大",
            "不就是来个月经吗，至于这么矫情吗",
            "忍忍就过去了，每个月都来习惯就好",
            "大姨妈来了真晦气",
        ]
        
        for test_reply in test_cases:
            with self.subTest(test_reply=test_reply):
                repaired = guard.repair_reply("我来月经了，肚子很痛", test_reply, {})
                expected = f"抱歉，晚了一点点。{guard.SAFE_RESPONSE_FOR_DISRESPECT}"
                self.assertEqual(repaired, expected)
    
    def test_normal_menstrual_support_is_not_replaced(self):
        """测试正常的经期支持回复不会被误替换"""
        from app.services.response_quality_service import ResponseQualityGuard

        guard = ResponseQualityGuard()
        
        # 测试正常的支持回复
        normal_replies = [
            "我听到啦，来月经的时候身体不舒服真的会很消耗。先找个舒服的位置靠一会儿。",
            "痛经真的很不好受，能热敷就轻轻热敷一下小腹。",
            "我在这里陪着你，慢慢说。",
        ]
        
        for test_reply in normal_replies:
            with self.subTest(test_reply=test_reply):
                repaired = guard.repair_reply("我来月经了，肚子很痛", test_reply, {})
                self.assertEqual(repaired, test_reply)
    
    def test_menstrual_disrespect_detection_works(self):
        """测试不尊重内容的检测方法"""
        from app.services.response_quality_service import ResponseQualityGuard

        guard = ResponseQualityGuard()
        
        # 应该被检测到的内容
        disrespectful_cases = [
            "流量控制",
            "流量模式",
            "矫情",
            "装的",
            "至于吗",
            "忍忍就过去了",
            "晦气",
            "脏",
            "PMS发作",
            "激素作祟",
            "为什么经期",
            "为什么来月经",
        ]
        
        for case in disrespectful_cases:
            with self.subTest(case=case):
                self.assertTrue(guard._is_menstrual_disrespect(case))
        
        # 不应该被检测到的内容
        safe_cases = [
            "我听到啦",
            "身体不舒服",
            "热敷一下",
            "喝杯温水",
            "我陪着你",
        ]
        
        for case in safe_cases:
            with self.subTest(case=case):
                self.assertFalse(guard._is_menstrual_disrespect(case))


class KnowledgeAgentLocalRagTests(unittest.TestCase):
    def test_knowledge_agent_loads_local_cards_without_llm_provider(self):
        from app.agents import knowledge_agent as knowledge_module

        with patch.object(knowledge_module, "LLMService", side_effect=ValueError("missing api key")):
            agent = knowledge_module.KnowledgeAgent()

        self.assertGreater(len(agent.knowledge), 0)
        self.assertIsNone(agent.llm)

    def test_knowledge_agent_answers_from_local_card_when_llm_unavailable(self):
        from app.agents import knowledge_agent as knowledge_module

        with patch.object(knowledge_module, "LLMService", side_effect=ValueError("missing api key")):
            agent = knowledge_module.KnowledgeAgent()

        reply = agent.respond("为什么经前会情绪波动？", {})

        self.assertIn("经前", reply)
        self.assertIn("仅供参考", reply)
        self.assertNotIn("暂时没有相关信息", reply)

    def test_knowledge_agent_fallback_answers_the_specific_symptom(self):
        from app.agents import knowledge_agent as knowledge_module

        with patch.object(knowledge_module, "LLMService", side_effect=ValueError("missing api key")):
            agent = knowledge_module.KnowledgeAgent()

        reply = agent.respond("经期为什么会头晕？", {})

        self.assertIn("头晕", reply)
        self.assertIn("经期", reply)
        self.assertIn("仅供参考", reply)
        self.assertNotIn("情绪突然变化", reply)
        self.assertNotIn("我帮你一起梳理规律", reply)

    def test_knowledge_agent_rewrites_high_risk_card_into_safe_menstrual_guidance(self):
        from app.agents import knowledge_agent as knowledge_module

        with patch.object(knowledge_module, "LLMService", side_effect=ValueError("missing api key")):
            agent = knowledge_module.KnowledgeAgent()

        reply = agent.respond("痛经痛得受不了怎么办？", {})

        self.assertIn("痛经", reply)
        self.assertTrue(any(marker in reply for marker in ["热敷", "休息", "补水", "散步", "拉伸"]))
        self.assertTrue(any(marker in reply for marker in ["如果", "建议", "就医"]))
        for forbidden in ["布洛芬", "避孕药", "子宫内膜异位症", "手术", "激素治疗"]:
            self.assertNotIn(forbidden, reply)

    def test_knowledge_agent_card_answer_keeps_reason_then_action_then_seek_care_order(self):
        from app.agents import knowledge_agent as knowledge_module

        with patch.object(knowledge_module, "LLMService", side_effect=ValueError("missing api key")):
            agent = knowledge_module.KnowledgeAgent()

        reply = agent.respond("经期为什么会头晕？", {})

        reason_index = reply.find("可能")
        action_index = max(reply.find("坐下"), reply.find("躺一会儿"), reply.find("温水"))
        care_index = max(reply.find("联系医生"), reply.find("咨询医生"), reply.find("尽快"))

        self.assertGreaterEqual(reason_index, 0)
        self.assertGreater(action_index, reason_index)
        self.assertGreater(care_index, action_index)

    def test_knowledge_agent_synthesizes_card_with_user_context_when_llm_unavailable(self):
        from app.agents import knowledge_agent as knowledge_module

        with patch.object(knowledge_module, "LLMService", side_effect=ValueError("missing api key")):
            agent = knowledge_module.KnowledgeAgent()

        reply = agent.respond(
            "我快来月经了，为什么最近男朋友讲几句话我就很烦？",
            {"recent_context": "user: 男朋友讲几句话我就烦了，我自己也不想这样。"},
        )

        self.assertIn("经前", reply)
        self.assertTrue(any(marker in reply for marker in ["男朋友", "亲密关系", "关系"]))
        self.assertIn("不是", reply)
        self.assertIn("仅供参考", reply)
        self.assertFalse(reply.startswith("关于"))


class StreamingFallbackTests(unittest.TestCase):
    def test_streaming_emotional_first_turn_sends_fast_ack_before_model_reply(self):
        import asyncio
        from app.services import agent_service as agent_module

        class FakeLLMService:
            async def async_streaming_generate_reply(self, user_message, context):
                yield {
                    "token": "我会继续陪你把这件事慢慢说清楚。",
                    "first_token_latency_ms": 1200,
                }

        async def collect_chunks():
            service = agent_module.AgentService()
            with patch.object(agent_module, "LLMService", FakeLLMService):
                return [
                    chunk
                    async for chunk in service.get_streaming_response(
                        user_id=1,
                        session_id="fast-ack-session",
                        user_message="我今天真的很难过",
                        context={"conversation_memory": {"conversation_messages": []}},
                        agent_mode="support",
                    )
                ]

        chunks = asyncio.run(collect_chunks())
        token_chunks = [chunk for chunk in chunks if chunk.get("type") == "token"]
        end_chunks = [chunk for chunk in chunks if chunk.get("type") == "end"]

        self.assertGreaterEqual(len(token_chunks), 2)
        self.assertIn("我在", token_chunks[0]["token"])
        self.assertIn("继续陪你", "".join(chunk["token"] for chunk in token_chunks))
        self.assertTrue(end_chunks)
        self.assertIn("我在", end_chunks[-1]["full_response"])
        self.assertIn("继续陪你", end_chunks[-1]["full_response"])

    def test_streaming_fast_ack_model_error_does_not_duplicate_fallback(self):
        import asyncio
        from app.services import agent_service as agent_module

        class FakeLLMService:
            async def async_streaming_generate_reply(self, user_message, context):
                yield {"error": "first_token_timeout"}

        async def collect_chunks():
            service = agent_module.AgentService()
            with patch.object(agent_module, "LLMService", FakeLLMService):
                return [
                    chunk
                    async for chunk in service.get_streaming_response(
                        user_id=1,
                        session_id="fast-ack-error-session",
                        user_message="我今天真的很难过",
                        context={"conversation_memory": {"conversation_messages": []}},
                        agent_mode="support",
                    )
                ]

        chunks = asyncio.run(collect_chunks())
        token_chunks = [chunk for chunk in chunks if chunk.get("type") == "token"]
        token_text = "".join(chunk.get("token", "") for chunk in token_chunks)
        end_chunk = [chunk for chunk in chunks if chunk.get("type") == "end"][-1]

        self.assertGreaterEqual(len(token_chunks), 2)
        self.assertEqual(end_chunk["full_response"], token_text)
        self.assertEqual(end_chunk["reply_status"], "timeout_fallback")
        self.assertLessEqual(token_text.count("如果你愿意"), 1)

    def test_streaming_support_second_turn_uses_soft_fallback_without_error_when_llm_unavailable(self):
        import asyncio
        from app.services import agent_service as agent_module

        async def collect_chunks():
            service = agent_module.AgentService()
            with patch.object(agent_module, "LLMService", side_effect=ValueError("missing api key")):
                return [
                    chunk
                    async for chunk in service.get_streaming_response(
                        user_id=1,
                        session_id="same-session",
                        user_message="还是有点堵",
                        context={"conversation_memory": {"conversation_messages": []}},
                        agent_mode="support",
                    )
                ]

        chunks = asyncio.run(collect_chunks())
        token_text = "".join(chunk.get("token", "") for chunk in chunks if chunk.get("type") == "token")
        end_chunks = [chunk for chunk in chunks if chunk.get("type") == "end"]

        self.assertTrue(token_text)
        self.assertTrue(end_chunks)
        self.assertNotIn("error", end_chunks[-1])

    def test_streaming_short_unhappy_disclosure_stays_natural_when_llm_unavailable(self):
        import asyncio
        from app.services import agent_service as agent_module

        async def collect_chunks():
            service = agent_module.AgentService()
            with patch.object(agent_module, "LLMService", side_effect=ValueError("missing api key")):
                return [
                    chunk
                    async for chunk in service.get_streaming_response(
                        user_id=1,
                        session_id="short-unhappy-stream",
                        user_message="我不开心",
                        context={"conversation_memory": {"conversation_messages": []}},
                        agent_mode="support",
                    )
                ]

        chunks = asyncio.run(collect_chunks())
        token_text = "".join(chunk.get("token", "") for chunk in chunks if chunk.get("type") == "token")
        end_chunk = [chunk for chunk in chunks if chunk.get("type") == "end"][-1]

        self.assertIn("我收到啦", token_text)
        self.assertIn("不开心", token_text)
        self.assertEqual(end_chunk["reply_status"], "error_fallback")
        for forbidden in ["轻飘飘", "继续往下放", "最想被听见", "一句话先放在这里", "呼一口气", "放下来", "🌷"]:
            self.assertNotIn(forbidden, token_text)

    def test_streaming_irritable_cycle_turn_uses_fast_ack_then_model_reasoning(self):
        import asyncio
        from app.services import agent_service as agent_module

        class PassivePerception:
            def analyze(self, message: str, cycle_phase=None, sensor_data=None):
                return {
                    "risk_level": "low",
                    "cycle_phase": cycle_phase or "经前期",
                    "support_context": {"emotion_signals": ["irritable"], "menstrual_related": True},
                }

        class FakeLLMService:
            def __init__(self):
                pass

            async def async_streaming_generate_reply(self, user_message, context):
                yield {
                    "token": "你刚说的是经前快来月经这段时间更烦躁、更容易被点着，我会按这个处境陪你理，不会只丢给你深呼吸。",
                    "first_token_latency_ms": 380,
                }

        async def collect_chunks():
            service = agent_module.AgentService()
            service.perception = PassivePerception()
            with patch.object(agent_module, "LLMService", FakeLLMService):
                return [
                    chunk
                    async for chunk in service.get_streaming_response(
                        user_id=1,
                        session_id="irritable-local-stream",
                        user_message="我快来了这段时间变得这么烦躁",
                        context={"conversation_memory": {"conversation_messages": []}},
                        agent_mode="support",
                    )
                ]

        chunks = asyncio.run(collect_chunks())
        token_chunks = [chunk for chunk in chunks if chunk.get("type") == "token"]
        token_text = "".join(chunk.get("token", "") for chunk in token_chunks)

        self.assertGreaterEqual(len(token_chunks), 2)
        self.assertIn("烦躁", token_text)
        self.assertIn("经前", token_text)
        self.assertIn("不会只丢给你深呼吸", token_text)
        self.assertLessEqual(token_text.count("如果你愿意"), 1)

    def test_streaming_action_request_sends_fast_action_ack_before_model_reply(self):
        import asyncio
        from app.services import agent_service as agent_module

        class FakeLLMService:
            async def async_streaming_generate_reply(self, user_message, context):
                yield {
                    "token": "先把这件事拆成眼前能做的一小步，我们一个个来。",
                    "first_token_latency_ms": 900,
                }

        class PassivePerception:
            def analyze(self, message: str, cycle_phase=None, sensor_data=None):
                return {"risk_level": "low", "cycle_phase": cycle_phase or "未知", "support_context": {}}

        async def collect_chunks():
            service = agent_module.AgentService()
            service.perception = PassivePerception()
            with patch.object(agent_module, "LLMService", FakeLLMService):
                return [
                    chunk
                    async for chunk in service.get_streaming_response(
                        user_id=1,
                        session_id="action-stream-session",
                        user_message="我该怎么做",
                        context={
                            "conversation_memory": {
                                "conversation_messages": [
                                    {"role": "user", "content": "我因为和男朋友吵架很委屈"},
                                    {"role": "assistant", "content": "我听到啦，这种委屈真的很扎心。"},
                                ]
                            }
                        },
                        agent_mode="auto",
                    )
                ]

        chunks = asyncio.run(collect_chunks())
        start_chunk = chunks[0]
        token_chunks = [chunk for chunk in chunks if chunk.get("type") == "token"]
        end_chunk = [chunk for chunk in chunks if chunk.get("type") == "end"][-1]

        self.assertEqual(start_chunk["agent_name"], "action_support")
        self.assertGreaterEqual(len(token_chunks), 2)
        self.assertIn("眼前", token_chunks[0]["token"])
        self.assertIn("一个个来", end_chunk["full_response"])
        self.assertTrue(end_chunk.get("suppress_assessment_prompt"))

    def test_streaming_internal_error_returns_complete_fallback_contract(self):
        import asyncio
        from app.services.agent_service import AgentService

        class BrokenPerception:
            def analyze(self, *args, **kwargs):
                raise RuntimeError("internal perception detail")

        async def collect_chunks():
            service = AgentService()
            service.perception = BrokenPerception()
            return [
                chunk
                async for chunk in service.get_streaming_response(
                    user_id=1,
                    session_id="stream-error-contract",
                    user_message="今天有点乱，想慢慢聊",
                    context={"conversation_memory": {"conversation_messages": []}},
                    agent_mode="support",
                )
            ]

        chunks = asyncio.run(collect_chunks())
        self.assertEqual(chunks[0]["type"], "start")
        token_text = "".join(chunk.get("token", "") for chunk in chunks if chunk.get("type") == "token")
        end_chunk = [chunk for chunk in chunks if chunk.get("type") == "end"][-1]

        self.assertTrue(token_text)
        self.assertEqual(end_chunk["reply_status"], "error_fallback")
        self.assertEqual(end_chunk["full_response"], token_text)
        self.assertFalse(end_chunk["cache_hit"])
        self.assertEqual(end_chunk["cache_similarity"], 0.0)
        self.assertNotIn("error", end_chunk)

    def test_real_chinese_crisis_text_uses_safe_streaming_fallback(self):
        import asyncio
        from app.services.agent_service import AgentService

        async def collect_chunks():
            return [
                chunk
                async for chunk in AgentService().get_streaming_response(
                    user_id=1,
                    session_id="real-crisis",
                    user_message="我想自残",
                    context={"conversation_memory": {"conversation_messages": []}},
                    agent_mode="support",
                )
            ]

        chunks = asyncio.run(collect_chunks())
        token_text = "".join(chunk.get("token", "") for chunk in chunks if chunk.get("type") == "token")

        self.assertIn("安全", token_text)
        self.assertIn("可信任的人", token_text)

    def test_frontend_chat_uses_sse_without_websocket_or_rest_fallback(self):
        chat_view = (BACKEND_ROOT.parent / "frontend" / "src" / "views" / "Chat.vue").read_text(encoding="utf-8")
        chat_store = (BACKEND_ROOT.parent / "frontend" / "src" / "stores" / "chat.js").read_text(encoding="utf-8")

        self.assertIn("sendMessageStream", chat_view)
        self.assertNotIn("new WebSocket", chat_store)
        self.assertNotIn("chatAPI.sendMessage(", chat_view)
        self.assertNotIn("AbortController", chat_view)

    def test_home_state_chat_entry_uses_main_chat_not_legacy_interview(self):
        home_view = (BACKEND_ROOT.parent / "frontend" / "src" / "views" / "Home.vue").read_text(encoding="utf-8")

        self.assertIn("router.push('/chat')", home_view)
        self.assertNotIn("interviewAPI", home_view)
        self.assertNotIn("setInterviewMode", home_view)
        self.assertNotIn("/interview/start", home_view)


class SemanticCacheCompatibilityTests(unittest.TestCase):
    def test_dummy_cache_matches_agent_service_contract(self):
        from app.services.semantic_cache_service import DummySemanticCache

        cache = DummySemanticCache()

        self.assertIsNone(cache.get_cached_response("hello"))
        self.assertIsNone(cache.set_cached_response("hello", "reply", ttl_hours=1))

    def test_get_response_cache_hit_skips_router_after_low_risk_perception(self):
        import asyncio
        from app.services.agent_service import AgentService

        class PassivePerception:
            def analyze(self, message: str, cycle_phase=None, sensor_data=None):
                return {"risk_level": "low", "cycle_phase": cycle_phase or "未知"}

        class CacheHit:
            def get_cached_response(self, *args, **kwargs):
                return {
                    "response": "这是缓存里的温柔回应。",
                    "similarity": 1.0,
                    "match_type": "exact",
                }

            def set_cached_response(self, *args, **kwargs):
                raise AssertionError("cache hit should not be written again")

        service = AgentService()
        service.perception = PassivePerception()
        service.semantic_cache = CacheHit()
        service.router = None

        async def fail_if_router_is_called(*args, **kwargs):
            raise AssertionError("router should not be called on cache hit")

        service._route_with_deadline = fail_if_router_is_called

        result = asyncio.run(
            service.get_response(
                user_id=1,
                session_id="cache-rest",
                user_message="今天想聊点轻松的事",
                context={"conversation_memory": {"conversation_messages": []}},
                agent_mode="support",
            )
        )

        self.assertEqual(result["reply_status"], "cache_hit")
        self.assertTrue(result["cache_hit"])
        self.assertEqual(result["cache_similarity"], 1.0)
        self.assertIn("这是缓存里的温柔回应。", result["message"])
        self.assertTrue(any(marker in result["message"] for marker in ["如果你想多说一点", "如果愿意", "慢慢说"]))

    def test_get_response_crisis_turn_never_reads_semantic_cache(self):
        import asyncio
        from app.services.agent_service import AgentService

        class CrisisPerception:
            def analyze(self, message: str, cycle_phase=None, sensor_data=None):
                return {"risk_level": "crisis", "cycle_phase": cycle_phase or "未知"}

        class CacheMustNotBeRead:
            def get_cached_response(self, *args, **kwargs):
                raise AssertionError("crisis turns must not read semantic cache")

            def set_cached_response(self, *args, **kwargs):
                raise AssertionError("crisis turns must not write semantic cache")

        class InterventionRouter:
            def route(self, message: str, state: dict, agent_mode: str = "auto"):
                return "请先把安全放在第一位，联系可信任的人或当地紧急服务。", "intervention"

        service = AgentService()
        service.perception = CrisisPerception()
        service.semantic_cache = CacheMustNotBeRead()
        service.router = InterventionRouter()

        result = asyncio.run(
            service.get_response(
                user_id=1,
                session_id="cache-crisis",
                user_message="我想自残",
                context={"conversation_memory": {"conversation_messages": []}},
                agent_mode="support",
            )
        )

        self.assertEqual(result["intent"], "intervention")
        self.assertFalse(result["cache_hit"])

    def test_get_response_action_request_never_reads_semantic_cache(self):
        import asyncio
        from app.services.agent_service import AgentService

        class PassivePerception:
            def analyze(self, message: str, cycle_phase=None, sensor_data=None):
                return {"risk_level": "low", "cycle_phase": cycle_phase or "未知", "support_context": {}}

        class GuardedCache:
            def get_cached_response(self, *args, **kwargs):
                raise AssertionError("action request should not read cache")

            def set_cached_response(self, *args, **kwargs):
                raise AssertionError("action request should not write cache")

        service = AgentService()
        service.perception = PassivePerception()
        service.semantic_cache = GuardedCache()

        with patch.object(
            service,
            "_route_with_deadline",
            return_value=("先别急着继续争论，我们先把这一步理出来。", "action_support"),
        ):
            result = asyncio.run(
                service.get_response(
                    user_id=1,
                    session_id="action-no-cache",
                    user_message="我该怎么做",
                    context={
                        "conversation_memory": {
                            "conversation_messages": [
                                {"role": "user", "content": "我因为和男朋友吵架很委屈"},
                            ]
                        }
                    },
                    agent_mode="auto",
                )
            )

        self.assertEqual(result["reply_status"], "ok")
        self.assertEqual(result["intent"], "action_support")

    def test_streaming_cache_hit_emits_tokens_and_cache_metadata_without_llm(self):
        import asyncio
        from app.services.agent_service import AgentService

        class PassivePerception:
            def analyze(self, message: str, cycle_phase=None, sensor_data=None):
                return {"risk_level": "low", "cycle_phase": cycle_phase or "未知"}

        class CacheHit:
            def get_cached_response(self, *args, **kwargs):
                return {
                    "response": "缓存回应也会一段段出现。",
                    "similarity": 0.96,
                    "match_type": "phrase",
                }

            def set_cached_response(self, *args, **kwargs):
                raise AssertionError("streaming cache hit should not be written again")

        async def collect_chunks():
            service = AgentService()
            service.perception = PassivePerception()
            service.semantic_cache = CacheHit()
            service.llm_service = None
            service.router = None
            return [
                chunk
                async for chunk in service.get_streaming_response(
                    user_id=1,
                    session_id="cache-stream",
                    user_message="今天想聊点轻松的事",
                    context={"conversation_memory": {"conversation_messages": []}},
                    agent_mode="support",
                )
            ]

        chunks = asyncio.run(collect_chunks())
        token_text = "".join(chunk.get("token", "") for chunk in chunks if chunk.get("type") == "token")
        end_chunks = [chunk for chunk in chunks if chunk.get("type") == "end"]

        self.assertIn("缓存回应", token_text)
        self.assertTrue(end_chunks)
        self.assertEqual(end_chunks[-1]["reply_status"], "cache_hit")
        self.assertTrue(end_chunks[-1]["cache_hit"])
        self.assertEqual(end_chunks[-1]["cache_similarity"], 0.96)


class ChatApiContractTests(unittest.TestCase):
    def test_chat_contract_builders_share_metadata_fields(self):
        from app.api.v1.chat import (
            _build_rest_chat_payload,
            _build_sse_end_payload,
            _build_ws_assistant_payload,
        )

        response = {
            "message": "我在这里。",
            "intent": "support",
            "state": {"risk_level": "low"},
            "suggestions": ["继续说"],
            "actions": [{"action": "diary"}],
            "reply_status": "cache_hit",
            "elapsed_ms": 12,
            "cache_hit": True,
            "cache_similarity": 0.91,
            "cache_match_type": "phrase",
            "first_token_latency_ms": 7,
        }
        assessment_state = {"status": "idle"}
        memory_state = {"updated": True}

        rest_payload = _build_rest_chat_payload(
            session_id="session-1",
            response=response,
            is_sensitive=False,
            assessment_state=assessment_state,
            memory_state=memory_state,
        )
        ws_payload = _build_ws_assistant_payload(
            response=response,
            sentiment_score=-0.1,
            is_sensitive=False,
            assessment_state=assessment_state,
            memory_state=memory_state,
        )
        sse_payload = _build_sse_end_payload(
            session_id="session-1",
            final_response="我在这里。",
            chunk=response,
            assessment_state=assessment_state,
            memory_state=memory_state,
        )

        for payload in (rest_payload, ws_payload, sse_payload):
            self.assertEqual(payload["reply_status"], "cache_hit")
            self.assertTrue(payload["cache_hit"])
            self.assertEqual(payload["cache_similarity"], 0.91)
            self.assertEqual(payload["cache_match_type"], "phrase")
            self.assertEqual(payload["first_token_latency_ms"], 7)
            self.assertEqual(payload["assessment_state"], assessment_state)
            self.assertEqual(payload["memory_state"], memory_state)

    def test_frontend_persists_sse_cache_metadata_on_assistant_message(self):
        chat_view = (BACKEND_ROOT.parent / "frontend" / "src" / "views" / "Chat.vue").read_text(encoding="utf-8")

        self.assertIn("cacheHit: chunk.cache_hit || false", chat_view)
        self.assertIn("cacheSimilarity: chunk.cache_similarity || 0", chat_view)


class AgentServiceQualityGuardTests(unittest.TestCase):
    def test_get_response_quality_sensitive_turn_calls_model_before_fallback(self):
        import asyncio
        from app.services.agent_service import AgentService

        called = {"count": 0}

        async def run():
            service = AgentService()
            message = "\u6211\u6765\u6708\u7ecf\u4e86\uff0c\u8eab\u4f53\u4e0d\u8212\u670d"

            async def route_with_deadline(router, user_message, state, agent_mode):
                called["count"] += 1
                return "我听见了，来月经时身体不舒服会很消耗。先找个舒服的位置靠一会儿，我陪你慢慢稳住。", "support"

            with patch.object(
                service,
                "_route_with_deadline",
                side_effect=route_with_deadline,
            ):
                return await service.get_response(
                    user_id=1,
                    session_id="quality-guard-fast",
                    user_message=message,
                    context={"conversation_memory": {"conversation_messages": []}},
                    agent_mode="auto",
                )

        response = asyncio.run(run())

        self.assertEqual(response["reply_status"], "ok")
        self.assertEqual(response["intent"], "deterministic_support")
        self.assertEqual(called["count"], 0)
        self.assertIn("身体不舒服", response["message"])

    def test_timeout_fallback_is_contextual_not_fixed_template(self):
        from app.services.agent_service import AgentService

        service = AgentService()
        reply = service._timeout_fallback(
            "我今天被老板批评了，心里乱成一团",
            {"risk_level": "low", "agent_mode": "support"},
        )

        self.assertIn("老板批评", reply)
        self.assertNotIn("最明显的那一点", reply)
        self.assertNotIn("刚才没有顺利接上", reply)
        self.assertNotIn("你可以继续说下一句", reply)

    def test_action_request_timeout_fallback_gives_concrete_next_steps(self):
        from app.services.agent_service import AgentService

        service = AgentService()
        state = {
            "risk_level": "low",
            "agent_mode": "support",
            "conversation_messages": [
                {"role": "user", "content": "我因为和男朋友吵架很委屈"},
                {"role": "assistant", "content": "我听到啦，和男朋友吵架后的委屈真的会很扎心。"},
            ],
        }
        reply = service._timeout_fallback("我该怎么做", state)

        for marker in ["先", "写", "等"]:
            self.assertIn(marker, reply)
        for forbidden in ["我跟上了", "轻飘飘", "继续往下放", "你可以继续说"]:
            self.assertNotIn(forbidden, reply)

    def test_action_request_with_body_context_gives_body_care_steps(self):
        from app.services.agent_service import AgentService

        service = AgentService()
        state = {
            "risk_level": "low",
            "agent_mode": "support",
            "conversation_messages": [
                {"role": "user", "content": "我来月经了，头晕，小腹也很痛"},
                {"role": "assistant", "content": "先坐下或躺一会儿，能热敷就轻轻热敷小腹。"},
            ],
        }
        reply = service._soft_error_fallback("我该怎么做", state)

        self.assertIn("热敷", reply)
        self.assertIn("温水", reply)
        self.assertIn("医生", reply)
        self.assertNotIn("我跟上了", reply)

    def test_action_request_uses_latest_visible_context_before_stale_health_memory(self):
        from app.services.agent_service import AgentService

        service = AgentService()
        state = {
            "risk_level": "low",
            "agent_mode": "support",
            "conversation_messages": [
                {"role": "user", "content": "我因为和男朋友吵架很委屈"},
                {"role": "assistant", "content": "我听到啦，和男朋友吵架后的委屈真的会很扎心。"},
            ],
            "health_context": "用户之前提到来月经、小腹痛、头晕。",
            "memory_context": "历史记忆：经期身体不舒服。",
        }
        reply = service._timeout_fallback("我该怎么做", state)

        self.assertIn("争论", reply)
        self.assertIn("写", reply)
        self.assertNotIn("热敷", reply)
        self.assertNotIn("小腹", reply)

    def test_partner_speaking_request_uses_latest_visible_context(self):
        from app.services.agent_service import AgentService

        service = AgentService()
        state = {
            "risk_level": "low",
            "agent_mode": "support",
            "conversation_messages": [
                {"role": "user", "content": "我和男朋友吵架了，他说我太敏感，我很委屈"},
                {"role": "assistant", "content": "我听到了，这种委屈真的很消耗。"},
            ],
        }

        self.assertTrue(service._looks_like_action_request("刚才那件事我该怎么和他说？"))
        reply = service._timeout_fallback("刚才那件事我该怎么和他说？", state)

        self.assertIn("十分钟", reply)
        self.assertIn("事实", reply)
        self.assertIn("感受", reply)
        self.assertNotIn("刚刚发生了什么", reply)

    def test_action_support_repair_does_not_append_generic_open_question(self):
        from app.services.agent_service import AgentService

        service = AgentService()
        original_reply = (
            "先别急着继续争论或马上回复对方，给自己十分钟从现场抽开一点。"
            "然后把最想表达的一句话写下来，只保留事实和感受，先别发出去。"
        )
        reply = service._repair_reply_quality(
            "刚才那件事我该怎么和他说？",
            original_reply,
            {
                "risk_level": "low",
                "agent_mode": "support",
                "support_intent": "action_support",
            },
        )

        self.assertEqual(reply, original_reply)
        self.assertNotIn("刚刚发生了什么", reply)
        self.assertNotIn("如果你愿意", reply)

    def test_partner_conflict_actions_are_specific_not_breathing_default(self):
        from app.services.agent_service import AgentService

        service = AgentService()
        actions = service._generate_action_suggestions(
            {
                "risk_level": "low",
                "agent_mode": "support",
                "message": "男朋友讲几句话我就烦了，搞得他很生气，我自己不想这样的",
                "support_context": {"emotion_signals": ["irritable"], "menstrual_related": True},
            },
            "support",
        )

        labels = [action["label"] for action in actions]
        self.assertTrue(any("回复" in label or "边界" in label or "写" in label for label in labels))
        self.assertNotEqual(actions[0]["action"], "breathing")

    def test_action_request_repairs_vague_support_reply(self):
        from app.services.agent_service import AgentService

        service = AgentService()
        state = {
            "risk_level": "low",
            "agent_mode": "support",
            "conversation_messages": [
                {"role": "user", "content": "我最近真的很烦躁，不知道该怎么办"},
            ],
        }
        reply = service._repair_reply_quality(
            "我该怎么做",
            "我在。你可以继续说，我会先跟着你现在最明显的感受。",
            state,
        )

        self.assertIn("先", reply)
        self.assertTrue(any(marker in reply for marker in ["写", "离开", "放下", "暂停"]))
        self.assertNotIn("你可以继续说", reply)

    def test_low_risk_support_reply_gets_one_open_question_when_missing(self):
        from app.services.agent_service import AgentService

        service = AgentService()
        reply = service._repair_reply_quality(
            "今天心里有点乱",
            "我听见了，我们先把这份感觉放慢一点。",
            {"risk_level": "low", "agent_mode": "support"},
        )

        self.assertTrue(any(marker in reply for marker in ["如果你想多说一点", "如果愿意", "慢慢说"]))
        self.assertGreater(len(reply), len("我听见了，我们先把这份感觉放慢一点。"))

    def test_knowledge_response_suppresses_hidden_assessment_prompt(self):
        import asyncio
        from app.services.agent_service import AgentService

        async def run():
            service = AgentService()
            with patch.object(
                service,
                "_route_with_deadline",
                return_value=("经期头晕可能和疼痛、睡眠、出血量变化有关。以上仅供参考。", "knowledge"),
            ):
                return await service.get_response(
                    user_id=1,
                    session_id="knowledge-no-probe",
                    user_message="经期为什么会头晕？",
                    context={"conversation_memory": {"conversation_messages": []}},
                    agent_mode="knowledge",
                )

        response = asyncio.run(run())

        self.assertTrue(response.get("suppress_assessment_prompt"))
        self.assertEqual(response["intent"], "knowledge")

    def test_frontend_failure_copy_does_not_expose_template_failure(self):
        chat_view = (BACKEND_ROOT.parent / "frontend" / "src" / "views" / "Chat.vue").read_text(encoding="utf-8")

        self.assertNotIn("刚才没有顺利接上完整回复", chat_view)
        self.assertNotIn("刚才没有顺利接上。你可以直接继续说一句", chat_view)

    def test_frontend_hides_waiting_indicator_after_first_stream_token(self):
        chat_view = (BACKEND_ROOT.parent / "frontend" / "src" / "views" / "Chat.vue").read_text(encoding="utf-8")

        self.assertIn("hasAssistantStarted", chat_view)
        self.assertIn("splitDisplayToken", chat_view)
        self.assertIn("hasAssistantStarted.value = true", chat_view)
        self.assertIn("const isBusy", chat_view)


class AssessmentTimingTests(unittest.TestCase):
    def test_generic_first_distress_does_not_trigger_menstrual_probe(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        from app.database import Base
        from app.models.assessment import AssessmentObservation, AssessmentSession  # noqa: F401
        from app.models.auth import EmailVerificationCode  # noqa: F401
        from app.models.biometric import BiometricData  # noqa: F401
        from app.models.chat_memory import ChatMemory  # noqa: F401
        from app.models.conversation import Conversation  # noqa: F401
        from app.models.menstrual import MenstrualRecord  # noqa: F401
        from app.models.mood import MoodDiary  # noqa: F401
        from app.models.music import Music  # noqa: F401
        from app.models.user import User  # noqa: F401
        from app.services.assessment_service import AssessmentOrchestrator

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        try:
            result = AssessmentOrchestrator(db).prepare_turn(
                user_id=1,
                chat_session_id="generic-first-distress",
                user_message="我有点难受",
                context={"sentiment_score": -0.8, "risk_level": "medium"},
            )
        finally:
            db.close()

        self.assertIsNone(result.assessment_prompt_hint)


class RouterKnowledgeQuestionTests(unittest.TestCase):
    """测试 _looks_like_knowledge_question 函数的优化功能"""
    
    def test_why_plus_physiological_phenomenon_recognized(self):
        """测试'为什么'+生理现象关键词组合的识别"""
        from app.agents.router import Router
        router = Router()
        
        # 测试各种生理/心理现象
        test_cases = [
            "为什么会烦躁？",
            "为什么会失眠",
            "为什么会头痛呢？",
            "为什么会腹痛",
            "为什么会疲劳",
            "为什么会乳房胀痛",
            "为什么会头晕",
            "为什么会想吐",
            "为什么会情绪低落",
            "为什么会脾气暴躁",
            "为什么会没精神",
            "为什么会发胖",
        ]
        
        for test_case in test_cases:
            with self.subTest(test_case=test_case):
                self.assertTrue(router._looks_like_knowledge_question(test_case))
    
    def test_normal_patterns_recognized(self):
        """测试'正常吗'等模式的识别"""
        from app.agents.router import Router
        router = Router()
        
        # 测试各种"正常吗"变体
        test_cases = [
            "这正常吗？",
            "这正常嘛",
            "这正常么？",
            "正常吗",
            "这样正常吗",
            "这样正常嘛？",
        ]
        
        for test_case in test_cases:
            with self.subTest(test_case=test_case):
                self.assertTrue(router._looks_like_knowledge_question(test_case))
    
    def test_normal_with_health_context_recognized(self):
        """测试'正常吗'+健康上下文的识别（较长句子也能识别）"""
        from app.agents.router import Router
        router = Router()
        
        test_cases = [
            "经前乳房胀痛正常吗？",
            "经期头痛正常嘛？",
            "姨妈推迟一周正常么？",
            "月经量多正常吗？",
            "最近特别烦躁正常吗？",
            "经前脾气暴躁正常吗？",
        ]
        
        for test_case in test_cases:
            with self.subTest(test_case=test_case):
                self.assertTrue(router._looks_like_knowledge_question(test_case))
    
    def test_extended_health_context_markers(self):
        """测试扩展的健康上下文标记词"""
        from app.agents.router import Router
        router = Router()
        
        test_cases = [
            "经期胸痛怎么办？",
            "腰酸怎么缓解？",
            "恶心想吐正常吗？",
            "心慌心悸是怎么回事？",
            "潮热盗汗正常吗？",
            "抽筋痉挛怎么办？",
            "腹胀便秘怎么改善？",
            "尿频尿急正常吗？",
            "量少发黑正常吗？",
            "提前好多天正常吗？",
        ]
        
        for test_case in test_cases:
            with self.subTest(test_case=test_case):
                self.assertTrue(router._looks_like_knowledge_question(test_case))
    
    def test_pms_pmdd_questions_recognized(self):
        """测试PMS/PMDD相关问题的识别"""
        from app.agents.router import Router
        router = Router()
        
        test_cases = [
            "PMS是什么？",
            "什么是PMDD？",
            "PMS怎么缓解？",
            "PMDD正常吗？",
        ]
        
        for test_case in test_cases:
            with self.subTest(test_case=test_case):
                self.assertTrue(router._looks_like_knowledge_question(test_case))
    
    def test_non_knowledge_questions_not_recognized(self):
        """测试非知识问题不应被误识别"""
        from app.agents.router import Router
        router = Router()
        
        test_cases = [
            "我今天心情不好",
            "我有点难受",
            "我想倾诉",
            "我不开心",
            "我很烦",
            "男朋友和我吵架了",
            "工作压力好大",
        ]
        
        for test_case in test_cases:
            with self.subTest(test_case=test_case):
                self.assertFalse(router._looks_like_knowledge_question(test_case))


if __name__ == "__main__":
    unittest.main()
