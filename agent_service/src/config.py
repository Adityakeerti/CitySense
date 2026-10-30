from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "city-sense-ai"
    environment: str = "development"
    demo_mode: bool = False
    database_url: str = "postgresql+asyncpg://localhost:5432/citysense"
    jwt_secret: SecretStr = SecretStr("")
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str | None = None
    jwt_audience: str | None = None
    embed_model: str = "intfloat/multilingual-e5-small"
    embed_dimension: int = Field(default=384, ge=384, le=384)
    use_sentence_transformer: bool = True
    embedding_local_files_only: bool = False
    local_llm_base_url: str | None = "http://localhost:8080/v1"
    local_llm_model: str = "local-model"
    groq_api_key: SecretStr | None = None
    sarvam_api_key: SecretStr | None = None
    provider_order: str = "local,groq,sarvam"
    log_level: str = "INFO"
    max_message_length: int = Field(default=4000, ge=100, le=4000)
    max_upload_bytes: int = Field(default=10_485_760, ge=1024)
    action_ttl_seconds: int = Field(default=300, ge=30, le=3600)
    rate_limit_per_minute: int = Field(default=10, ge=1, le=1000)
    provider_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    local_stt_base_url: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    sarvam_base_url: str = "https://api.sarvam.ai"
    groq_model: str = "llama-3.1-8b-instant"
    groq_stt_model: str = "whisper-large-v3-turbo"
    sarvam_model: str = "sarvam-105b"
    sarvam_stt_model: str = "saaras:v3"
    local_stt_model: str = "whisper-1"
    local_llm_api_key: SecretStr | None = None
    stt_provider_order: str = "local,groq,sarvam"
    local_tools_enabled: bool = False
    llm_max_concurrency: int = Field(default=4, ge=1, le=32)
    provider_rpm: int = Field(default=20, ge=1)
    provider_cooldown_seconds: int = Field(default=60, ge=1)
    max_provider_answer_chars: int = Field(default=16000, ge=100)
    default_city_id: str = "dehradun"
    source_freshness_days: int = Field(default=90, ge=1)
    cache_ttl_seconds: int = Field(default=3600, ge=1)
    upload_dir: Path = Path("data/uploads")
    ingestion_timeout_seconds: float = Field(default=120, gt=0)
    complaint_adapter_url: str | None = None
    complaint_status_url: str | None = None
    events_url: str | None = None
    alerts_url: str | None = None
    adapter_api_key: SecretStr | None = None
    cors_origins: list[str] = Field(default_factory=list)
    refresh_allowed_domains: list[str] = Field(default_factory=list)
    refresh_interval_seconds: int = Field(default=3600, ge=60)
    request_timeout_seconds: float = Field(default=90, gt=0, le=300)
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="", extra="ignore", env_ignore_empty=True
    )

    @property
    def providers(self) -> list[str]:
        return [item.strip() for item in self.provider_order.split(",") if item.strip()]

    @model_validator(mode="after")
    def validate_configuration(self):
        if not self.use_sentence_transformer and not self.demo_mode:
            raise ValueError(
                "Hash embeddings are only allowed in DEMO_MODE; production requires E5"
            )
        for name in self.providers + self.stt_provider_order.split(","):
            if name.strip() not in {"local", "groq", "sarvam"}:
                raise ValueError(f"Unknown provider: {name}")
        return self

    @field_validator("database_url")
    @classmethod
    def async_postgres_url(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use postgresql+asyncpg")
        return value

    @field_validator(
        "local_llm_base_url",
        "local_stt_base_url",
        "groq_base_url",
        "sarvam_base_url",
        "complaint_adapter_url",
        "complaint_status_url",
        "events_url",
        "alerts_url",
    )
    @classmethod
    def endpoint_url(cls, value: str | None) -> str | None:
        if not value:
            return None
        from urllib.parse import urlparse

        parsed = urlparse(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise ValueError("Endpoint must be an HTTP(S) URL without credentials or fragments")
        return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
