import logging
import typing as t
from functools import lru_cache

import dns.name
import durationpy
from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    field_validator,
)
from pydantic_core.core_schema import ValidationInfo
from pydantic_settings import (
    BaseSettings,
    NoDecode,
    SettingsConfigDict,
)

Duration = t.Annotated[
    int, BeforeValidator(lambda v: durationpy.from_str(v).total_seconds())
]


class SnowflakePrivateSettings(BaseModel):
    show_scalar_devtools_on_localhost: bool = False


class SnowflakeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SNOWFLAKE_", env_ignore_empty=True, env_nested_delimiter="__"
    )

    allowed_hosts: t.Annotated[list[str], NoDecode] = Field(default_factory=list)
    allowed_clients: t.Annotated[list[str], NoDecode] = Field(
        default=["*"], validate_default=False
    )
    base_path: str = "/"
    fix_redirect_uris: bool = False
    token_lifetime: Duration = Field("1h", ge=60)
    root_redirect: t.Literal["repo", "settings", "docs", "off"] = "repo"
    allowed_webfinger_hosts: t.Annotated[list[dns.name.Name], NoDecode] = Field(
        default_factory=list, validate_default=False
    )
    return_to_referrer: bool = False
    enable_docs: bool = False

    private: SnowflakePrivateSettings = Field(default_factory=SnowflakePrivateSettings)

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def validate_allowed_hosts(cls, v: str | list) -> list[str]:
        hosts = v.split(",") if isinstance(v, str) else v

        if "*" in hosts:
            logging.getLogger("uvicorn").warning(
                "Setting SNOWFLAKE_ALLOWED_HOSTS to '*' is insecure and not recommended."
            )

        return hosts + ["localhost", "127.0.0.1", "::1"]

    @field_validator("allowed_clients", mode="before")
    @classmethod
    def validate_allowed_clients(cls, v: str) -> list[str]:
        return v.split(",")

    @field_validator("allowed_webfinger_hosts", mode="before")
    @classmethod
    def validate_allowed_webfinger_hosts(cls, v: str) -> list[dns.name.Name]:
        hosts = []

        for i in v.split(","):
            name = dns.name.from_text(i)

            if name.is_wild() and len(name) < 3:
                raise ValueError(
                    "The unqualified wildcard ('*') is not permitted in SNOWFLAKE_ALLOWED_WEBFINGER_HOSTS"
                )

            hosts.append(name)

        return hosts

    @field_validator("enable_docs")
    @classmethod
    def validate_enable_docs(cls, v: bool, info: ValidationInfo) -> bool:
        return v or info.data["root_redirect"] == "docs"


@lru_cache
def settings() -> SnowflakeSettings:
    return SnowflakeSettings()


settings()
