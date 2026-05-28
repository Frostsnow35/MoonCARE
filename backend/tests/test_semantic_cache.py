import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


class LocalSemanticCacheTests(unittest.TestCase):
    def test_exact_match_returns_cached_response_with_similarity_one(self):
        from app.services.semantic_cache_service import LocalSemanticCache

        cache = LocalSemanticCache(max_size=3, ttl_hours=1, similarity_threshold=0.85)
        cache.set_cached_response(
            "我今天有点烦躁",
            "我听见了，这份烦躁是真的不好受。",
            context={"intent": "support", "detected_emotion": "烦躁"},
            intent="support",
        )

        hit = cache.get_cached_response(
            "我今天有点烦躁",
            context={"intent": "support", "detected_emotion": "烦躁"},
        )

        self.assertIsNotNone(hit)
        self.assertEqual(hit["response"], "我听见了，这份烦躁是真的不好受。")
        self.assertEqual(hit["match_type"], "exact")
        self.assertEqual(hit["similarity"], 1.0)

    def test_phrase_similarity_match_uses_configurable_threshold(self):
        from app.services.semantic_cache_service import LocalSemanticCache

        cache = LocalSemanticCache(max_size=3, ttl_hours=1, similarity_threshold=0.35)
        cache.set_cached_response(
            "我最近焦虑睡不着",
            "先把手机放远一点，陪自己慢慢呼吸几次。",
            context={"intent": "support", "detected_emotion": "焦虑"},
            intent="support",
        )

        hit = cache.get_cached_response(
            "焦虑到睡不着",
            similarity_threshold=0.35,
            context={"intent": "support", "detected_emotion": "焦虑"},
        )

        self.assertIsNotNone(hit)
        self.assertEqual(hit["match_type"], "phrase")
        self.assertGreaterEqual(hit["similarity"], 0.35)

    def test_intent_match_requires_similar_context(self):
        from app.services.semantic_cache_service import LocalSemanticCache

        cache = LocalSemanticCache(max_size=3, ttl_hours=1, similarity_threshold=0.95)
        cache.set_cached_response(
            "我有点累",
            "先允许自己休息一会儿。",
            context={"intent": "support", "detected_emotion": "疲惫"},
            intent="support",
        )

        hit = cache.get_cached_response(
            "今天不知道怎么开口",
            similarity_threshold=0.95,
            context={"intent": "support", "detected_emotion": "疲惫"},
        )
        miss = cache.get_cached_response(
            "经期为什么会头晕",
            similarity_threshold=0.95,
            context={"intent": "knowledge", "detected_emotion": "疲惫"},
        )

        self.assertIsNotNone(hit)
        self.assertEqual(hit["match_type"], "intent")
        self.assertIsNone(miss)

    def test_ttl_expiry_and_lru_eviction_are_enforced(self):
        from app.services.semantic_cache_service import LocalSemanticCache

        expired = LocalSemanticCache(max_size=3, ttl_hours=0, similarity_threshold=0.85)
        expired.set_cached_response("会过期的问题", "过期回复")
        time.sleep(0.001)
        self.assertIsNone(expired.get_cached_response("会过期的问题"))

        cache = LocalSemanticCache(max_size=2, ttl_hours=1, similarity_threshold=0.85)
        cache.set_cached_response("第一条", "reply-1")
        cache.set_cached_response("第二条", "reply-2")
        self.assertIsNotNone(cache.get_cached_response("第一条"))
        cache.set_cached_response("第三条", "reply-3")

        self.assertIsNotNone(cache.get_cached_response("第一条"))
        self.assertIsNone(cache.get_cached_response("第二条"))
        self.assertIsNotNone(cache.get_cached_response("第三条"))

    def test_get_semantic_cache_uses_settings_when_env_is_absent(self):
        from app.services import semantic_cache_service as cache_module

        cache_module._semantic_cache = None
        try:
            with patch.object(cache_module.settings, "SEMANTIC_CACHE_ENABLED", True):
                with patch.object(cache_module.settings, "SEMANTIC_CACHE_MAX_SIZE", 8):
                    with patch.dict("os.environ", {}, clear=True):
                        cache = cache_module.get_semantic_cache()
        finally:
            cache_module._semantic_cache = None

        self.assertEqual(cache.get_cache_stats()["enabled"], True)
        self.assertEqual(cache.get_cache_stats()["max_size"], 8)

    def test_warmup_loads_safe_entries_and_skips_crisis_content(self):
        from app.services.semantic_cache_service import LocalSemanticCache

        cache = LocalSemanticCache(max_size=5, ttl_hours=1, similarity_threshold=0.85)

        warmed = cache.warmup(
            [
                {
                    "message": "cycle irritability support",
                    "response": "I am here with you. This is for reference only.",
                    "context": {"intent": "support", "risk_level": "low"},
                    "intent": "support",
                },
                {
                    "message": "I want to kill myself",
                    "response": "unsafe cache entry",
                    "context": {"intent": "support", "risk_level": "crisis"},
                    "intent": "support",
                },
            ]
        )

        self.assertEqual(warmed, 1)
        self.assertEqual(cache.get_cache_stats()["warmup_count"], 1)
        self.assertIsNotNone(
            cache.get_cached_response(
                "cycle irritability support",
                context={"intent": "support", "risk_level": "low"},
            )
        )
        self.assertIsNone(
            cache.get_cached_response(
                "I want to kill myself",
                context={"intent": "support", "risk_level": "crisis"},
            )
        )

    def test_get_semantic_cache_warmup_respects_config(self):
        from app.services import semantic_cache_service as cache_module

        cache_module._semantic_cache = None
        try:
            with patch.object(cache_module.settings, "SEMANTIC_CACHE_ENABLED", True):
                with patch.object(cache_module.settings, "SEMANTIC_CACHE_WARMUP_ENABLED", True, create=True):
                    with patch.object(cache_module.settings, "SEMANTIC_CACHE_WARMUP_ITEMS", 1, create=True):
                        with patch.dict("os.environ", {}, clear=True):
                            cache = cache_module.get_semantic_cache()
        finally:
            cache_module._semantic_cache = None

        stats = cache.get_cache_stats()
        self.assertEqual(stats["enabled"], True)
        self.assertEqual(stats["warmup_count"], 1)

    def test_cache_stats_track_hits_misses_writes_and_evictions(self):
        from app.services.semantic_cache_service import LocalSemanticCache

        cache = LocalSemanticCache(max_size=1, ttl_hours=1, similarity_threshold=0.85)
        cache.set_cached_response("first cache question", "first response")
        self.assertIsNotNone(cache.get_cached_response("first cache question"))
        self.assertIsNone(cache.get_cached_response("missing cache question"))
        cache.set_cached_response("second cache question", "second response")

        stats = cache.get_cache_stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["writes"], 2)
        self.assertEqual(stats["evictions"], 1)

    def test_cache_namespace_prevents_stale_template_hits(self):
        from app.services.semantic_cache_service import LocalSemanticCache

        cache = LocalSemanticCache(max_size=3, ttl_hours=1, namespace="template-v1")
        cache.set_cached_response("same user message", "old template response")

        cache.namespace = "template-v2"

        self.assertIsNone(cache.get_cached_response("same user message"))
        self.assertEqual(cache.get_cache_stats()["namespace"], "template-v2")


if __name__ == "__main__":
    unittest.main()
