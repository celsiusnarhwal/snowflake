from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from fastapi import Request
from starlette.datastructures import URL

from snowflake.settings import settings


def get_oauth_client(**kwargs) -> StarletteOAuth2App:
    """
    Create a client for Discord's OAuth2 API.
    """
    return OAuth().register(
        name="discord",
        authorize_url="https://discord.com/oauth2/authorize",
        access_token_url="https://discord.com/api/oauth2/token",
        api_base_url="https://discord.com/api/",
        **kwargs,
    )


def fix_redirect_uri(request: Request, redirect_uri: str) -> str:
    """
    Modify a redirect URI to be a subpath of the /r endpoint.
    """
    if not redirect_uri.startswith(f"{request.url_for('redirect')}/"):
        redirect_uri = str(request.url_for("callback", redirect_uri=redirect_uri))

    return redirect_uri


def is_secure_transport(url: str | URL) -> bool:
    """
    Return `True` if the given URL is HTTPS or for a loopback address; `False` otherwise.
    """
    if not isinstance(url, URL):
        url = URL(url)

    return url.scheme == "https" or (
        settings().treat_loopback_as_secure
        and url.hostname in ["localhost", "127.0.0.1", "::1"]
    )


def get_discovery_info(request: Request) -> dict:
    """
    Return OpenID Connect Discovery information.
    """
    return {
        "issuer": str(request.base_url),
        "authorization_endpoint": str(request.url_for("authorize")),
        "token_endpoint": str(request.url_for("token")),
        "userinfo_endpoint": str(request.url_for("userinfo")),
        "jwks_uri": str(request.url_for("jwks")),
        "claims_supported": [
            "sub",
            "name",
            "preferred_username",
            "locale",
            "picture",
            "email",
            "email_verified",
            "groups",
        ],
        "grant_types_supported": ["authorization_code"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post",
        ],
        "response_types_supported": ["token", "id_token"],
        "subject_types_supported": ["public"],
        "scopes_supported": ["openid", "profile", "email", "groups"],
    }
