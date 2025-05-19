import typing as t
from functools import lru_cache

import annotated_types as at
import durationpy
from pydantic import BeforeValidator, RedisDsn
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)
from redis import asyncio as aioredis

Duration = t.Annotated[
    int, BeforeValidator(lambda v: durationpy.from_str(v).total_seconds()), at.Ge(60)
]


class SnowflakeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SNOWFLAKE_", env_ignore_empty=True)

    base_path: str = ""
    token_lifetime: Duration = "1h"
    fix_redirect_uris: bool = False
    redis_url: RedisDsn | None = None
    redirect_status_code: t.Literal[302, 303] = 303
    enable_openapi: bool = False
    enable_swagger: bool = False
    dev_mode: bool = False

    @property
    def redis(self):
        if self.redis_url:
            return aioredis.from_url(self.redis_url, decode_responses=True)

        return aioredis.Redis(decode_responses=True)

    @property
    def openapi_url(self):
        return "/docs" if self.enable_openapi else None

    @property
    def docs_url(self):
        return "/docs" if self.enable_swagger else None


@lru_cache
def settings() -> SnowflakeSettings:
    return SnowflakeSettings()


settings()
