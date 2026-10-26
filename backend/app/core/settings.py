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
    # Intelligence extraction. Temporary as of 2026-10-20: the user authorised the
    # Messages-compatible gateway already present in this environment, which ignores
    # the model name and always serves deepseek-flash. Azure OpenAI replaces it before
    # release; the seam above keeps that a one-class change.
    llm_provider: str = "anthropic_messages"
    llm_model: str = "deepseek-flash"
    llm_max_tokens: int = 4096
    llm_timeout_seconds: float = 120.0
    anthropic_base_url: str = ""
    anthropic_api_key: str = ""
    # Session lifetime. Fourteen days keeps a reviewer signed in across a fortnight of
    # meetings without holding a credential forever.
    session_days: int = 14
    # Production runs behind TLS; local development does not, so this defaults off.
    cookie_secure: bool = False
    worker_poll_seconds: int = 5


settings = Settings()
