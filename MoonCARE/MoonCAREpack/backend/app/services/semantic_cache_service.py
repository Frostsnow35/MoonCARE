import os
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class DummySemanticCache:
    """空缓存，避免任何 Redis 依赖"""
    def get(self, *args, **kwargs):
        return None
    def set(self, *args, **kwargs):
        pass
    def get_cached_response(self, *args, **kwargs) -> None:
        """Match AgentService cache lookup API when Redis is unavailable."""
        return None
    def set_cached_response(self, *args, **kwargs) -> None:
        """Match AgentService cache write API as a no-op."""
        return None
    def clear(self, *args, **kwargs):
        pass
    def get_cache_stats(self) -> Dict[str, Any]:
        return {"enabled": False, "message": "Semantic cache disabled"}

_semantic_cache = None

def get_semantic_cache():
    global _semantic_cache
    if _semantic_cache is not None:
        return _semantic_cache

    enabled = os.getenv("SEMANTIC_CACHE_ENABLED", "false").lower() == "true"
    if not enabled:
        logger.info("Semantic cache disabled by environment variable")
        _semantic_cache = DummySemanticCache()
        return _semantic_cache

    # 如果启用，尝试导入真实 Redis 模块（但这里不强制）
    try:
        from redis import Redis
        from redis.commands.search.indexDefinition import IndexDefinition, IndexType
        # 这里可以初始化真实连接，但既然你不需要，直接走 dummy
        logger.warning("Redis enabled but not fully configured, using dummy cache")
        _semantic_cache = DummySemanticCache()
    except ImportError:
        logger.warning("Redis modules not installed, using dummy cache")
        _semantic_cache = DummySemanticCache()
    
    return _semantic_cache
