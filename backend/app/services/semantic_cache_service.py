import logging
import os
import re
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from app.config import settings
from app.utils.safety import contains_crisis_signal


logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    """Read a boolean env var while allowing Settings to provide the default."""
    raw = os.getenv(name)
    if raw is None:
        return bool(default)
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    """Read an int env var while keeping a safe default on invalid input."""
    raw = os.getenv(name)
    if raw is None:
        return int(default)
    try:
        return int(raw.strip())
    except ValueError:
        logger.warning("Invalid integer for %s; using default", name)
        return int(default)


SAFE_SEMANTIC_CACHE_WARMUP_ENTRIES: tuple[Dict[str, Any], ...] = (
    {
        "message": "经前有点烦躁怎么办",
        "response": "我听见你现在有些烦躁。可以先把期待降到一个小步骤，喝点水、慢慢呼吸几轮；这些建议仅供参考，如果不适持续或明显加重，建议咨询专业人士。",
        "context": {"intent": "support", "risk_level": "low", "detected_emotion": "烦躁"},
        "intent": "support",
    },
    {
        "message": "快来月经了情绪低落",
        "response": "这种低落感可能和压力、睡眠、周期变化一起出现。我们先不急着下结论，可以记录今天的情绪和身体感受；仅供参考，如果持续影响生活，建议寻求专业支持。",
        "context": {"intent": "support", "risk_level": "low", "detected_emotion": "低落"},
        "intent": "support",
    },
    {
        "message": "经期肚子疼可以怎么缓解",
        "response": "可以先尝试热敷、补水、休息和轻柔伸展。这里的建议仅供参考，不替代医生判断；如果疼痛很剧烈、伴随异常出血或发热，建议及时就医。",
        "context": {"intent": "knowledge", "risk_level": "low", "detected_emotion": "身体不适"},
        "intent": "knowledge",
    },
)


class DummySemanticCache:
    """No-op cache used when semantic caching is disabled."""

    def get(self, *args, **kwargs):
        return None

    def set(self, *args, **kwargs):
        return None

    def get_cached_response(self, *args, **kwargs) -> None:
        """Match AgentService cache lookup API when caching is unavailable."""
        return None

    def set_cached_response(self, *args, **kwargs) -> None:
        """Match AgentService cache write API as a no-op."""
        return None

    def clear(self, *args, **kwargs):
        return None

    def get_cache_stats(self) -> Dict[str, Any]:
        return {"enabled": False, "message": "Semantic cache disabled"}


@dataclass
class _CacheEntry:
    response: str
    context: Dict[str, Any]
    intent: str
    timestamp: float
    namespace: str
    access_count: int = 0


