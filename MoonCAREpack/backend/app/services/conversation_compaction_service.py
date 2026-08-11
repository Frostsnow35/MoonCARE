"""
对话历史压缩服务 - 实现分层记忆和动态截断
"""
import asyncio
import json
import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    tiktoken = None

from app.config import settings


class ConversationCompactionService:
    """
    对话历史压缩服务
    实现分层记忆、摘要生成和动态截断策略
    """

    def __init__(self):
        self.token_encoder = None
        self._init_token_encoder()
        
        # 配置参数
        self.max_total_tokens = 4096
        self.system_prompt_tokens = 1024
        self.max_response_tokens = 512
        self.user_message_tokens = 256
        
        # 分层记忆配置
        self.layer_config = {
            "recent": {
                "turns": 8,
                "max_tokens": 1024,
                "priority": 1.0,
            },
            "middle": {
                "turns": 10,
                "max_tokens": 1536,
                "priority": 0.7,
                "compression_ratio": 0.6,
            },
            "long_term": {
                "turns": 10,
                "max_tokens": 1024,
                "priority": 0.3,
                "compression_ratio": 0.3,
            },
        }

    def _init_token_encoder(self):
        """初始化 Token 编码器"""
        if not TIKTOKEN_AVAILABLE:
            print("[ConversationCompactionService] tiktoken not available")
            return
        
        try:
            self.token_encoder = tiktoken.get_encoding("cl100k_base")
            print("[ConversationCompactionService] Token encoder loaded")
        except Exception as e:
            print(f"[ConversationCompactionService] Failed to load token encoder: {e}")
            self.token_encoder = None

    def count_tokens(self, text: str) -> int:
        """计算文本的 Token 数量"""
        if not self.token_encoder:
            # 回退方案：按字符数估算
            return int(len(text) / 4)
        
        return len(self.token_encoder.encode(text))

    def truncate_message(self, text: str, max_tokens: int) -> str:
        """截断消息到指定 Token 数"""
        if not self.token_encoder:
            # 回退方案
            max_chars = max_tokens * 4
            if len(text) <= max_chars:
                return text
            return text[:max_chars - 3] + "..."
        
        tokens = self.token_encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text
        
        truncated_tokens = tokens[:max_tokens - 10]
        truncated_text = self.token_encoder.decode(truncated_tokens)
        return truncated_text.strip() + "..."

    def compress_message(self, text: str, compression_ratio: float) -> str:
        """按压缩比例压缩消息"""
        if compression_ratio >= 1.0:
            return text
        
        target_length = int(len(text) * compression_ratio)
        if target_length < 10:
            target_length = 10
        
        # 简单压缩策略：保留关键信息
        sentences = re.split(r'[。！？\n]+', text)
        if len(sentences) <= 1:
            return text[:target_length] + "..." if len(text) > target_length else text
        
        # 保留首尾句子
        compressed = []
        total_length = 0
        
        # 添加开头句子
        for sentence in sentences[:2]:
            if total_length + len(sentence) <= target_length:
                compressed.append(sentence)
                total_length += len(sentence)
        
        # 添加结尾句子
        for sentence in reversed(sentences[-2:]):
            if total_length + len(sentence) <= target_length:
                compressed.insert(0, sentence)
                total_length += len(sentence)
        
        return "。".join(compressed) + "。"

    def build_compacted_context(
        self,
        conversation_history: List[Dict[str, str]],
        user_message: str,
    ) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        """
        构建压缩后的对话上下文
        返回压缩后的消息列表和统计信息
        """
        stats = {
            "original_turns": len(conversation_history),
            "original_tokens": 0,
            "compressed_turns": 0,
            "compressed_tokens": 0,
            "layers_used": [],
        }

        # 计算原始 Token 数
        for msg in conversation_history:
            stats["original_tokens"] += self.count_tokens(msg.get("content", ""))

        # 计算可用 Token 数
        available_tokens = self.max_total_tokens - \
            self.system_prompt_tokens - \
            self.max_response_tokens - \
            self.count_tokens(user_message)
        
        if available_tokens <= 0:
            available_tokens = 512

        # 分层压缩
        compressed_messages = []
        remaining_tokens = available_tokens
        
        # 最近对话层（高优先级，保留完整）
        recent_turns = conversation_history[-self.layer_config["recent"]["turns"]:]
        recent_tokens = sum(self.count_tokens(msg.get("content", "")) for msg in recent_turns)
        
        if recent_tokens <= remaining_tokens:
            compressed_messages.extend(recent_turns)
            remaining_tokens -= recent_tokens
            stats["layers_used"].append("recent")
            stats["compressed_turns"] += len(recent_turns)
            stats["compressed_tokens"] += recent_tokens
        else:
            # 需要截断最近对话
            for msg in reversed(recent_turns):
                content = msg.get("content", "")
                max_tokens_for_msg = int(remaining_tokens / len(recent_turns))
                if max_tokens_for_msg > 0:
                    truncated = self.truncate_message(content, max_tokens_for_msg)
                    compressed_messages.insert(0, {"role": msg["role"], "content": truncated})
                    stats["compressed_tokens"] += max_tokens_for_msg
                    remaining_tokens -= max_tokens_for_msg
                    stats["compressed_turns"] += 1
            stats["layers_used"].append("recent_truncated")

        # 中间对话层（中等优先级，部分压缩）
        if remaining_tokens > 0:
            middle_start = max(0, len(conversation_history) - 
                              self.layer_config["recent"]["turns"] - 
                              self.layer_config["middle"]["turns"])
            middle_end = len(conversation_history) - self.layer_config["recent"]["turns"]
            middle_turns = conversation_history[middle_start:middle_end]
            
            if middle_turns:
                compression_ratio = self.layer_config["middle"]["compression_ratio"]
                max_middle_tokens = min(
                    remaining_tokens,
                    self.layer_config["middle"]["max_tokens"]
                )
                
                for msg in middle_turns:
                    if max_middle_tokens <= 0:
                        break
                    
                    content = msg.get("content", "")
                    compressed = self.compress_message(content, compression_ratio)
                    compressed_tokens = self.count_tokens(compressed)
                    
                    if compressed_tokens <= max_middle_tokens:
                        compressed_messages.insert(0, {"role": msg["role"], "content": compressed})
                        max_middle_tokens -= compressed_tokens
                        remaining_tokens -= compressed_tokens
                        stats["compressed_turns"] += 1
                        stats["compressed_tokens"] += compressed_tokens
                
                stats["layers_used"].append("middle")

        # 长期记忆层（低优先级，高度压缩）
        if remaining_tokens > 0:
            long_term_turns = conversation_history[:middle_start]
            
            if long_term_turns:
                compression_ratio = self.layer_config["long_term"]["compression_ratio"]
                max_long_term_tokens = min(
                    remaining_tokens,
                    self.layer_config["long_term"]["max_tokens"]
                )
                
                # 只保留关键信息
                key_points = []
                for msg in long_term_turns:
                    content = msg.get("content", "")
                    # 提取关键点（简单规则）
                    if len(content) > 20:
                        key_points.append(content[:30] + "...")
                
                if key_points:
                    summary = "；".join(key_points[:5])
                    summary_tokens = self.count_tokens(summary)
                    
                    if summary_tokens <= max_long_term_tokens:
                        compressed_messages.insert(0, {
                            "role": "system",
                            "content": f"【历史摘要】{summary}"
                        })
                        stats["compressed_turns"] += 1
                        stats["compressed_tokens"] += summary_tokens
                        stats["layers_used"].append("long_term")

        stats["compression_ratio"] = 1 - (stats["compressed_tokens"] / stats["original_tokens"]) if stats["original_tokens"] > 0 else 0
        
        return compressed_messages, stats

    def extract_key_points(self, conversation_history: List[Dict[str, str]]) -> List[str]:
        """从对话历史中提取关键点"""
        key_points = []
        
        for msg in conversation_history:
            content = msg.get("content", "")
            role = msg.get("role", "")
            
            # 提取用户提到的重要信息
            if role == "user":
                # 检测情绪表达
                emotion_keywords = ["难过", "开心", "烦躁", "焦虑", "疲惫", "想哭", "生气"]
                for keyword in emotion_keywords:
                    if keyword in content:
                        key_points.append(f"用户表达了{keyword}的情绪")
                        break
                
                # 检测经前相关内容
                pms_keywords = ["经前", "月经", "姨妈", "周期", "PMS", "痛经"]
                if any(keyword in content for keyword in pms_keywords):
                    key_points.append("用户提到经前相关话题")
                
                # 检测需求表达
                need_keywords = ["需要", "想要", "希望", "想"]
                if any(keyword in content for keyword in need_keywords):
                    key_points.append(f"用户表达了需求：{content[:30]}")
        
        return list(set(key_points))[:10]  # 去重并限制数量

    def create_summary(self, conversation_history: List[Dict[str, str]]) -> str:
        """生成对话历史摘要"""
        if not conversation_history:
            return "暂无对话历史"
        
        key_points = self.extract_key_points(conversation_history)
        
        if key_points:
            return "；".join(key_points)
        
        # 如果没有关键点，生成简单摘要
        last_user_msg = None
        last_assistant_msg = None
        
        for msg in reversed(conversation_history):
            if msg.get("role") == "user" and not last_user_msg:
                last_user_msg = msg.get("content", "")
            elif msg.get("role") == "assistant" and not last_assistant_msg:
                last_assistant_msg = msg.get("content", "")
            
            if last_user_msg and last_assistant_msg:
                break
        
        summary_parts = []
        if last_user_msg:
            summary_parts.append(f"用户提到：{last_user_msg[:20]}")
        if last_assistant_msg:
            summary_parts.append(f"助理回应：{last_assistant_msg[:20]}")
        
        return "；".join(summary_parts) if summary_parts else "对话进行中"


# 单例实例
_compaction_singleton: Optional[ConversationCompactionService] = None


def get_conversation_compaction_service() -> ConversationCompactionService:
    """获取对话压缩服务单例"""
    global _compaction_singleton
    if _compaction_singleton is None:
        _compaction_singleton = ConversationCompactionService()
    return _compaction_singleton