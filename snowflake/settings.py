import base64
import importlib.metadata
import logging
import secrets
import typing as t
from functools import lru_cache

import dns.name
import durationpy
from pydantic import (
    Base64Bytes,
    BaseModel,
    BeforeValidator,
    Field,
    Secret,
    field_validator,
)
from pydantic_core.core_schema import ValidationInfo
from pydantic_settings import (
    BaseSettings,
    NoDecode,
    SettingsConfigDict,
)

type CommaSeparatedList[T] = t.Annotated[
    list[T],
    NoDecode,
    BeforeValidator(lambda v: v.split(",") if isinstance(v, str) else v),
]

Duration = t.Annotated[
    int, BeforeValidator(lambda v: durationpy.from_str(v).total_seconds())
]


class SnowflakePrivateSettings(BaseModel):
    show_scalar_devtools_on_localhost: bool = False


class SnowflakeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SNOWFLAKE_", env_ignore_empty=True, env_nested_delimiter="__"
    )

    allowed_hosts: CommaSeparatedList[str] = Field(default_factory=list)
    secret: Secret[Base64Bytes] = Field(None)
    allowed_clients: t.Annotated[list[str], NoDecode] = Field(
        default=["*"], validate_default=False
    )
    base_path: str = "/"
    fix_redirect_uris: bool = False
    token_lifetime: Duration = Field("1h", ge=60)
    rotation_interval: Duration = None
    key_history: int = Field(1, ge=1, le=10)
    root_redirect: t.Literal["repo", "settings", "docs", "off"] = "repo"
    treat_loopback_as_secure: bool = True
    return_to_referrer: bool = False
    allowed_webfinger_hosts: CommaSeparatedList[dns.name.Name] = Field(
        default_factory=list, validate_default=False
    )
    enable_docs: bool = False

    private: SnowflakePrivateSettings = Field(default_factory=SnowflakePrivateSettings)

    @field_validator("allowed_hosts", mode="after")
    def validate_allowed_hosts(cls, v: str | list) -> list[str]:
        if "*" in v:
            logging.getLogger("uvicorn").warning(
                "Setting SNOWFLAKE_ALLOWED_HOSTS to '*' is insecure and not recommended."
            )

        loopback = ["localhost", "127.0.0.1", "::1"]

        if not set(v).difference(loopback):
            logging.getLogger("uvicorn").warning(
                "Snowflake is only accessible from within your local network. If this isn't your intention, set "
                "SNOWFLAKE_ALLOWED_HOSTS to include the hosts at which Snowflake should be accessible."
            )

        return v + loopback

    @field_validator("allowed_clients", mode="before")
    def validate_allowed_clients(cls, v: str) -> list[str]:
        return v.split(",")

    @field_validator("allowed_webfinger_hosts", mode="before")
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

    @field_validator("secret", mode="wrap")
    def validate_secret(cls, v, handler: t.Callable):
        if v is None:
            v = base64.b64encode(secrets.token_bytes(32))

            logging.getLogger("uvicorn").warning(
                f"SNOWFLAKE_SECRET is not set. Snowflake will generate one for "
                f"you this time, but unless you set SNOWLAKE_SECRET yourself, "
                f"restarting Snowflake will cause all in-progress authorizations to "
                f"fail and invalidate all existing tokens. You can generate a secret with "
                f"the following command: "
                f"docker run --rm ghcr.io/celsiusnarhwal/snowflake:v{importlib.metadata.version('snowflake')} secret"
            )

        v = handler(v)

        if len(v.get_secret_value()) < 32:
            raise ValueError("SNOWFLAKE_SECRET must be at least 32 bytes")

        return v

    @field_validator("rotation_interval", mode="wrap")
    def validate_rotation_interval(cls, v, handler: t.Callable, info: ValidationInfo):
        token_lifetime = info.data["token_lifetime"]

        if v is None:
            return token_lifetime

        v = handler(v)

        if v < token_lifetime:
            raise ValueError(
                "SNOWFLAKE_ROTATION_INTERVAL, if set to a duration, must be greater than or equal to "
                "SNOWFLAKE_TOKEN_LIFETIME"
            )

        return v

    @field_validator("enable_docs")
    def validate_enable_docs(cls, v: bool, info: ValidationInfo) -> bool:
        return v or info.data["root_redirect"] == "docs"


@lru_cache
def settings() -> SnowflakeSettings:
    return SnowflakeSettings()


settings()
print(settings())
