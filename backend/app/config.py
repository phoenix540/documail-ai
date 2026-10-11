from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://documail:documail@postgres:5432/documail"
    redis_url: str = "redis://redis:6379/0"
    celery_eager: bool = False  # run tasks inline (tests / no Redis)

    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60 * 12

    chroma_path: str = "/data/chroma"
    chroma_collection: str = "documents"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2:3b"
    rag_top_k: int = 4

    smtp_host: str = "mailhog"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "DocuMail AI <no-reply@documail.local>"

    cors_origins: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
