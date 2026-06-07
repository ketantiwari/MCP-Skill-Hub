from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    node_env: str = Field(default="development", alias="NODE_ENV")
    port: int = Field(default=3000, alias="PORT")

    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    google_model: str = Field(default="gemini-2.5-flash", alias="GOOGLE_MODEL")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    model_timeout_ms: int = Field(default=30_000, alias="MODEL_TIMEOUT_MS")
    model_max_retries: int = Field(default=2, alias="MODEL_MAX_RETRIES")

    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")

    tool_workspace_dir: str = Field(default="workspace", alias="TOOL_WORKSPACE_DIR")
    tool_registry_dir: str = Field(default="workspace/tools", alias="TOOL_REGISTRY_DIR")
    runtime_dir: str = Field(default="workspace/runtime", alias="RUNTIME_DIR")
    log_dir: str = Field(default="workspace/logs", alias="LOG_DIR")

    auto_publish_low_risk: bool = Field(default=True, alias="AUTO_PUBLISH_LOW_RISK")
    require_approval_for_destructive: bool = Field(
        default=True, alias="REQUIRE_APPROVAL_FOR_DESTRUCTIVE"
    )
    sandbox_mode: str = Field(default="docker", alias="SANDBOX_MODE")
    docker_tool_image: str = Field(
        default="dynamic-mcp-skill-runner:latest", alias="DOCKER_TOOL_IMAGE"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
