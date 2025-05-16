import typing as t
from functools import lru_cache

import annotated_types as at
import durationpy
from pydantic import BeforeValidator, HttpUrl, model_validator
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

Duration = t.Annotated[
    int, BeforeValidator(lambda v: durationpy.from_str(v).total_seconds()), at.Ge(60)
]


class SnowflakeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SNOWFLAKE_", env_file=".env", env_ignore_empty=True
    )

    public_url: str
    token_lifetime: Duration = "1h"
    redirect_status_code: t.Literal[302, 303] = 303
    dev_mode: bool = False

    @model_validator(mode="after")
    def validate_public_url(self):
        self.public_url = self.public_url.rstrip("/")

        if HttpUrl(self.public_url).scheme != "https" and not self.dev_mode:
            raise ValueError("public_url must be an HTTPS URL")

        return self


@lru_cache
def settings() -> SnowflakeSettings:
    return SnowflakeSettings()


settings()
