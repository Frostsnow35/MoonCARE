"""
语义缓存服务 - 使用 Redis Stack 实现向量相似度查询
"""
import asyncio
import hashlib
import json
import time
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timedelta

import redis
from redis.commands.search.field import VectorField, TextField, NumericField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType

from app.config import settings

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False
    SentenceTransformer = None


class SemanticCacheService:
    """
    基于 Redis Stack 的语义缓存服务
    支持向量相似度查询和缓存管理
    """

    def __init__(self):
        self.redis_client = None
        self.embedding_model = None
        self.index_name = "chat_cache_idx"
        self.vector_dim = 384  # all-MiniLM-L6-v2 输出维度
        self._init_redis()
        self._init_embedding_model()
        self._ensure_index()

    def _init_redis(self):
        """初始化 Redis 连接"""
        try:
            redis_url = settings.REDIS_URL
            
            self.redis_client = redis.Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=float(settings.REDIS_SOCKET_TIMEOUT),
                socket_connect_timeout=float(settings.REDIS_CONNECTION_TIMEOUT),
                retry_on_timeout=True,
            )
            # 测试连接
            self.redis_client.ping()
            print("[SemanticCacheService] Redis connection established")
        except Exception as e:
            print(f"[SemanticCacheService] Failed to connect to Redis: {e}")
            self.redis_client = None

    def _init_embedding_model(self):
        """初始化嵌入模型"""
        if not self.redis_client:
            return

        if not EMBEDDING_AVAILABLE:
            print("[SemanticCacheService] sentence_transformers not available")
            return
        
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("[SemanticCacheService] Embedding model loaded")
        except Exception as e:
            print(f"[SemanticCacheService] Failed to load embedding model: {e}")
            self.embedding_model = None

    def _ensure_index(self):
        """确保 Redis 搜索索引存在"""
        if not self.redis_client:
            return
        
        try:
            # 检查索引是否存在
            self.redis_client.ft(self.index_name).info()
            print(f"[SemanticCacheService] Index {self.index_name} already exists")
        except redis.exceptions.ResponseError:
            # 创建索引
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
                    }
                ),
                NumericField("created_at"),
                NumericField("expire_at"),
            )
            definition = IndexDefinition(prefix=["chat_cache:"], index_type=IndexType.HASH)
            self.redis_client.ft(self.index_name).create_index(schema, definition=definition)
            print(f"[SemanticCacheService] Index {self.index_name} created")

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """生成文本的向量嵌入"""
        if not self.embedding_model:
            return None
        
        try:
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            print(f"[SemanticCacheService] Failed to generate embedding: {e}")
            return None

    def _generate_cache_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(text.encode()).hexdigest()

    def _get_expire_at(self, ttl_hours: int = 24) -> float:
        """获取过期时间戳"""
        return (datetime.now() + timedelta(hours=ttl_hours)).timestamp()

    def get_cached_response(
        self,
        query: str,
        similarity_threshold: float = 0.85,
        max_results: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """
        查询语义缓存
        返回最相似的缓存响应，如果相似度超过阈值
        """
        if not self.redis_client or not self.embedding_model:
            return None

        try:
            # 生成查询向量
            query_embedding = self._generate_embedding(query)
            if not query_embedding:
                return None

            # 构建向量查询
            query_str = f"*=>[KNN {max_results} @embedding $vec AS score]"
            
            # 执行查询
            results = self.redis_client.ft(self.index_name).search(
                query_str,
                query_params={"vec": query_embedding},
                sort_by="score",
                limit=max_results,
            )

            # 检查结果
            for doc in results.docs:
                score = float(doc.score)
                similarity = 1 - score  # 转换为相似度（COSINE距离越小越相似）
                
                if similarity >= similarity_threshold:
                    # 检查是否过期
                    expire_at = float(doc.expire_at)
                    if time.time() < expire_at:
                        return {
                            "response": doc.response,
                            "similarity": similarity,
                            "cached_at": datetime.fromtimestamp(float(doc.created_at)),
                            "expire_at": datetime.fromtimestamp(expire_at),
                        }
            
            return None

        except Exception as e:
            print(f"[SemanticCacheService] Cache lookup error: {e}")
            return None

    def set_cached_response(
        self,
        query: str,
        response: str,
        ttl_hours: int = 24,
    ) -> bool:
        """
        将响应缓存到 Redis
        """
        if not self.redis_client or not self.embedding_model:
            return False

        try:
            # 生成嵌入
            embedding = self._generate_embedding(query)
            if not embedding:
                return False

            # 生成缓存键
            cache_key = self._generate_cache_key(query)
            redis_key = f"chat_cache:{cache_key}"

            # 存储数据
            data = {
                "query": query,
                "response": response,
                "embedding": json.dumps(embedding),
                "created_at": time.time(),
                "expire_at": self._get_expire_at(ttl_hours),
            }

            self.redis_client.hset(redis_key, mapping=data)
            
            # 设置 TTL（双重保障）
            self.redis_client.expire(redis_key, ttl_hours * 3600)
            
            print(f"[SemanticCacheService] Cached response for key: {cache_key}")
            return True

        except Exception as e:
            print(f"[SemanticCacheService] Cache set error: {e}")
            return False

    def delete_cache(self, query: str) -> bool:
        """删除指定查询的缓存"""
        if not self.redis_client:
            return False

        try:
            cache_key = self._generate_cache_key(query)
            redis_key = f"chat_cache:{cache_key}"
            result = self.redis_client.delete(redis_key)
            return result > 0
        except Exception as e:
            print(f"[SemanticCacheService] Cache delete error: {e}")
            return False

    def clear_expired_cache(self) -> int:
        """清理过期缓存"""
        if not self.redis_client:
            return 0

        try:
            count = 0
            current_time = time.time()
            
            # 扫描所有缓存键
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

        except Exception as e:
            print(f"[SemanticCacheService] Cache cleanup error: {e}")
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        if not self.redis_client:
            return {"available": False}

        try:
            # 获取索引信息
            info = self.redis_client.ft(self.index_name).info()
            
            # 统计缓存键数量
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
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
            }


# 单例实例
_semantic_cache_singleton: Optional[SemanticCacheService] = None


def get_semantic_cache() -> SemanticCacheService:
    """获取语义缓存服务单例"""
    global _semantic_cache_singleton
    if _semantic_cache_singleton is None:
        _semantic_cache_singleton = SemanticCacheService()
    return _semantic_cache_singleton
