import typing as t

from cryptography.fernet import Fernet
from pydantic import BaseModel


class SnowflakeAuthorizationCode(BaseModel):
    cipher: t.ClassVar[Fernet] = Fernet(Fernet.generate_key())

    code: str
    nonce: str | None = None

    def to_encrypted(self):
        return self.cipher.encrypt(self.model_dump_json().encode()).decode()

    @classmethod
    def from_encrypted(cls, encrypted) -> t.Self:
        return cls.model_validate_json(cls.cipher.decrypt(encrypted))
