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


if __name__ == "__main__":
    unittest.main()
