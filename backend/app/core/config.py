import os


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./orion.db")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret")
    jwt_algorithm: str = "HS256"
    cors_origins: list[str] = [
        origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    ]


settings = Settings()
