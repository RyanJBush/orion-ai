from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Orion AI API"
    environment: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./orion.db"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ORION_")


settings = Settings()
