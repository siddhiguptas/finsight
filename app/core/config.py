from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql://user:password@postgres:5432/finsight",
        alias="DATABASE_URL",
    )
    async_database_url: str = Field(
        default="postgresql+asyncpg://user:password@postgres:5432/finsight",
        alias="ASYNC_DATABASE_URL",
    )
    mongo_uri: str = Field(default="mongodb://mongo:27017/finsight", alias="MONGO_URI")
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    newsapi_key: str | None = Field(default=None, alias="NEWSAPI_KEY")
    alpha_vantage_key: str | None = Field(default=None, alias="ALPHA_VANTAGE_KEY")
    reddit_client_id: str | None = Field(default=None, alias="REDDIT_CLIENT_ID")
    reddit_client_secret: str | None = Field(default=None, alias="REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = Field(default="FinSight/1.0", alias="REDDIT_USER_AGENT")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")

    secret_key: str | None = Field(default=None, alias="SECRET_KEY")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


settings = Settings()
