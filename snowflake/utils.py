from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from fastapi import Request
from starlette.datastructures import URL


def get_oauth_client(**kwargs) -> StarletteOAuth2App:
    return OAuth().register(
        name="discord",
        authorize_url="https://discord.com/oauth2/authorize",
        access_token_url="https://discord.com/api/oauth2/token",
        api_base_url="https://discord.com/api/",
        **kwargs,
    )


def fix_redirect_uri(request: Request, redirect_uri: str):
    if not redirect_uri.startswith(f"{request.url_for('redirect')}/"):
        return str(request.url_for("redirect_to", redirect_uri=redirect_uri))

    return redirect_uri


def is_secure_transport(url: str | URL):
    if not isinstance(url, URL):
        url = URL(url)

    return url.scheme == "https" or url.hostname in ["127.0.0.1", "::1", "localhost"]
