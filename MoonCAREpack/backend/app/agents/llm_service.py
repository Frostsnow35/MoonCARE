import asyncio
import logging
import os
import re
import time
from typing import Optional, Dict, Any, List, AsyncGenerator, Iterator

import httpx

from app.config import settings
from app.utils.prompt_loader import render_prompt

try:
    from openai import OpenAI, AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None
    AsyncOpenAI = None


_NVIDIA_MODEL_ALIASES = {
    "glm-5.1": "z-ai/glm-5.1",
    "glm5.1": "z-ai/glm-5.1",
    "z-ai/glm5.1": "z-ai/glm-5.1",
}

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed. Please install with: pip install openai")
        
        # Get LLM provider from environment or config
        llm_provider = os.getenv("LLM_PROVIDER", settings.LLM_PROVIDER).lower().strip()
        self.provider = llm_provider
        
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

        elif llm_provider in {"zai", "zhipu", "bigmodel", "glm"}:
            api_key = self._first_nonempty(
                os.getenv("ZAI_API_KEY"),
                os.getenv("ZHIPUAI_API_KEY"),
                os.getenv("BIGMODEL_API_KEY"),
                os.getenv("GLM_API_KEY"),
                settings.ZAI_API_KEY,
            )
            if not api_key:
                raise ValueError(
                    "ZAI_API_KEY must be set for LLM_PROVIDER=zai when using glm-5.1."
                )
            base_url = self._normalize_base_url(
                os.getenv("ZAI_BASE_URL", settings.ZAI_BASE_URL)
            )
            self.model = os.getenv("ZAI_MODEL_NAME", settings.ZAI_MODEL_NAME)
            print(f"[LLMService] Using Z.AI GLM endpoint with model: {self.model}")
            
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
            self.model = self._normalize_nvidia_model_name(
                os.getenv("NVIDIA_MODEL_NAME", settings.NVIDIA_MODEL_NAME)
            )
            print(f"[LLMService] Using NVIDIA API with model: {self.model}")
            
        else:
            raise ValueError(
                f"Unknown LLM_PROVIDER: {llm_provider}. Must be one of: "
                "nvidia, openai, vllm, accelerated, zai"
            )

        self.http2_enabled = self._should_enable_http2(llm_provider)
        self.http_client = self._build_http_client(async_mode=False)
        self.async_http_client = self._build_http_client(async_mode=True)

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=settings.LLM_REQUEST_TIMEOUT_SECONDS,
            max_retries=settings.LLM_MAX_RETRIES,
            http_client=self.http_client,
        )
        
        if AsyncOpenAI:
            self.async_client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=settings.LLM_REQUEST_TIMEOUT_SECONDS,
                max_retries=settings.LLM_MAX_RETRIES,
                http_client=self.async_http_client,
            )
        else:
            self.async_client = None

    def _should_enable_http2(self, llm_provider: str) -> bool:
        """Return whether HTTP/2 should be used for the selected provider."""
        if not bool(settings.HTTP2_ENABLED):
            return False
        # NVIDIA Integrate currently answers basic HTTPS and streaming requests, but the
        # OpenAI SDK over HTTP/2 can fail the streaming connection on this endpoint.
        # Keep pooled keep-alive clients, but use HTTP/1.1 for this provider.
        return llm_provider != "nvidia"

    def _build_http_client(self, async_mode: bool) -> httpx.Client | httpx.AsyncClient:
        """Create a reusable HTTPX client for OpenAI-compatible model gateways."""
        max_connections = max(int(settings.MAX_CONCURRENT_CONNECTIONS), 1)
        max_keepalive = max(int(settings.CONNECTION_POOL_SIZE), 0) if settings.KEEP_ALIVE_ENABLED else 0
        timeout = httpx.Timeout(
            timeout=float(settings.LLM_REQUEST_TIMEOUT_SECONDS),
            connect=float(settings.LLM_CONNECT_TIMEOUT_SECONDS),
            write=float(settings.LLM_WRITE_TIMEOUT_SECONDS),
            pool=float(settings.LLM_POOL_TIMEOUT_SECONDS),
        )
        limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=min(max_keepalive, max_connections),
            keepalive_expiry=float(settings.KEEP_ALIVE_TIMEOUT_SECONDS) if settings.KEEP_ALIVE_ENABLED else 0.0,
        )
        client_class = httpx.AsyncClient if async_mode else httpx.Client
        return client_class(
            http2=bool(self.http2_enabled),
            timeout=timeout,
            limits=limits,
            trust_env=bool(settings.LLM_TRUST_ENV_PROXY),
        )

    async def aclose(self) -> None:
        """Close pooled async HTTP resources during explicit service shutdown."""
        if getattr(self, "async_http_client", None):
            await self.async_http_client.aclose()

    def close(self) -> None:
        """Close pooled sync HTTP resources during explicit service shutdown."""
        if getattr(self, "http_client", None):
            self.http_client.close()

    def _normalize_openai_compatible_base_url(self, base_url: Optional[str]) -> Optional[str]:
        if not base_url:
            return None
        normalized = base_url.strip().rstrip("/")
        if normalized.endswith("/v1"):
            return normalized
        return f"{normalized}/v1"

    def _normalize_base_url(self, base_url: Optional[str]) -> Optional[str]:
        """Normalize provider base URLs that are already complete API roots."""
        if not base_url:
            return None
        return base_url.strip().rstrip("/")

    def _first_nonempty(self, *values: Optional[str]) -> Optional[str]:
        """Return the first non-empty string from environment/config aliases."""
        for value in values:
            if value and str(value).strip():
                return str(value).strip()
        return None

    def _normalize_nvidia_model_name(self, model_name: str) -> str:
        """Map friendly NVIDIA catalog names to the exact Integrate model id."""
        normalized = (model_name or "").strip()
        return _NVIDIA_MODEL_ALIASES.get(normalized.lower(), normalized)

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
        
        # 清理多余的空格
        text = re.sub(r'\s+', ' ', text).strip()
        
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
            max_tokens=settings.MAX_RESPONSE_TOKENS,
        )

        text = response.choices[0].message.content or ""
        text = self._clean_response(text)

        if not text:
            return "我在这里。你可以说一点，再跟我说现在最难忍受的那一部分。"

        return text

    def streaming_generate_reply(
        self, 
        user_message: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Iterator[Dict[str, Any]]:
        """Stream reply tokens with first-token latency tracking."""
        context = context or {}
        first_token_received = False
        start_time = time.perf_counter()
        first_token_latency_ms = 0

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

        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.85,
                max_tokens=settings.MAX_RESPONSE_TOKENS,
                stream=True,
            )

            for chunk in stream:
                choices = getattr(chunk, "choices", None) or []
                if not choices:
                    continue
                delta = getattr(choices[0], "delta", None)
                content = getattr(delta, "content", None) or ""
                
                if content:
                    is_first = not first_token_received
                    if is_first:
                        first_token_received = True
                        first_token_latency_ms = int((time.perf_counter() - start_time) * 1000)
                    
                    yield {
                        "token": content,
                        "is_first": is_first,
                        "first_token_latency_ms": first_token_latency_ms,
                    }

        except Exception as e:
            yield {
                "token": "",
                "is_first": False,
                "first_token_latency_ms": 0,
                "error": str(e),
            }

    async def async_streaming_generate_reply(
        self, 
        user_message: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Async stream reply tokens with first-token latency tracking."""
        context = context or {}
        first_token_received = False
        start_time = time.perf_counter()
        first_token_latency_ms = 0

        if not self.async_client:
            raise RuntimeError("AsyncOpenAI client not available")

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

        try:
            stream = await self.async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.85,
                max_tokens=settings.MAX_RESPONSE_TOKENS,
                stream=True,
            )

            iterator = stream.__aiter__()
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        iterator.__anext__(),
                        timeout=(
                            float(settings.FIRST_TOKEN_TIMEOUT_SECONDS)
                            if not first_token_received
                            else float(settings.LLM_REQUEST_TIMEOUT_SECONDS)
                        ),
                    )
                except StopAsyncIteration:
                    break
                except asyncio.TimeoutError:
                    yield {
                        "token": "",
                        "is_first": False,
                        "first_token_latency_ms": int((time.perf_counter() - start_time) * 1000),
                        "error": "first_token_timeout" if not first_token_received else "stream_timeout",
                    }
                    return

                choices = getattr(chunk, "choices", None) or []
                if not choices:
                    continue
                delta = getattr(choices[0], "delta", None)
                content = getattr(delta, "content", None) or ""
                
                if content:
                    is_first = not first_token_received
                    if is_first:
                        first_token_received = True
                        first_token_latency_ms = int((time.perf_counter() - start_time) * 1000)
                    
                    yield {
                        "token": content,
                        "is_first": is_first,
                        "first_token_latency_ms": first_token_latency_ms,
                    }

        except Exception as e:
            logger.warning("Async streaming LLM request failed: %s", e)
            yield {
                "token": "",
                "is_first": False,
                "first_token_latency_ms": 0,
                "error": str(e),
            }

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
