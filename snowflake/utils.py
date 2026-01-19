import httpx
import pydantic
from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from fastapi import Request
from pydantic import ConfigDict
from starlette.datastructures import URL


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
        return str(request.url_for("callback", redirect_uri=redirect_uri))

    return redirect_uri


def is_secure_transport(url: str | URL) -> bool:
    """
    Return `True` if the given URL is HTTPS or for a loopback address; `False` otherwise.
    """
    if not isinstance(url, URL):
        url = URL(url)

    return url.scheme == "https" or url.hostname in ["localhost", "127.0.0.1", "::1"]


def get_response_code_documentation(code: int) -> dict:
    """
    Return generic OpenAPI response documentation for an HTTP status code.
    """
    reason_phrase = httpx.codes.get_reason_phrase(code)

    model = pydantic.create_model(
        f"HTTP{code}Error",
        __config__=ConfigDict(title=f"HTTP {code} Error"),
        detail=(str, reason_phrase),
    )

    return {
        "summary": reason_phrase,
        "model": model,
    }
