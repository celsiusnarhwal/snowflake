import typing as t

from authlib.oauth2.rfc6749 import MismatchingStateException
from joserfc.errors import JoseError
from pydantic import BaseModel, ValidationError
from starlette.exceptions import HTTPException

from snowflake import security


class Encodable(BaseModel):
    def to_jwt(self):
        return security.create_jwt(self.model_dump(), security.get_private_key())

    @classmethod
    def from_jwt(cls, token: str) -> t.Self:
        decoded = security.decode_jwt(token, security.get_private_key())
        return cls.model_validate(decoded.claims)


class SnowflakeStateData(Encodable):
    state: str
    scopes: list
    nonce: str | None = None

    @classmethod
    def from_jwt(cls, token: str) -> t.Self:
        try:
            return super(SnowflakeStateData, cls).from_jwt(token)
        except (JoseError, ValidationError):
            raise MismatchingStateException()


class SnowflakeAuthorizationData(Encodable):
    code: str
    scopes: list
    nonce: str | None = None

    @classmethod
    def from_jwt(cls, token: str) -> t.Self:
        try:
            return super(SnowflakeAuthorizationData, cls).from_jwt(token)
        except (JoseError, ValidationError):
            raise HTTPException(400, "Invalid authorization code")
