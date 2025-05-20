import logging
import typing as t
from functools import lru_cache

import annotated_types as at
import durationpy
from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    RedisDsn,
    field_validator,
    model_validator,
)
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)
from redis import asyncio as aioredis

Duration = t.Annotated[
    int, BeforeValidator(lambda v: durationpy.from_str(v).total_seconds()), at.Ge(60)
]


class SnowflakeInternalSettings(BaseModel):
    dev_mode: bool = False
    use_internal_redis: bool = True

    @field_validator("dev_mode")
    def validate_dev_mode(cls, v):
        if v:
            logging.getLogger("uvicorn").warning(
                "Developer mode disables certain security features. Please don't use it in production."
            )

        return v


class SnowflakeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SNOWFLAKE_", env_ignore_empty=True, env_nested_delimiter="__"
    )

    allowed_hosts: str
    base_path: str = "/"
    fix_redirect_uris: bool = False
    token_lifetime: Duration = "1h"
    redis_url: RedisDsn | None = None
    root_redirect: t.Literal["repo", "web", "app", "off"] = "repo"
    redirect_status_code: t.Literal[302, 303] = 303
    enable_swagger: bool = False

    internal: SnowflakeInternalSettings = Field(
        default_factory=SnowflakeInternalSettings
    )

    @model_validator(mode="after")
    def validate_allowed_hosts(self):
        if "*" in self.allowed_hosts and not self.internal.dev_mode:
            logging.getLogger("uvicorn").warning(
                "Setting SNOWFLAKE_ALLOWED_HOSTS to '*' is insecure and not recommended."
            )

        return self

    @model_validator(mode="after")
    def validate_redis_url(self):
        if not (self.redis_url or self.internal.use_internal_redis):
            raise ValueError("redis_url is required on no-redis Snowflake images")

        return self

    @property
    def allowed_host_list(self) -> list[str]:
        return self.allowed_hosts.split(",")

    @property
    def redis(self):
        if self.redis_url:
            return aioredis.from_url(self.redis_url, decode_responses=True)

        return aioredis.Redis(decode_responses=True)

    @property
    def docs_url(self):
        return "/docs" if self.enable_swagger else None

    @property
    def root_redirect_url(self):
        return {
            "repo": "https://github.com/celsiusnarhwal/snowflake",
            "web": "https://discord.com/settings/account",
            "app": "discord://-/settings/account",
        }.get(self.root_redirect)


@lru_cache
def settings() -> SnowflakeSettings:
    return SnowflakeSettings()


settings()
