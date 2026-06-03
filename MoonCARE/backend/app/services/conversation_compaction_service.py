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
        self.max_total_tokens = int(settings.MAX_PROMPT_TOKENS)
        self.system_prompt_tokens = int(settings.SYSTEM_PROMPT_TOKENS)
        self.max_response_tokens = int(settings.MAX_RESPONSE_TOKENS)
        self.user_message_tokens = 256
        self.recent_turns = max(int(getattr(settings, "CHAT_CONTEXT_RECENT_TURNS", 20)), 1)
        self.max_total_turns = max(int(getattr(settings, "CHAT_CONTEXT_MAX_TURNS", 30)), self.recent_turns)
        
        # 分层记忆配置
        self.layer_config = {
            "recent": {
                "turns": self.recent_turns,
                "max_tokens": 2048,
                "priority": 1.0,
            },
            "middle": {
                "turns": max(self.max_total_turns - self.recent_turns - 1, 0),
                "max_tokens": 1024,
                "priority": 0.7,
                "compression_ratio": 0.5,
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
        if not bool(getattr(settings, "CONVERSATION_COMPACTION_USE_TIKTOKEN", False)):
            self.token_encoder = None
            return
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

        conversation_history = [
            msg for msg in conversation_history
            if isinstance(msg, dict) and msg.get("role") in {"user", "assistant"} and msg.get("content")
        ]

        # 计算原始 Token 数
        for msg in conversation_history:
            stats["original_tokens"] += self.count_tokens(msg.get("content", ""))

        if not conversation_history:
            return [], stats

        recent_turns = conversation_history[-self.recent_turns:]
        older_turns = conversation_history[:-self.recent_turns]
        compressed_messages: List[Dict[str, str]] = []

        key_points = self.extract_key_points(conversation_history)
        if key_points:
            key_info = "；".join(key_points[:6])
            compressed_messages.append({
                "role": "system",
                "content": f"【关键信息】{key_info}",
            })
            stats["layers_used"].append("key_info")

        if older_turns:
            older_summary = self.create_summary(older_turns)
            if older_summary:
                compressed_messages.append({
                    "role": "system",
                    "content": f"【历史摘要】{older_summary}",
                })
                stats["layers_used"].append("long_term")

        compressed_messages.extend(
            {
                "role": msg["role"],
                "content": self.truncate_message(
                    msg.get("content", ""),
                    max(32, int(self.layer_config["recent"]["max_tokens"] / max(len(recent_turns), 1))),
                ),
            }
            for msg in recent_turns
        )
        stats["layers_used"].append("recent")

        if len(compressed_messages) > self.max_total_turns:
            system_messages = [msg for msg in compressed_messages if msg["role"] == "system"]
            non_system_messages = [msg for msg in compressed_messages if msg["role"] != "system"]
            remaining = max(self.max_total_turns - len(system_messages), 0)
            compressed_messages = system_messages + non_system_messages[-remaining:]

        stats["compressed_turns"] = len(compressed_messages)
        stats["compressed_tokens"] = sum(self.count_tokens(msg.get("content", "")) for msg in compressed_messages)

        stats["compression_ratio"] = 1 - (stats["compressed_tokens"] / stats["original_tokens"]) if stats["original_tokens"] > 0 else 0
        
        return compressed_messages, stats

    def extract_key_points(self, conversation_history: List[Dict[str, str]]) -> List[str]:
        """从对话历史中提取关键点"""
        key_points = []
        seen = set()

        def add_point(point: str) -> None:
            if point and point not in seen:
                seen.add(point)
                key_points.append(point)
        
        for msg in conversation_history:
            content = msg.get("content", "")
            role = msg.get("role", "")
            
            # 提取用户提到的重要信息
            if role == "user":
                # 检测情绪表达
                emotion_keywords = ["难过", "开心", "烦躁", "焦虑", "疲惫", "想哭", "生气"]
                for keyword in emotion_keywords:
                    if keyword in content:
                        add_point(f"用户表达了{keyword}的情绪")
                        break
                
                # 检测经前相关内容
                pms_keywords = ["经前", "月经", "姨妈", "周期", "PMS", "痛经"]
                if any(keyword in content for keyword in pms_keywords):
                    add_point("用户提到经前相关话题")

                # 检测用户已尝试过的照护方式，避免下一轮重复给泛建议
                if any(keyword in content for keyword in ["试过", "已经试了", "还是", "也试了", "之前试过"]):
                    coping_methods = []
                    coping_mapping = {
                        "热敷": ["热敷", "热水袋"],
                        "早点躺下": ["早点躺下", "躺一会儿"],
                        "休息": ["休息"],
                        "喝温水": ["温水", "热水"],
                        "散步": ["散步", "走一走"],
                        "拉伸": ["拉伸", "伸展"],
                    }
                    for label, keywords in coping_mapping.items():
                        if any(keyword in content for keyword in keywords):
                            coping_methods.append(label)
                    if coping_methods:
                        add_point(f"用户已尝试：{'、'.join(coping_methods[:3])}")

                # 检测用户此刻最想得到什么，优先保留最新目标
                goal_markers = ["我现在更想", "我更想", "我想知道", "怎么办", "怎么做", "上班前", "接下来"]
                if any(marker in content for marker in goal_markers):
                    add_point(f"当前诉求：{content[:36]}")
                
                # 检测需求表达
                need_keywords = ["需要", "想要", "希望", "想"]
                if any(keyword in content for keyword in need_keywords):
                    add_point(f"用户表达了需求：{content[:30]}")
        
        return key_points[:10]

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
