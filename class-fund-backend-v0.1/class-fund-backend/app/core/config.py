from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Class Fund API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://classfund:classfund@localhost:5432/classfund"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    upload_dir: str = "./storage/uploads"
    max_upload_mb: int = 10
    ai_service_key: str = "change-me-ai-service-key"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    ai_confidence_threshold: float = 0.90

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
