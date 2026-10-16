from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_registry() -> Path:
    """Locate models/registry.yaml by walking up from this file (works from a repo checkout)."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "models" / "registry.yaml"
        if candidate.exists():
            return candidate
    return Path("models/registry.yaml")


class Settings(BaseSettings):
    """All settings come from VORTEX_* environment variables or a .env file."""

    model_config = SettingsConfigDict(
        env_prefix="VORTEX_",
        env_file=(".env", "../../.env"),
        extra="ignore",
    )

    env: str = "development"
    local_mode: bool = True
    registry_path: Path = Field(default_factory=_find_registry)
    database_url: str = "sqlite+aiosqlite:///./data/vortex.db"
    db_auto_create: bool = False
    cors_origins: str = "http://localhost:3000"
    rate_limit_per_minute: int = 120
    request_timeout: float = 300.0
    mock_backend: bool = False

    # Accounts (used when local_mode is false)
    data_dir: Path = Path("data")
    secret_key: str = ""  # empty: generated once and stored in data_dir/.secret_key
    session_hours: int = 12
    allow_registration: bool = True
    cookie_secure: bool = False  # set true behind HTTPS

    # Files
    max_upload_mb: int = 25
    rag_context_chars: int = 8000  # file text given to the model per answer

    # Tools (each is off until its service is set up; see docs/ferramentas.md)
    searxng_url: str = "http://127.0.0.1:8888"
    comfyui_url: str = "http://127.0.0.1:8188"
    image_checkpoint: str = "v1-5-pruned-emaonly.safetensors"
    sandbox_image: str = "vortex-sandbox"
    sandbox_timeout: int = 60  # seconds
    sandbox_memory: str = "768m"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
