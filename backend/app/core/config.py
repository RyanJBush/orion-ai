from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Orion AI API"
    environment: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./orion.db"
    jwt_secret: str = Field(default="change-me", min_length=8)
    jwt_algorithm: str = "HS256"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ORION_")


settings = Settings()
