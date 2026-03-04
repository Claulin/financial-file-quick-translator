from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os


@dataclass(frozen=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    sec_user_agent: str
    openai_api_key: str | None
    openai_base_url: str
    openai_model: str

    app_host: str
    app_port: int

    db_path: Path

    @staticmethod
    def load() -> "Settings":
        load_dotenv()

        sec_user_agent = os.getenv("SEC_USER_AGENT", "").strip()
        if not sec_user_agent:
            raise RuntimeError(
                "SEC_USER_AGENT is required. Example: "
                '"FilingTranslationEngine (your-email@example.com)"'
            )

        return Settings(
            sec_user_agent=sec_user_agent,
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip() or None,
            openai_base_url=(os.getenv("OPENAI_BASE_URL", "https://api.openai.com").strip()),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
            app_host=os.getenv("APP_HOST", "0.0.0.0").strip(),
            app_port=int(os.getenv("APP_PORT", "8000").strip()),
            db_path=Path(os.getenv("DB_PATH", "app.db")).resolve(),
        )
