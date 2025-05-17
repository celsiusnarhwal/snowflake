import typing as t
from functools import lru_cache

import annotated_types as at
import durationpy
from pydantic import BeforeValidator
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

Duration = t.Annotated[
    int, BeforeValidator(lambda v: durationpy.from_str(v).total_seconds()), at.Ge(60)
]


class SnowflakeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SNOWFLAKE_", env_ignore_empty=True)

    token_lifetime: Duration = "1h"
    redirect_status_code: t.Literal[302, 303] = 303
    dev_mode: bool = False


@lru_cache
def settings() -> SnowflakeSettings:
    return SnowflakeSettings()


settings()