class LocalSemanticCache:
    """Bounded local semantic cache with exact, phrase, and intent matching."""

    def __init__(
        self,
        max_size: int = 1000,
        ttl_hours: int = 24,
        similarity_threshold: float = 0.85,
        namespace: str = "chat-agent-v1",
    ):
        self.max_size = max(int(max_size), 1)
        self.ttl_seconds = max(float(ttl_hours), 0.0) * 3600
        self.similarity_threshold = float(similarity_threshold)
        self.namespace = str(namespace or "chat-agent-v1")
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._warmup_count = 0
        self._stats = {
            "hits": 0,
            "misses": 0,
            "writes": 0,
            "skips": 0,
            "evictions": 0,
        }

    def get_cached_response(
        self,
        user_message: str,
        similarity_threshold: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return a safe cached response using exact, phrase, then intent matching."""
        self._purge_expired()
        query_key = self._normalize(user_message)
        if not query_key or contains_crisis_signal(user_message):
            self._stats["misses"] += 1
            return None

        threshold = (
            float(similarity_threshold)
            if similarity_threshold is not None
            else self.similarity_threshold
        )
        context = context or {}

        entry = self._cache.get(query_key)
        if entry is not None:
            if self._entry_safe(entry) and self._context_similar(context, entry.context, strict=False):
                self._touch(query_key, entry)
                self._stats["hits"] += 1
                return self._result(query_key, entry, 1.0, "exact")
            self._stats["misses"] += 1
            return None

        query_tokens = self._tokenize(user_message)
        best_key = ""
        best_entry: Optional[_CacheEntry] = None
        best_similarity = 0.0
        for key, candidate in list(self._cache.items()):
            if not self._entry_safe(candidate):
                continue
            if not self._context_similar(context, candidate.context, strict=False):
                continue
            similarity = self._calculate_similarity(query_tokens, self._tokenize(key))
            if similarity > best_similarity:
                best_key = key
                best_entry = candidate
                best_similarity = similarity

        if best_entry is not None and best_similarity >= threshold:
            self._touch(best_key, best_entry)
            self._stats["hits"] += 1
            return self._result(best_key, best_entry, best_similarity, "phrase")

        query_intent = str(context.get("intent") or "").strip()
        if query_intent:
            for key, candidate in list(self._cache.items()):
                if candidate.intent != query_intent:
                    continue
                if not self._entry_safe(candidate):
                    continue
                if self._context_similar(context, candidate.context, strict=True):
                    self._touch(key, candidate)
                    self._stats["hits"] += 1
                    return self._result(key, candidate, 0.5, "intent")

        self._stats["misses"] += 1
        return None

    def set_cached_response(
        self,
        user_message: str,
        response: str,
        ttl_hours: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        intent: Optional[str] = None,
    ) -> None:
        """Store one response unless it contains sensitive or crisis content."""
        if contains_crisis_signal(user_message) or contains_crisis_signal(response):
            self._stats["skips"] += 1
            return None

        key = self._normalize(user_message)
        value = " ".join((response or "").split())
        if not key or not value:
            self._stats["skips"] += 1
            return None

        if ttl_hours is not None:
            self.ttl_seconds = max(float(ttl_hours), 0.0) * 3600

        context = dict(context or {})
        entry_intent = str(intent or context.get("intent") or "").strip()
        self._cache[key] = _CacheEntry(
            response=value,
            context=context,
            intent=entry_intent,
            timestamp=time.time(),
            namespace=self.namespace,
        )
        self._cache.move_to_end(key)
        self._stats["writes"] += 1
        self._evict_if_needed()
        return None

    def warmup(self, entries: Iterable[Dict[str, Any]], limit: Optional[int] = None) -> int:
        """Load safe seed entries without caching crisis or empty content."""
        warmed = 0
        max_entries = None if limit is None or int(limit) <= 0 else int(limit)

        for entry in entries:
            if max_entries is not None and warmed >= max_entries:
                break

            message = str(entry.get("message") or entry.get("user_message") or "")
            response = str(entry.get("response") or "")
            if contains_crisis_signal(message) or contains_crisis_signal(response):
                continue

            context = dict(entry.get("context") or {})
            intent = str(entry.get("intent") or context.get("intent") or "").strip()
            self.set_cached_response(
                message,
                response,
                context=context,
                intent=intent,
            )
            if self._normalize(message) in self._cache:
                warmed += 1

        self._warmup_count += warmed
        return warmed

    def clear(self) -> None:
        self._cache.clear()
        self._warmup_count = 0
        for key in self._stats:
            self._stats[key] = 0

    def get_cache_stats(self) -> Dict[str, Any]:
        self._purge_expired()
        return {
            "enabled": True,
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "similarity_threshold": self.similarity_threshold,
            "namespace": self.namespace,
            "warmup_count": self._warmup_count,
            **self._stats,
        }

    def _normalize(self, text: str) -> str:
        normalized = re.sub(r"\s+", "", (text or "").strip().lower())
        return re.sub(r"[，。！？!?、,.；;：:\-_\[\]（）()\"'`~]", "", normalized)

    def _tokenize(self, text: str) -> list[str]:
        normalized = self._normalize(text)
        if not normalized:
            return []

        tokens = re.findall(r"[a-z0-9_]{2,}", normalized)
        domain_terms = [
            "经前",
            "经期",
            "月经",
            "姨妈",
            "痛经",
            "头晕",
            "睡不着",
            "焦虑",
            "烦躁",
            "低落",
            "难过",
            "想哭",
            "疲惫",
            "压力",
            "男朋友",
            "吵架",
        ]
        tokens.extend(term for term in domain_terms if term in normalized)
        if len(normalized) >= 2:
            tokens.extend(normalized[index : index + 2] for index in range(len(normalized) - 1))
        if len(normalized) >= 3:
            tokens.extend(normalized[index : index + 3] for index in range(len(normalized) - 2))
        return list(dict.fromkeys(tokens))

    def _calculate_similarity(self, tokens1: list[str], tokens2: list[str]) -> float:
        set1 = set(tokens1)
        set2 = set(tokens2)
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        jaccard = intersection / union if union else 0.0
        overlap = intersection / min(len(set1), len(set2))
        return max(jaccard, overlap)

    def _context_similar(
        self,
        current_context: Dict[str, Any],
        cached_context: Dict[str, Any],
        strict: bool,
    ) -> bool:
        current_risk = current_context.get("risk_level")
        cached_risk = cached_context.get("risk_level")
        if current_risk in {"high", "crisis"} or cached_risk in {"high", "crisis"}:
            return False

        current_intent = current_context.get("intent")
        cached_intent = cached_context.get("intent")
        if strict and current_intent and cached_intent and current_intent != cached_intent:
            return False

        emotion_keys = ("detected_emotion", "emotion_detected", "emotion", "dominant_emotion")
        current_emotion = self._first_context_value(current_context, emotion_keys)
        cached_emotion = self._first_context_value(cached_context, emotion_keys)
        if current_emotion and cached_emotion and current_emotion != cached_emotion:
            return False
        if strict:
            return bool(current_intent and cached_intent and current_intent == cached_intent)
        return True

    def _first_context_value(self, context: Dict[str, Any], keys: tuple[str, ...]) -> str:
        for key in keys:
            value = context.get(key)
            if value:
                return str(value)
        return ""

    def _entry_safe(self, entry: _CacheEntry) -> bool:
        return (
            bool(entry.response)
            and entry.namespace == self.namespace
            and not contains_crisis_signal(entry.response)
        )

    def _touch(self, key: str, entry: _CacheEntry) -> None:
        entry.access_count += 1
        self._cache.move_to_end(key)

    def _result(
        self,
        key: str,
        entry: _CacheEntry,
        similarity: float,
        match_type: str,
    ) -> Dict[str, Any]:
        return {
            "response": entry.response,
            "context": entry.context,
            "intent": entry.intent,
            "similarity": round(float(similarity), 4),
            "match_type": match_type,
            "cache_key": key,
            "access_count": entry.access_count,
        }

    def _expired(self, entry: _CacheEntry) -> bool:
        if self.ttl_seconds <= 0:
            return True
        return (time.time() - entry.timestamp) > self.ttl_seconds

    def _purge_expired(self) -> None:
        for key, entry in list(self._cache.items()):
            if self._expired(entry):
                self._cache.pop(key, None)

    def _evict_if_needed(self) -> None:
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)
            self._stats["evictions"] += 1


_semantic_cache: Optional[Any] = None


def get_semantic_cache():
    """Return the configured semantic cache implementation."""
    global _semantic_cache
    if _semantic_cache is not None:
        return _semantic_cache

    enabled = _env_bool("SEMANTIC_CACHE_ENABLED", settings.SEMANTIC_CACHE_ENABLED)
    if not enabled:
        logger.info("Semantic cache disabled by configuration")
        _semantic_cache = DummySemanticCache()
        return _semantic_cache

    _semantic_cache = LocalSemanticCache(
        max_size=getattr(settings, "SEMANTIC_CACHE_MAX_SIZE", 1000),
        ttl_hours=settings.SEMANTIC_CACHE_TTL_HOURS,
        similarity_threshold=settings.SEMANTIC_CACHE_SIMILARITY_THRESHOLD,
        namespace=os.getenv("SEMANTIC_CACHE_NAMESPACE", getattr(settings, "SEMANTIC_CACHE_NAMESPACE", "chat-agent-v1")),
    )
    warmup_enabled = _env_bool(
        "SEMANTIC_CACHE_WARMUP_ENABLED",
        getattr(settings, "SEMANTIC_CACHE_WARMUP_ENABLED", False),
    )
    if warmup_enabled:
        warmup_limit = _env_int(
            "SEMANTIC_CACHE_WARMUP_ITEMS",
            getattr(settings, "SEMANTIC_CACHE_WARMUP_ITEMS", len(SAFE_SEMANTIC_CACHE_WARMUP_ENTRIES)),
        )
        warmed = _semantic_cache.warmup(SAFE_SEMANTIC_CACHE_WARMUP_ENTRIES, limit=warmup_limit)
        logger.info("Local semantic cache warmed with %s safe entries", warmed)

    logger.info("Local semantic cache enabled with max_size=%s", _semantic_cache.max_size)
    return _semantic_cache
