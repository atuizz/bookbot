import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str
    BOT_USERNAME: str = "bookbot"
    MEILI_HOST: str = "http://localhost:7700"
    MEILI_MASTER_KEY: str
    PG_DSN: str = "postgresql://user:password@localhost:5432/bookbot"
    REDIS_URL: str = "redis://localhost:6379/0"
    ADMIN_IDS: list[int] = []  # 管理员 ID 列表

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def _parse_admin_ids(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            raw = v.strip()
            if not raw:
                return []
            if raw.startswith("["):
                parsed = json.loads(raw)
                return [int(x) for x in parsed]
            return [int(x.strip()) for x in raw.split(",") if x.strip()]
        return v

config = Settings()
