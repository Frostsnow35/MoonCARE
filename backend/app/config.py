from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_ROOT / ".env", override=True)


class Settings(BaseSettings):
    APP_NAME: str = "HealthAI - 智能情绪管理平台"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./healthai.db"

    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    API_V1_PREFIX: str = "/api/v1"

    # LLM Provider selection: "nvidia", "openai", "vllm", "accelerated", "zai"
    LLM_PROVIDER: str = "nvidia"

    NVIDIA_API_KEY: Optional[str] = None
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL_NAME: str = "meta/llama-3.2-3b-instruct"

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    MODEL_NAME: str = "gpt-3.5-turbo"

    # vLLM local inference (OpenAI-compatible API)
    VLLM_BASE_URL: str = "http://localhost:8000/v1"
    VLLM_API_KEY: str = "vllm-local"
    VLLM_MODEL_NAME: str = "meta/llama-3.2-3b-instruct"
    VLLM_HOST: str = "0.0.0.0"
    VLLM_PORT: int = 8000
    VLLM_GPU_MEMORY_UTILIZATION: float = 0.9
    VLLM_TENSOR_PARALLEL_SIZE: int = 1
    VLLM_DTYPE: str = "auto"

    # Generic OpenAI-compatible acceleration engine endpoint.
    # Can point to vLLM, SGLang, LMDeploy, or an internal GLM-compatible gateway.
    ACCELERATED_LLM_BASE_URL: str = "http://localhost:30000/v1"
    ACCELERATED_LLM_API_KEY: str = "accelerated-local"
    ACCELERATED_LLM_MODEL_NAME: str = "glm-5.1"
    ACCELERATED_LLM_ENGINE: str = "openai-compatible"

    # Z.AI / Zhipu GLM endpoint. Z.AI uses an OpenAI-compatible SDK surface,
    # but the base URL is /api/paas/v4 instead of /v1.
    ZAI_API_KEY: Optional[str] = None
    ZAI_BASE_URL: str = "https://api.z.ai/api/paas/v4/"
    ZAI_MODEL_NAME: str = "glm-5.1"

    # Chat latency controls. Keep the model and prompts unchanged, but bound user wait time.
    LLM_REQUEST_TIMEOUT_SECONDS: float = 18.0
    CHAT_AGENT_REPLY_TIMEOUT_SECONDS: float = 18.0

    SQLITE_JOURNAL_MODE: str = "TRUNCATE"
    SQLITE_BUSY_TIMEOUT_SECONDS: float = 30.0

    PMS_RISK_HIGH_THRESHOLD: float = 0.7
    PMS_RISK_CRITICAL_THRESHOLD: float = 0.8

    CYCLE_PREDICTION_MIN_HISTORY: int = 2
    CYCLE_PREDICTION_ERROR_RANGE: int = 2

    NLP_CONFIDENCE_THRESHOLD: float = 0.6
    CONTEXT_WINDOW_SIZE: int = 10

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
