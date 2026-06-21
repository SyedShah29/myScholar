from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "myScholar"
    app_env: str = Field(default="development", alias="APP_ENV")

    # Groq (free tier — console.groq.com)
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1", alias="GROQ_BASE_URL"
    )
    groq_model: str = Field(
        default="meta-llama/llama-4-scout-17b-16e-instruct", alias="GROQ_MODEL"
    )

    # Local Embeddings (sentence-transformers, free, no API)
    local_embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", alias="LOCAL_EMBEDDING_MODEL"
    )

    # ChromaDB (in-process, no Docker)
    chroma_path: str = Field(default="./data/chromadb", alias="CHROMA_PATH")

    # SQLite
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/myscholar.db", alias="DATABASE_URL"
    )

    # External APIs (all free, no key)
    quran_api_base: str = Field(
        default="https://api.alquran.cloud/v1", alias="QURAN_API_BASE"
    )
    hadith_api_base: str = Field(
        default="https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1",
        alias="HADITH_API_BASE",
    )
    aladhan_api_base: str = Field(
        default="https://api.aladhan.com/v1", alias="ALADHAN_API_BASE"
    )
    pollinations_base: str = Field(
        default="https://image.pollinations.ai/prompt", alias="POLLINATIONS_BASE"
    )

    # App behaviour
    request_timeout_seconds: float = Field(default=60.0, alias="REQUEST_TIMEOUT_SECONDS")
    max_history_messages: int = Field(default=10, alias="MAX_HISTORY_MESSAGES")
    max_search_results: int = Field(default=15, alias="MAX_SEARCH_RESULTS")
    seed_on_startup: bool = Field(default=True, alias="SEED_ON_STARTUP")
    allow_offline_demo: bool = Field(default=True, alias="ALLOW_OFFLINE_DEMO")

    # Default madhab
    default_madhab: Literal["hanafi", "maliki", "shafii", "hanbali", "jafari", "general"] = Field(
        default="general", alias="DEFAULT_MADHAB"
    )

    # Features
    enable_streaming: bool = Field(default=True, alias="ENABLE_STREAMING")
    enable_image_generation: bool = Field(default=True, alias="ENABLE_IMAGE_GENERATION")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @property
    def has_groq_key(self) -> bool:
        return bool(
            self.groq_api_key
            and self.groq_api_key.strip()
            and "your-" not in self.groq_api_key.lower()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
