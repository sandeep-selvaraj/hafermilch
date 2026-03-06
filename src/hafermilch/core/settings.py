from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI (standard)
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    # Azure OpenAI
    azure_openai_api_key: str | None = Field(default=None, alias="AZURE_OPENAI_API_KEY")

    # Google Gemini
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")

    # Ollama
    ollama_host: str = Field(default="http://localhost:11434", alias="OLLAMA_HOST")


settings = Settings()
