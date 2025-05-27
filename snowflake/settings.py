import logging
import typing as t
from functools import lru_cache

import durationpy
from pydantic import (
    BeforeValidator,
    Field,
    model_validator,
)
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

Duration = t.Annotated[
    int, BeforeValidator(lambda v: durationpy.from_str(v).total_seconds())
]


class SnowflakeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SNOWFLAKE_", env_ignore_empty=True, env_nested_delimiter="__"
    )

    allowed_hosts: str = ""
    base_path: str = "/"
    fix_redirect_uris: bool = False
    token_lifetime: Duration = Field("1h", ge=60)
    root_redirect: t.Literal["repo", "settings", "off"] = "repo"
    enable_swagger: bool = False

    @model_validator(mode="after")
    def validate_allowed_hosts(self):
        if "*" in self.allowed_hosts:
            logging.getLogger("uvicorn").warning(
                "Setting SNOWFLAKE_ALLOWED_HOSTS to '*' is insecure and not recommended."
            )

        return self

    @property
    def allowed_host_list(self) -> list[str]:
        return self.allowed_hosts.split(",") + ["localhost", "127.0.0.1", "::1"]

    @property
    def docs_url(self):
        return "/docs" if self.enable_swagger else None

    @property
    def openapi_url(self):
        return "/openapi.json" if self.enable_swagger else None

    @property
    def root_redirect_url(self):
        return {
            "repo": "https://github.com/celsiusnarhwal/snowflake",
            "settings": "https://discord.com/settings/account",
        }.get(self.root_redirect)


@lru_cache
def settings() -> SnowflakeSettings:
    return SnowflakeSettings()


settings()
