from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    # Settled 2026-10-19: recordings are kept for 90 days; owners may delete sooner.
    retention_days: int = 90
    # Development storage. Production targets S3, which slots in behind the same seam.
    storage_local_path: str = ".storage/recordings"
    # Speech runs locally until AWS credentials exist for Transcribe; see PROGRESS.md.
    whisper_model: str = "tiny.en"
    worker_poll_seconds: int = 5


settings = Settings()
