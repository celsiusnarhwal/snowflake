import secrets
import typing as t

from authlib.common.errors import AuthlibHTTPError
from fastapi import Depends, FastAPI, Request
from fastapi.security import (
    HTTPBasic,
    HTTPBasicCredentials,
)
from starlette.datastructures import URL
from starlette.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

from snowflake import utils
from snowflake.middleware import HTTPSOnlyMiddleware
from snowflake.settings import settings
from snowflake.types import SnowflakeAuthorizationCode

app = FastAPI(root_path=settings().base_path)
app.add_middleware(HTTPSOnlyMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=secrets.token_urlsafe(32),
    session_cookie="snowflake_session",
    max_age=0,
)


# noinspection PyUnusedLocal
@app.exception_handler(AuthlibHTTPError)
async def oauth_exception_handler(request: Request, exception: AuthlibHTTPError):
    raise HTTPException(exception.status_code, exception.description)


@app.get("/authorize")
async def authorize(
    request: Request,
    client_id: str,
    scope: str,
    redirect_uri: str,
    state: str = None,
    nonce: str = None,
):
    if not redirect_uri.startswith(f"{request.url_for('redirect')}/"):
        raise HTTPException(
            400,
            f"Redirect URI must be a subpath of {request.url_for('redirect')} "
            f"(e.g., {request.url_for('redirect_to', redirect_uri=redirect_uri)}",
        )

    scopes = set(scope.split(" "))

    if not (
        scopes == {"openid", "profile"} or scopes == {"openid", "profile", "email"}
    ):
        raise HTTPException(400, "Bad scopes")

    discord = utils.get_oauth_client(
        client_id=client_id, scope="identify" + (" email" if "email" in scopes else "")
    )

    authorization_params = {
        k: v for k, v in request.query_params.items() if k not in ["client_id", "scope"]
    }

    resp = await discord.authorize_redirect(request, **authorization_params)
    resp.status_code = settings().redirect_status_code

    if state and nonce:
        redis = settings().redis
        await redis.set(state, nonce, ex=300)

    return resp


@app.get("/redirect")
async def redirect():
    raise HTTPException(403)


@app.get("/redirect/{redirect_uri:path}")
async def redirect_to(
    request: Request, redirect_uri: str, code: str, state: str = None
):
    redis = settings().redis
    nonce = await redis.getdel(state)

    snowflake_code = SnowflakeAuthorizationCode(code=code, nonce=nonce)
    full_redirect_uri = URL(redirect_uri).include_query_params(
        **{**request.query_params, "code": snowflake_code.to_encrypted()}
    )

    return RedirectResponse(full_redirect_uri)


@app.post("/token")
async def token(
    request: Request,
    credentials: t.Annotated[
        HTTPBasicCredentials, Depends(HTTPBasic(auto_error=False))
    ],
):
    params = dict(await request.form())

    client_id = params.pop("client_id", None)
    client_secret = params.pop("client_secret", None)

    if credentials:
        client_id = client_id or credentials.username
        client_secret = client_secret or credentials.password

    snowflake_code = SnowflakeAuthorizationCode.from_encrypted(params.pop("code"))

    discord = utils.get_oauth_client(client_id=client_id, client_secret=client_secret)
    discord_token = await discord.fetch_access_token(**params, code=snowflake_code.code)

    resp = await discord.get("users/@me", token=discord_token)
    resp.raise_for_status()

    return utils.create_id_token(
        issuer=str(request.base_url),
        client_id=discord.client_id,
        nonce=snowflake_code.nonce,
        user_info=resp.json(),
    )


@app.get("/.well-known/jwks.json")
async def jwks():
    return utils.get_jwks()


@app.get("/.well-known/openid-configuration")
async def discovery(request: Request):
    return {
        "issuer": str(request.base_url),
        "claims_supported": [
            "sub",
            "name",
            "preferred_username",
            "locale",
            "picture",
            "email",
            "email_verified",
        ],
        "grant_types_supported": ["authorization_code"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "response_types_supported": ["code", "id_token"],
        "subject_types_supported": ["public"],
        "scopes_supported": ["openid", "profile", "email"],
        "authorization_endpoint": str(request.url_for("authorize")),
        "token_endpoint": str(request.url_for("token")),
        "jwks_uri": str(request.url_for("jwks")),
    }
