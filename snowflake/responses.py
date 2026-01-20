import typing as t

from pydantic import BaseModel, Field, HttpUrl


class TokenResponse(BaseModel, title="Token"):
    access_token: str
    token_type: t.Literal["Bearer"]
    expires_at: int
    id_token: str = Field(title="ID Token")


class UserInfoResponse(BaseModel, title="User Info"):
    sub: str = Field(title="Subject")
    name: str = None
    preferred_username: str = None
    locale: str = None
    picture: HttpUrl = None
    email: str = None
    email_verified: bool = None
    groups: list[str] = None


class JWKSResponse(BaseModel, title="JSON Web Key Set"):
    class JWK(BaseModel, title="JSON Web Key"):
        n: str = Field(title="Modulus")
        e: str = Field(title="Exponent")
        kty: t.Literal["RSA"] = Field(title="Key Type")
        kid: str = Field(title="Key ID")
        use: t.Literal["sig"] = Field(title="Public Key Use")

    keys: list[JWK]


class WebFingerResponse(BaseModel, title="WebFinger"):
    class WebFingerLink(BaseModel):
        rel: t.Literal["http://openid.net/specs/connect/1.0/issuer"] = Field(
            title="Link Relation"
        )
        href: HttpUrl = Field(title="Target URI")

    subject: str
    links: list[WebFingerLink]


class DiscoveryResponse(BaseModel, title="OpenID Connect Discovery"):
    issuer: HttpUrl
    authorization_endpoint: HttpUrl
    token_endpoint: HttpUrl
    userinfo_endpoint: HttpUrl = Field(title="User Info Endpoint")
    jwks_uri: HttpUrl = Field(title="JWKS URI")
    claims_supported: list[str]
    grant_types_supported: list[str]
    id_token_signing_alg_values_supported: list[str] = Field(
        title="ID Token Signing Alg Values Supported"
    )
    token_endpoint_auth_methods_supported: list[str]
    response_types_supported: list[str]
    scopes_supported: list[str]


class HTTPClientErrorResponse(BaseModel, title="HTTP Client Error"):
    detail: str
