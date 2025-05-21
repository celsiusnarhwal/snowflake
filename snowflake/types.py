from joserfc.errors import JoseError
from pydantic import BaseModel, ValidationError
from starlette.exceptions import HTTPException

from snowflake import security


class SnowflakeStateData(BaseModel):
    scopes: list
    nonce: str | None = None


class SnowflakeAuthorizationData(BaseModel):
    code: str
    scopes: list
    nonce: str | None = None

    def to_jwt(self):
        return security.create_jwt(self.model_dump(), security.get_private_key())

    @classmethod
    def from_jwt(cls, token: str):
        try:
            decoded = security.decode_jwt(token, security.get_private_key())
            return cls.model_validate(decoded.claims)
        except (JoseError, ValidationError):
            raise HTTPException(400, "Invalid authorization code")
