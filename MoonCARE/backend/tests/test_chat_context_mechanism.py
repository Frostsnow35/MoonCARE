import json
import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


class ChatClientContextTests(unittest.TestCase):
    def test_parse_client_context_discards_current_user_duplicate(self):
        from app.api.v1.chat import _parse_client_context_messages

        messages = [
            {"role": "assistant", "content": "我在这里陪你。"},
            {"role": "user", "content": "我来月经了，身体不舒服"},
            {"role": "assistant", "content": "我接住这份不舒服。"},
            {"role": "user", "content": "我感觉真的很痛"},
        ]

        parsed = _parse_client_context_messages(
            json.dumps(messages, ensure_ascii=False),
            current_message="我感觉真的很痛",
        )

        self.assertEqual(parsed[-1]["role"], "assistant")
        self.assertNotIn({"role": "user", "content": "我感觉真的很痛"}, parsed)

    def test_merge_client_context_only_fills_missing_server_history(self):
        from app.api.v1.chat import _merge_client_context_into_memory

        memory = {
            "recent_context": "暂无最近对话。",
            "conversation_messages": [],
            "memory_state": {"has_memory": False},
        }
        client_messages = [
            {"role": "user", "content": "我来月经了，身体不舒服"},
            {"role": "assistant", "content": "我会在这里听着。"},
        ]

        merged = _merge_client_context_into_memory(memory, client_messages)

        self.assertEqual(merged["conversation_messages"], client_messages)
        self.assertIn("user: 我来月经了，身体不舒服", merged["recent_context"])
        self.assertTrue(merged["memory_state"]["client_context_used"])

        server_memory = {
            "recent_context": "user: 服务端已有记录",
            "conversation_messages": [{"role": "user", "content": "服务端已有记录"}],
            "memory_state": {},
        }
        unchanged = _merge_client_context_into_memory(server_memory, client_messages)

        self.assertEqual(unchanged["conversation_messages"], server_memory["conversation_messages"])
        self.assertFalse(unchanged["memory_state"]["client_context_used"])


class ConversationCompactionWindowTests(unittest.TestCase):
    def test_compaction_keeps_recent_20_turns_and_total_under_30(self):
        from app.services.conversation_compaction_service import ConversationCompactionService

        service = ConversationCompactionService()
        history = [
            {
                "role": "user" if index % 2 else "assistant",
                "content": f"第{index}轮内容，用户在持续补充经前情绪和身体状态。",
            }
            for index in range(1, 36)
        ]

        compacted, stats = service.build_compacted_context(history, "现在继续聊")

        compacted_text = "\n".join(item["content"] for item in compacted)
        for index in range(16, 36):
            self.assertIn(f"第{index}轮内容", compacted_text)
        self.assertLessEqual(len(compacted), 30)
        self.assertTrue(any(item["role"] == "system" and "历史摘要" in item["content"] for item in compacted))
        self.assertIn("recent", stats["layers_used"])

    def test_compaction_exposes_key_information_before_recent_turns(self):
        from app.services.conversation_compaction_service import ConversationCompactionService

        service = ConversationCompactionService()
        history = [
            {"role": "user", "content": "我最近焦虑，工作压力很大"},
            {"role": "assistant", "content": "我听见了。"},
        ] * 18

        compacted, _ = service.build_compacted_context(history, "我该怎么做")

        first = compacted[0]
        self.assertEqual(first["role"], "system")
        self.assertIn("关键信息", first["content"])
        self.assertIn("焦虑", first["content"])


    def test_agent_state_keeps_compaction_stats_with_compacted_messages(self):
        from app.services.agent_service import AgentService

        service = AgentService()
        history = [
            {
                "role": "user" if index % 2 else "assistant",
                "content": f"第{index}轮内容，用户提到经前压力和工作加班。",
            }
            for index in range(1, 34)
        ]
        context = {
            "conversation_memory": {
                "conversation_messages": history,
                "memory_state": {"has_memory": True},
            }
        }

        compacted_context = service._compact_conversation_context(context)
        state = service._attach_conversation_context(
            {"risk_level": "low"},
            compacted_context,
            "support",
        )

        self.assertIn("compaction_stats", state)
        self.assertLessEqual(len(state["conversation_messages"]), 30)
        self.assertEqual(state["conversation_messages"][0]["role"], "system")

    def test_compaction_prioritizes_recent_goal_and_attempted_coping(self):
        from app.services.conversation_compaction_service import ConversationCompactionService

        service = ConversationCompactionService()
        history = [
            {"role": "user", "content": "这两天经前特别烦躁，昨晚又没睡好"},
            {"role": "assistant", "content": "我在，先别硬撑。"},
            {"role": "user", "content": "我试过热敷和早点躺下，但还是会心里发紧"},
            {"role": "assistant", "content": "我记下了，热敷对你帮助有限。"},
            {"role": "user", "content": "我现在更想知道明天上班前怎么让自己稳一点"},
        ] * 8

        compacted, _ = service.build_compacted_context(history, "明天上班前我该怎么做")
        system_text = "\n".join(item["content"] for item in compacted if item["role"] == "system")

        self.assertIn("热敷", system_text)
        self.assertIn("上班前", system_text)
        self.assertIn("稳一点", system_text)


if __name__ == "__main__":
    unittest.main()
