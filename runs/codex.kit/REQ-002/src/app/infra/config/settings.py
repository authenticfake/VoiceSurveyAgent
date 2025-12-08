from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+pysqlite:///./campaigns.db"

    class Config:
        env_prefix = "VSA_"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()