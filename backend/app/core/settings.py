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
    # "whisper" runs locally; "huawei" calls SIS and needs the credentials below.
    speech_provider: str = "whisper"
    whisper_model: str = "small"
    # Huawei Cloud SIS reads audio from OBS, so the bucket must exist in the same region.
    huawei_region: str = ""
    huawei_project_id: str = ""
    huawei_ak: str = ""
    huawei_sk: str = ""
    huawei_obs_bucket: str = ""
    huawei_sis_property: str = "chinese_16k_conversation"
    huawei_sis_endpoint: str = ""
    huawei_obs_endpoint: str = ""
    huawei_sis_poll_seconds: float = 5.0
    huawei_sis_timeout_seconds: float = 3600.0
    worker_poll_seconds: int = 5


settings = Settings()
