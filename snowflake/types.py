import typing as t

import cryptography.fernet
from cryptography.fernet import Fernet
from pydantic import BaseModel
from starlette.exceptions import HTTPException


class SnowflakeStateData(BaseModel):
    cipher: t.ClassVar[Fernet] = Fernet(Fernet.generate_key())

    scopes: list
    nonce: str | None = None

    def to_encrypted(self):
        return self.cipher.encrypt(self.model_dump_json().encode()).decode()

    @classmethod
    def from_encrypted(cls, encrypted) -> t.Self:
        try:
            return cls.model_validate_json(cls.cipher.decrypt(encrypted))
        except cryptography.fernet.InvalidToken:
            raise HTTPException(400)


class SnowflakeAuthorizationData(SnowflakeStateData):
    cipher: t.ClassVar[Fernet] = Fernet(Fernet.generate_key())

    code: str
