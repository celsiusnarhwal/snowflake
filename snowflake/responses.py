import typing as t

from pydantic import BaseModel, HttpUrl


class TokenResponse(BaseModel):
    access_token: str
    token_type: t.Literal["Bearer"]
    expires_at: int
    id_token: str


class UserInfoResponse(BaseModel):
    sub: str
    name: str = None
    preferred_username: str = None
    locale: str = None
    picture: HttpUrl = None
    email: str = None
    email_verified: bool = None
    groups: list[str] = None


class JWK(BaseModel):
    n: str
    e: str
    kty: t.Literal["RSA"]
    kid: str
    use: t.Literal["sig"]


class JWKSResponse(BaseModel):
    keys: list[JWK]


class WebFingerLink(BaseModel):
    rel: t.Literal["http://openid.net/specs/connect/1.0/issuer"]
    href: HttpUrl


class WebFingerResponse(BaseModel):
    subject: str
    links: list[WebFingerLink]


class DiscoveryResponse(BaseModel):
    issuer: HttpUrl
    claims_supported: list[str]
    grant_types_supported: list[str]
    id_token_signing_alg_values_supported: list[str]
    token_endpoint_auth_methods_supported: list[str]
    response_types_supported: list[str]
    scopes_supported: list[str]
    authorization_endpoint: HttpUrl
    token_endpoint: HttpUrl
    userinfo_endpoint: HttpUrl
    jwks_uri: HttpUrl
