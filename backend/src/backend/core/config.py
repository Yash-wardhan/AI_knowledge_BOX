from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str

    EMBEDDING_BASE_URL: str
    EMBEDDING_API_KEY: str
    EMBEDDING_MODEL: str
    EMBEDDING_DIMENSIONS: int = 768

    LLM_BASE_URL: str
    LLM_API_KEY: str
    LLM_MODEL: str

    # Optional — only needed if using real OpenAI endpoints
    OPENAI_API_KEY: str = "not-set"

    # Frontend origins allowed to call the API (JSON list in .env, e.g.
    # CORS_ORIGINS=["http://localhost:3000","https://app.example.com"])
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()