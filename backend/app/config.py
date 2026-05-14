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
    NVIDIA_MODEL_NAME: str = "z-ai/glm-5.1"

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
    LLM_REQUEST_TIMEOUT_SECONDS: float = 45.0
    LLM_CONNECT_TIMEOUT_SECONDS: float = 10.0
    LLM_WRITE_TIMEOUT_SECONDS: float = 20.0
    LLM_POOL_TIMEOUT_SECONDS: float = 10.0
    CHAT_AGENT_REPLY_TIMEOUT_SECONDS: float = 45.0
    LLM_MAX_RETRIES: int = 0

    SQLITE_JOURNAL_MODE: str = "TRUNCATE"
    SQLITE_BUSY_TIMEOUT_SECONDS: float = 30.0

    PMS_RISK_HIGH_THRESHOLD: float = 0.7
    PMS_RISK_CRITICAL_THRESHOLD: float = 0.8

    CYCLE_PREDICTION_MIN_HISTORY: int = 2
    CYCLE_PREDICTION_ERROR_RANGE: int = 2

    NLP_CONFIDENCE_THRESHOLD: float = 0.6
    CONTEXT_WINDOW_SIZE: int = 10

    # Redis configuration for semantic caching
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_MAX_CONNECTIONS: int = 100
    REDIS_CONNECTION_TIMEOUT: float = 0.3
    REDIS_SOCKET_TIMEOUT: float = 0.5

    # Semantic cache configuration
    SEMANTIC_CACHE_ENABLED: bool = True
    SEMANTIC_CACHE_TTL_HOURS: int = 24
    SEMANTIC_CACHE_SIMILARITY_THRESHOLD: float = 0.85
    SEMANTIC_CACHE_MAX_RESULTS: int = 3

    # Awareness Local product memory. This is intended for local development
    # and demos; production needs a separate multi-user isolation review.
    AWARENESS_MEMORY_ENABLED: bool = True
    AWARENESS_BASE_URL: str = "http://localhost:37800"
    AWARENESS_MCP_PATH: str = "/mcp"
    AWARENESS_TIMEOUT_SECONDS: float = 3.0
    AWARENESS_RECALL_LIMIT: int = 5
    AWARENESS_SOURCE: str = "mooncare-backend"

    # HTTP/2 and connection pooling configuration
    HTTP2_ENABLED: bool = True
    KEEP_ALIVE_ENABLED: bool = True
    KEEP_ALIVE_TIMEOUT_SECONDS: int = 60
    MAX_CONCURRENT_CONNECTIONS: int = 1000
    CONNECTION_POOL_SIZE: int = 100

    # Compression configuration
    ENABLE_GZIP_COMPRESSION: bool = True
    ENABLE_BROTLI_COMPRESSION: bool = False

    # Streaming configuration
    STREAMING_ENABLED: bool = True
    STREAMING_CHUNK_SIZE: int = 1024
    FIRST_TOKEN_TIMEOUT_SECONDS: float = 20.0

    # Conversation compaction configuration
    MAX_PROMPT_TOKENS: int = 4096
    SYSTEM_PROMPT_TOKENS: int = 1024
    MAX_RESPONSE_TOKENS: int = 512

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
