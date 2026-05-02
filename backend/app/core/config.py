from dotenv import load_dotenv
from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_name: str = "ClinSight AI Backend"
    app_version: str = "0.2.0"
    app_description: str = "Clinical data ingestion, quality analysis, and patient insights API"
    database_url: str = Field(..., alias="DATABASE_URL")
    api_v1_prefix: str = "/api"
    clinical_schema: str = Field(default="analytics_clinical", alias="CLINICAL_SCHEMA")
    auth_secret_key: str = Field(default="clinsight-demo-secret-change-me", alias="AUTH_SECRET_KEY")
    auth_token_expire_minutes: int = Field(default=480, alias="AUTH_TOKEN_EXPIRE_MINUTES")
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"], alias="CORS_ORIGINS")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
