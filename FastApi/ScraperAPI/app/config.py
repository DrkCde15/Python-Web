from functools import lru_cache
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.app_name = os.getenv("APP_NAME", "ScraperAPI")
        self.database_path = Path(os.getenv("DATABASE_PATH", "data/scraperapi.db"))
        self.scraper_api_keys = self._csv(os.getenv("SCRAPER_API_KEYS", ""))
        self.default_user_agent = os.getenv(
            "DEFAULT_USER_AGENT",
            "ScraperAPI/0.1 (+https://localhost)",
        )
        self.request_timeout_seconds = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))
        self.max_html_bytes = int(os.getenv("MAX_HTML_BYTES", "2000000"))
        self.allow_private_urls = os.getenv("ALLOW_PRIVATE_URLS", "false").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def _csv(self, raw_value: str) -> set[str]:
        return {item.strip() for item in raw_value.split(",") if item.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
