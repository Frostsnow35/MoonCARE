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
        
        # Get LLM provider from environment or config
        llm_provider = os.getenv("LLM_PROVIDER", settings.LLM_PROVIDER).lower().strip()
        
        if llm_provider == "vllm":
            api_key = os.getenv("VLLM_API_KEY", settings.VLLM_API_KEY)
            base_url = self._normalize_openai_compatible_base_url(
                os.getenv("VLLM_BASE_URL", settings.VLLM_BASE_URL)
            )
            self.model = os.getenv("VLLM_MODEL_NAME", settings.VLLM_MODEL_NAME)
            print(f"[LLMService] Using vLLM local inference with model: {self.model}")

        elif llm_provider == "accelerated":
            api_key = os.getenv("ACCELERATED_LLM_API_KEY", settings.ACCELERATED_LLM_API_KEY)
            base_url = self._normalize_openai_compatible_base_url(
                os.getenv("ACCELERATED_LLM_BASE_URL", settings.ACCELERATED_LLM_BASE_URL)
            )
            self.model = os.getenv("ACCELERATED_LLM_MODEL_NAME", settings.ACCELERATED_LLM_MODEL_NAME)
            engine = os.getenv("ACCELERATED_LLM_ENGINE", settings.ACCELERATED_LLM_ENGINE)
            print(f"[LLMService] Using accelerated OpenAI-compatible engine ({engine}) with model: {self.model}")
            
        elif llm_provider == "openai":
            openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY must be set in .env for OpenAI provider")
            api_key = openai_api_key
            base_url = os.getenv("OPENAI_BASE_URL", settings.OPENAI_BASE_URL)
            self.model = os.getenv("MODEL_NAME", settings.MODEL_NAME)
            print(f"[LLMService] Using OpenAI API with model: {self.model}")
            
        elif llm_provider == "nvidia":
            nvidia_api_key = os.getenv("NVIDIA_API_KEY", "").strip()
            if not nvidia_api_key:
                raise ValueError("NVIDIA_API_KEY must be set in .env for NVIDIA provider")
            api_key = nvidia_api_key
            base_url = self._normalize_openai_compatible_base_url(
                os.getenv("NVIDIA_BASE_URL", settings.NVIDIA_BASE_URL)
            )
            self.model = os.getenv("NVIDIA_MODEL_NAME", settings.NVIDIA_MODEL_NAME)
            print(f"[LLMService] Using NVIDIA API with model: {self.model}")
            
        else:
            raise ValueError(f"Unknown LLM_PROVIDER: {llm_provider}. Must be one of: nvidia, openai, vllm, accelerated")

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=settings.LLM_REQUEST_TIMEOUT_SECONDS,
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

      # Remove all role prefixes and format markers
        prefix_pattern = (
            r"^\s*(?:"
            r"assistant|Assistant|AI|MoonCARE|"
            r"情绪宝宝|守护宝宝|知识宝宝|她语|懂懂宝宝|"
            r"一句话回应|简单的解释|解释|回答|回应|回复|Note|注意|"
            r"比如|例如|假设|如果|对话范例|示范|"
            r"用户|你|我"
            r")\s*[：:]\s*"
        )

        # Remove lines that look like examples or instructions
        example_patterns = [
            r"^\s*(?:比如|例如|假设|如果|比如你|比如用户).*$",
            r"^\s*(?:第一句|第二句|第三句|第一步|第二步).*$",
            r"^\s*(?:像这样|这样说|应该说).*$",
            r"^\s*(?:对话范例|示范|示例).*$",
        ]

        previous = None
        while previous != text:
            previous = text
            text = re.sub(prefix_pattern, "", text, flags=re.M | re.I)
            text = re.sub(r"^\s*\d+[.、]\s*", "", text, flags=re.M)
            text = re.sub(r"^\s*[-*•]\s*", "", text, flags=re.M)
            
            # Remove example-like lines
            for pattern in example_patterns:
                text = re.sub(pattern, "", text, flags=re.M | re.I)
            
            text = text.strip()

        # Remove any remaining colon-prefixed lines
        text = re.sub(r"^\s*[^：:\n]+[：:]\s*", "", text, flags=re.M)
        
        # Remove multiple newlines
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
