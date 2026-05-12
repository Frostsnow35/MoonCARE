import os
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from app.config import settings
from app.utils.prompt_loader import render_prompt

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_ROOT / ".env", override=True)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None


class LLMService:
    def __init__(self):
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed. Please install with: pip install openai")
        
        nvidia_api_key = os.getenv("NVIDIA_API_KEY", "").strip()
        nvidia_base_url = os.getenv("NVIDIA_BASE_URL", "").strip()
        nvidia_model = os.getenv("NVIDIA_MODEL_NAME", "").strip()

        openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        openai_base_url = os.getenv("OPENAI_BASE_URL", "").strip()
        openai_model = os.getenv("MODEL_NAME", "gpt-3.5-turbo")

        use_nvidia = bool(nvidia_api_key)       

        if use_nvidia:
            api_key = nvidia_api_key
            base_url = self._normalize_openai_compatible_base_url(nvidia_base_url or settings.NVIDIA_BASE_URL)
            self.model = nvidia_model or settings.NVIDIA_MODEL_NAME
            print(f"[LLMService] Using NVIDIA API with model: {self.model}")
        else:
            if not openai_api_key:
                raise ValueError("Either NVIDIA_API_KEY or OPENAI_API_KEY must be set in .env")
            api_key = openai_api_key
            base_url = openai_base_url or settings.OPENAI_BASE_URL
            self.model = openai_model
            print(f"[LLMService] Using OpenAI API with model: {self.model}")

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=35.0,
        )

    def _normalize_openai_compatible_base_url(self, base_url: Optional[str]) -> Optional[str]:
        if not base_url:
            return None
        normalized = base_url.strip().rstrip("/")
        if normalized.endswith("/v1"):
            return normalized
        return f"{normalized}/v1"

    def _clean_response(self, text: str) -> str:
        if not text:
            return ""

        # Remove hidden reasoning and model/control tags before showing text.
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I)
        text = re.sub(r"</?think>", "", text, flags=re.I)
        text = re.sub(r"\b_chatting_\b", "", text, flags=re.I)

        prefix_pattern = (
            r"^\s*(?:"
            r"assistant|Assistant|AI|MoonCARE|"
            r"情绪宝宝|守护宝宝|知识宝宝|她语|"
            r"一句话回应|简单的解释|解释|回答|回应|回复|Note|注意"
            r")\s*[：:]\s*"
        )

        previous = None
        while previous != text:
            previous = text
            text = re.sub(prefix_pattern, "", text, flags=re.M | re.I)
            text = re.sub(r"^\s*\d+[.、]\s*", "", text, flags=re.M)
            text = re.sub(r"^\s*[-*•]\s*", "", text, flags=re.M)
            text = text.strip()

        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    def generate_reply(self, user_message: str, context: Optional[Dict[str, Any]] = None) -> str:
        context = context or {}

        if context.get("raw_system_prompt"):
            system_prompt = context["raw_system_prompt"]
        else:
            cycle_phase = context.get("cycle_phase", "未知")
            risk_level = context.get("risk_level", "low")

            system_prompt = render_prompt(
                "default_chat_prompt.txt",
                cycle_phase=cycle_phase,
                risk_level=risk_level,
                memory_context=context.get("memory_context", "暂无可用长期记忆。"),
                recent_context=context.get("recent_context", "暂无最近对话。"),
                retrieved_context=context.get("retrieved_context", "暂无检索片段。"),
                mode_guidance=context.get("mode_guidance", ""),
            )

        messages = self._build_messages(system_prompt, user_message, context)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.85,
            max_tokens=320,
        )

        text = response.choices[0].message.content or ""
        text = self._clean_response(text)

        if not text:
            return "我在这里。你可以说一点，再跟我说现在最难忍受的那一部分。"

        return text

    def _build_messages(
        self,
        system_prompt: str,
        user_message: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """Build chat-completion messages with bounded prior conversation turns."""
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        for item in context.get("conversation_messages") or []:
            role = item.get("role")
            content = self._truncate_message(item.get("content", ""))
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_message})
        return messages

    def _truncate_message(self, text: str, limit: int = 500) -> str:
        """Bound historical message length before sending it to the model."""
        normalized = " ".join((text or "").split())
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[: limit - 1]}…"
