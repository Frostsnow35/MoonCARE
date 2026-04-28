import os
import re
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

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
        nvidia_api_key = os.getenv("NVIDIA_API_KEY")
        nvidia_base_url = os.getenv("NVIDIA_BASE_URL")
        nvidia_model = os.getenv("NVIDIA_MODEL_NAME")

        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_base_url = os.getenv("OPENAI_BASE_URL")
        openai_model = os.getenv("MODEL_NAME", "MiniMax-M2.7")

        use_nvidia = any([nvidia_api_key, nvidia_base_url, nvidia_model])

        if use_nvidia:
            api_key = nvidia_api_key or openai_api_key
            base_url = self._normalize_openai_compatible_base_url(nvidia_base_url or openai_base_url)
            self.model = nvidia_model or "mistralai/mistral-large"
        else:
            api_key = openai_api_key
            base_url = openai_base_url
            self.model = openai_model

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
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
        # Remove think tags
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I)

        # 去掉一些常见"思维暴露"前缀
        noisy_prefixes = [
            r"^思考过程[:：]\s*",
            r"^推理过程[:：]\s*",
            r"^分析[:：]\s*",
        ]
        for pattern in noisy_prefixes:
            text = re.sub(pattern, "", text, flags=re.I)

        return text.strip()

    def generate_reply(self, user_message: str, context: Optional[Dict[str, Any]] = None) -> str:
        context = context or {}

        # 优先使用外部传入的人设 prompt
        if context.get("raw_system_prompt"):
            system_prompt = context["raw_system_prompt"]
        else:
            cycle_phase = context.get("cycle_phase", "未知")
            risk_level = context.get("risk_level", "low")

            system_prompt = f"""
你是"她语 MoonCARE"的温柔情绪陪伴助手。

当前用户状态：
- 周期阶段：{cycle_phase}
- 风险等级：{risk_level}

回答要求：
1. 温柔，自然、口语化。
2. 不要说教，不要像客服。
3. 尽量控制在 2~4 句。
4. 先接住情绪，再轻轻回应。
5. 不要输出思维过程，不要出现 think 标签。
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
        )

        text = response.choices[0].message.content or ""
        text = self._clean_response(text)

        if not text:
            return "我在这里。你可以慢一点，再跟我说说现在最难受的那一部分。"

        return text
