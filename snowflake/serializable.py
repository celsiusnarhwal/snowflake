import secrets
import time
import typing as t

from authlib.oauth2.rfc6749 import MismatchingStateException
from fastapi.exceptions import HTTPException
from joserfc.errors import JoseError
from pydantic import BaseModel, ValidationError, computed_field

from snowflake import security


class Serializable(BaseModel):
    @computed_field
    @property
    def iat(self) -> int:
        return int(time.time())

    @computed_field
    @property
    def exp(self) -> int:
        return self.iat + 300

    @computed_field
    @property
    def randomizer(self) -> str:
        return secrets.token_urlsafe(32)

    def to_jwt(self) -> str:
        """
        Serialize this model to a JWT.
        """
        return security.create_jwt(self.model_dump())

    @classmethod
    def from_jwt(cls, token: str) -> t.Self:
        """
        Deserialize this model from a JWT.
        """
        decoded = security.decode_jwt(token)
        return cls.model_validate(decoded.claims)


class SnowflakeStateData(Serializable):
    scopes: list[str]
    redirect_uri: str
    state: str | None
    nonce: str | None
    referrer: str | None

    @classmethod
    def from_jwt(cls, token: str) -> t.Self:
        try:
            return super(SnowflakeStateData, cls).from_jwt(token)
        except (JoseError, ValidationError):
            raise MismatchingStateException()


class SnowflakeAuthorizationData(Serializable):
    code: str
    scopes: list[str]
    nonce: str | None = None

    @classmethod
    def from_jwt(cls, token: str) -> t.Self:
        try:
            return super(SnowflakeAuthorizationData, cls).from_jwt(token)
        except (JoseError, ValidationError):
            raise HTTPException(400, "Invalid authorization code")
