"""Optional Redis/RediSearch semantic cache service.

The main application must be able to start when semantic caching is disabled,
when the Redis Python package changes RediSearch import paths, or when the
server is plain Redis instead of Redis Stack.
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.config import settings

try:
    import redis
except ImportError as exc:
    redis = None
    REDIS_AVAILABLE = False
    REDIS_IMPORT_ERROR = exc
    RedisResponseError = Exception
else:
    REDIS_AVAILABLE = True
    REDIS_IMPORT_ERROR = None
    RedisResponseError = redis.exceptions.ResponseError

try:
    from redis.commands.search.field import NumericField, TextField, VectorField
    try:
        from redis.commands.search.indexDefinition import IndexDefinition, IndexType
    except ModuleNotFoundError:
        from redis.commands.search.index_definition import IndexDefinition, IndexType
    REDIS_SEARCH_AVAILABLE = True
    REDIS_SEARCH_IMPORT_ERROR = None
except Exception as exc:
    NumericField = TextField = VectorField = IndexDefinition = IndexType = None
    REDIS_SEARCH_AVAILABLE = False
    REDIS_SEARCH_IMPORT_ERROR = exc

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    EMBEDDING_AVAILABLE = False


class SemanticCacheService:
    """Best-effort semantic cache backed by Redis Stack vector search."""

    def __init__(self):
        self.redis_client = None
        self.embedding_model = None
        self.index_name = "chat_cache_idx"
        self.vector_dim = 384
        self._init_redis()
        self._init_embedding_model()
        self._ensure_index()

    def _init_redis(self) -> None:
        """Initialize Redis if the package and server are available."""
        if not REDIS_AVAILABLE:
            print(f"[SemanticCacheService] redis package not available: {REDIS_IMPORT_ERROR}")
            return

        try:
            self.redis_client = redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=float(settings.REDIS_SOCKET_TIMEOUT),
                socket_connect_timeout=float(settings.REDIS_CONNECTION_TIMEOUT),
                retry_on_timeout=True,
            )
            self.redis_client.ping()
            print("[SemanticCacheService] Redis connection established")
        except Exception as exc:
            print(f"[SemanticCacheService] Failed to connect to Redis: {exc}")
            self.redis_client = None

    def _init_embedding_model(self) -> None:
        """Initialize the embedding model only after Redis is available."""
        if not self.redis_client:
            return

        if not EMBEDDING_AVAILABLE:
            print("[SemanticCacheService] sentence_transformers not available")
            return

        try:
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            print("[SemanticCacheService] Embedding model loaded")
        except Exception as exc:
            print(f"[SemanticCacheService] Failed to load embedding model: {exc}")
            self.embedding_model = None

    def _ensure_index(self) -> None:
        """Create the RediSearch vector index when Redis Stack is available."""
        if not self.redis_client:
            return

        if not REDIS_SEARCH_AVAILABLE:
            print(
                "[SemanticCacheService] RediSearch client helpers not available: "
                f"{REDIS_SEARCH_IMPORT_ERROR}"
            )
            self.redis_client = None
            return

        try:
            self.redis_client.ft(self.index_name).info()
            print(f"[SemanticCacheService] Index {self.index_name} already exists")
        except RedisResponseError:
            try:
                schema = (
                    TextField("query", weight=1.0),
                    TextField("response", weight=1.0),
                    VectorField(
                        "embedding",
                        "FLAT",
                        {
                            "TYPE": "FLOAT32",
                            "DIM": self.vector_dim,
                            "DISTANCE_METRIC": "COSINE",
                        },
                    ),
                    NumericField("created_at"),
                    NumericField("expire_at"),
                )
                definition = IndexDefinition(prefix=["chat_cache:"], index_type=IndexType.HASH)
                self.redis_client.ft(self.index_name).create_index(schema, definition=definition)
                print(f"[SemanticCacheService] Index {self.index_name} created")
            except Exception as exc:
                print(f"[SemanticCacheService] RediSearch index unavailable: {exc}")
                self.redis_client = None
        except Exception as exc:
            print(f"[SemanticCacheService] RediSearch unavailable: {exc}")
            self.redis_client = None

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate an embedding for cache lookup or storage."""
        if not self.embedding_model:
            return None

        try:
            return self.embedding_model.encode(text).tolist()
        except Exception as exc:
            print(f"[SemanticCacheService] Failed to generate embedding: {exc}")
            return None

    def _generate_cache_key(self, text: str) -> str:
        """Return a deterministic cache key for the query text."""
        return hashlib.md5(text.encode()).hexdigest()

    def _get_expire_at(self, ttl_hours: int = 24) -> float:
        """Return the expiration timestamp."""
        return (datetime.now() + timedelta(hours=ttl_hours)).timestamp()

    def get_cached_response(
        self,
        query: str,
        similarity_threshold: float = 0.85,
        max_results: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """Return a cached semantic response when available."""
        if not self.redis_client or not self.embedding_model:
            return None

        try:
            query_embedding = self._generate_embedding(query)
            if not query_embedding:
                return None

            query_str = f"*=>[KNN {max_results} @embedding $vec AS score]"
            results = self.redis_client.ft(self.index_name).search(
                query_str,
                query_params={"vec": query_embedding},
                sort_by="score",
                limit=max_results,
            )

            for doc in results.docs:
                score = float(doc.score)
                similarity = 1 - score
                if similarity >= similarity_threshold:
                    expire_at = float(doc.expire_at)
                    if time.time() < expire_at:
                        return {
                            "response": doc.response,
                            "similarity": similarity,
                            "cached_at": datetime.fromtimestamp(float(doc.created_at)),
                            "expire_at": datetime.fromtimestamp(expire_at),
                        }
            return None
        except Exception as exc:
            print(f"[SemanticCacheService] Cache lookup error: {exc}")
            return None

    def set_cached_response(
        self,
        query: str,
        response: str,
        ttl_hours: int = 24,
    ) -> bool:
        """Store a semantic cache response when all optional pieces are available."""
        if not self.redis_client or not self.embedding_model:
            return False

        try:
            embedding = self._generate_embedding(query)
            if not embedding:
                return False

            cache_key = self._generate_cache_key(query)
            redis_key = f"chat_cache:{cache_key}"
            data = {
                "query": query,
                "response": response,
                "embedding": json.dumps(embedding),
                "created_at": time.time(),
                "expire_at": self._get_expire_at(ttl_hours),
            }
            self.redis_client.hset(redis_key, mapping=data)
            self.redis_client.expire(redis_key, ttl_hours * 3600)
            print(f"[SemanticCacheService] Cached response for key: {cache_key}")
            return True
        except Exception as exc:
            print(f"[SemanticCacheService] Cache set error: {exc}")
            return False

    def delete_cache(self, query: str) -> bool:
        """Delete a cached query response."""
        if not self.redis_client:
            return False

        try:
            cache_key = self._generate_cache_key(query)
            redis_key = f"chat_cache:{cache_key}"
            return self.redis_client.delete(redis_key) > 0
        except Exception as exc:
            print(f"[SemanticCacheService] Cache delete error: {exc}")
            return False

    def clear_expired_cache(self) -> int:
        """Clear expired cache entries and return the number deleted."""
        if not self.redis_client:
            return 0

        try:
            count = 0
            current_time = time.time()
            cursor = 0
            while True:
                cursor, keys = self.redis_client.scan(
                    cursor=cursor,
                    match="chat_cache:*",
                    count=100,
                )
                for key in keys:
                    expire_at = self.redis_client.hget(key, "expire_at")
                    if expire_at and float(expire_at) < current_time:
                        self.redis_client.delete(key)
                        count += 1
                if cursor == 0:
                    break

            print(f"[SemanticCacheService] Cleared {count} expired cache entries")
            return count
        except Exception as exc:
            print(f"[SemanticCacheService] Cache cleanup error: {exc}")
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Return cache availability and lightweight stats."""
        if not self.redis_client:
            return {"available": False}

        try:
            info = self.redis_client.ft(self.index_name).info()
            cursor = 0
            count = 0
            while True:
                cursor, keys = self.redis_client.scan(
                    cursor=cursor,
                    match="chat_cache:*",
                    count=100,
                )
                count += len(keys)
                if cursor == 0:
                    break

            return {
                "available": True,
                "index_name": self.index_name,
                "index_doc_count": info.get("num_docs", 0),
                "cache_entry_count": count,
            }
        except Exception as exc:
            return {"available": False, "error": str(exc)}


_semantic_cache_singleton: Optional[SemanticCacheService] = None


def get_semantic_cache() -> SemanticCacheService:
    """Return the semantic cache singleton."""
    global _semantic_cache_singleton
    if _semantic_cache_singleton is None:
        _semantic_cache_singleton = SemanticCacheService()
    return _semantic_cache_singleton
