from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "HealthAI - 智能情绪管理平台"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./healthai.db"

    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    API_V1_PREFIX: str = "/api/v1"

    NVIDIA_API_KEY: Optional[str] = None
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL_NAME: str = "mistralai/mistral-large-3-675b-instruct-2512"

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    MODEL_NAME: str = "gpt-3.5-turbo"

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
